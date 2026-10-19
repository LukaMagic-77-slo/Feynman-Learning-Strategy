"""React前端的本地API；保留Streamlit和现有后端。"""
import hashlib
import json
import logging
import os
import sys
import time
from copy import copy
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from threading import Lock, RLock
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'monitoring'), str(ROOT / 'evaluation'), str(ROOT)]
from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI, APIConnectionError, APITimeoutError
from pydantic import BaseModel, Field, field_validator
from typing import Literal

from assistant import create_assistant
from init_db import get_db_connection
from practice_record import PracticeWithRecord
from practice.get_knowledge import get_sections, get_topics
from save_feedback import save_feedback
from save_history import save_history
from record_query import get_chat_list, get_history

log = logging.getLogger(__name__)
sessions = {}
sessions_lock = Lock()
SESSION_TTL = 4 * 3600


@dataclass
class BrowserSession:
    id: str
    updated: float = field(default_factory=time.monotonic)
    lock: RLock = field(default_factory=RLock)
    exercise: object = None
    record_ids: set = field(default_factory=set)
    responses: dict = field(default_factory=dict)


def session(request: Request, response: Response):
    sid = request.cookies.get('feynman_session')
    now = time.monotonic()
    with sessions_lock:
        for old in [key for key, value in sessions.items() if now - value.updated > SESSION_TTL]:
            sessions.pop(old, None)
        state = sessions.get(sid)
        if state is None:
            if len(sessions) >= 200:
                raise HTTPException(503, '会话已满，请稍后再试')
            sid = str(uuid4())
            state = sessions[sid] = BrowserSession(sid)
            response.set_cookie('feynman_session', sid, httponly=True,
                                samesite='strict', max_age=SESSION_TTL)
        state.updated = now
    return state


@lru_cache(maxsize=1)
def model_client():
    for name in ['DASHSCOPE_API_KEY', 'DASHSCOPE_BASE_URL', 'DASHSCOPE_MODEL']:
        if not os.getenv(name):
            raise HTTPException(503, f'后端缺少配置：{name}')
    return OpenAI(api_key=os.environ['DASHSCOPE_API_KEY'],
                  base_url=os.environ['DASHSCOPE_BASE_URL'], timeout=60.0, max_retries=0)


@asynccontextmanager
async def lifespan(app):
    yield
    if model_client.cache_info().currsize:
        model_client().close()
    sessions.clear()
    model_client.cache_clear()


app = FastAPI(title='费曼学习 API', lifespan=lifespan)


@app.exception_handler(Exception)
async def unexpected(request, exc):
    log.error('Request failed: %s', request.url.path, exc_info=exc)
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        message = '模型连接暂时不稳定，请稍后重试。已保存的数据不受影响。'
    else:
        message = '本次操作未完成，请检查数据库、模型配置或后端终端日志。'
    return JSONResponse(status_code=503, content={'detail': message})


class Operation(BaseModel):
    request_id: UUID


class Question(Operation):
    question: str = Field(min_length=1, max_length=6000)
    chat_id: UUID | None = None

    @field_validator('question')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('问题不能为空')
        return value.strip()


class PracticeQuestion(Operation):
    section: str = Field(min_length=1, max_length=300)
    topic: str = Field(min_length=1, max_length=300)


class Explanation(Operation):
    user_answer: str = Field(min_length=1, max_length=12000)

    @field_validator('user_answer')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('解释不能为空')
        return value.strip()


class Feedback(BaseModel):
    record_id: int = Field(gt=0)
    score: Literal[-1, 1]


def once(state, operation, body, action):
    """同一浏览器重复提交相同请求ID时，返回已完成结果而不再次消费模型。"""
    payload = body.model_dump(mode='json')
    key = str(body.request_id)
    fingerprint = hashlib.sha256(json.dumps([operation, payload], sort_keys=True).encode()).hexdigest()
    with state.lock:
        if key in state.responses:
            previous, result = state.responses[key]
            if previous != fingerprint:
                raise HTTPException(409, '请求标识已用于其他内容，请重新提交')
            return result
        result = action()
        state.responses[key] = (fingerprint, result)
        if len(state.responses) > 100:
            state.responses.pop(next(iter(state.responses)))
        return result


def monitor_result(state, actor):
    record = actor.last_call
    rid = actor.last_conversation_id
    if rid is not None:
        state.record_ids.add(rid)
    return {
        'record_id': rid,
        'save_warning': '结果已生成，但监控记录保存失败，暂不能提交反馈。'
                        if actor.last_monitor_error else None,
        'usage': {'input_tokens': record.prompt_tokens, 'output_tokens': record.completion_tokens,
                  'total_tokens': record.total_tokens, 'seconds': record.response_time,
                  'estimated_cost': record.cost, 'currency': 'CNY', 'model': record.model}
                 if record else None,
    }


@app.get('/api/session')
def get_session(state=Depends(session)):
    return {'id': state.id, 'model': os.getenv('DASHSCOPE_MODEL', ''),
            'scope': 'local-prototype'}


@app.get('/api/health')
def health():
    try:
        with get_db_connection() as conn:
            conn.execute('SELECT 1')
        return {'database': True}
    except Exception:
        return {'database': False}


@app.get('/api/sections')
def sections():
    return get_sections('概率论')


@app.get('/api/topics')
def topics(section: str = Query(min_length=1, max_length=300)):
    return get_topics('概率论', section)


@app.get('/api/chats')
def chats(state=Depends(session)):
    # 本机单用户原型：列出本地知识问答历史，不代表登录用户隔离。
    return get_chat_list()


@app.get('/api/chats/{chat_id}/history')
def chat_history(chat_id: UUID, state=Depends(session)):
    rows = get_history(limit=None, chat_id=str(chat_id))
    # 恢复历史答案的反馈入口，沿用当前匿名浏览器的投票标识。
    state.record_ids.update(row['record_id'] for row in rows if row['record_id'] is not None)
    return rows


@app.post('/api/qa')
def qa(body: Question, state=Depends(session)):
    def action():
        # 在保存本轮之前读取同一聊天的旧问答，当前问题由Agent自己追加。
        history = []
        if body.chat_id is not None:
            rows = get_history(limit=None, chat_id=str(body.chat_id))
            for row in rows:
                history.append({'role': 'user', 'content': row['question']})
                history.append({'role': 'assistant', 'content': row['answer']})
        actor = create_assistant(client=model_client())
        answer = (actor.rag(body.question, history=history)
                  if body.chat_id is not None else actor.rag(body.question))
        result = monitor_result(state, actor)
        history_id = None
        history_warning = None
        if body.chat_id is not None:
            try:
                # 只存整次任务的最终问答，不在模型调用记录循环中重复保存。
                record = copy(actor.last_call)
                if record is None:
                    raise ValueError('没有可保存的最终调用记录')
                record.chat_id = str(body.chat_id)
                record.session_id = actor.session_id
                record.answer = answer
                history_id = save_history(
                    record, body.question, '概率论',
                    conversation_id=actor.last_conversation_id,
                    usage=result['usage'],
                )
            except Exception:
                log.exception('Chat history save failed')
                history_warning = '答案已生成，但聊天历史保存失败；当前答案仍可查看。'
        return {'question': body.question, 'answer': answer,
                # 当前Agent未单独返回引用列表；不额外搜索或替换工具。
                'sources': [],
                'chat_id': str(body.chat_id) if body.chat_id else None,
                'history_id': history_id, 'history_warning': history_warning,
                **result}
    return once(state, 'qa', body, action)


@app.post('/api/practice/questions')
def practice_question(body: PracticeQuestion, state=Depends(session)):
    def action():
        actor = PracticeWithRecord(model_client())
        try:
            question, _ = actor.ask(body.section, body.topic)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        state.exercise = actor
        return {'exercise_id': actor.session_id, 'question': question,
                'section': body.section, 'topic': body.topic, **monitor_result(state, actor)}
    return once(state, 'practice-question', body, action)


@app.post('/api/practice/{exercise_id}/judge')
def practice_judge(exercise_id: UUID, body: Explanation, state=Depends(session)):
    def action():
        actor = state.exercise
        if actor is None or actor.session_id != str(exercise_id):
            raise HTTPException(409, '练习已过期或已换题，请重新出题')
        result, _ = actor.judge(body.user_answer)
        return {'exercise_id': actor.session_id, 'user_answer': body.user_answer,
                'evaluation': result.model_dump(), **monitor_result(state, actor)}
    return once(state, 'practice-judge:' + str(exercise_id), body, action)


@app.post('/api/feedback')
def feedback(body: Feedback, state=Depends(session)):
    with state.lock:
        if body.record_id not in state.record_ids:
            raise HTTPException(403, '此记录不属于当前浏览器会话，或会话已过期')
        fid = save_feedback(body.record_id, 'user', score=body.score, user_id=state.id)
    return {'id': fid, 'score': body.score}


@app.get('/api/dashboard')
def dashboard(limit: int = Query(default=50, ge=1, le=200)):
    # 本地原型的全库视图；非登录用户账单。
    with get_db_connection() as conn:
        stats = conn.execute('''SELECT COUNT(*), COALESCE(SUM(total_tokens),0),
            COALESCE(SUM(cost),0), COALESCE(AVG(response_time),0) FROM conversations''').fetchone()
        daily = conn.execute('''SELECT (timestamp AT TIME ZONE 'Asia/Shanghai')::date AS day,
            COUNT(*), SUM(total_tokens), SUM(cost) FROM conversations
            GROUP BY day ORDER BY day DESC LIMIT 14''').fetchall()
        votes = conn.execute('''SELECT COUNT(*) FILTER (WHERE score=1),
            COUNT(*) FILTER (WHERE score=-1) FROM feedback WHERE source='user' ''').fetchone()
        records = conn.execute('''SELECT id, question, answer, purpose, model, total_tokens,
            response_time, cost, timestamp, session_id, user_answer, prompt, instructions
            FROM conversations ORDER BY timestamp DESC, id DESC LIMIT %s''', (limit,)).fetchall()
    return {'scope':'database', 'stats':dict(zip(['calls','tokens','cost','seconds'],stats)),
            'daily':[dict(zip(['date','calls','tokens','cost'],r)) for r in reversed(daily)],
            'feedback':{'up':votes[0], 'down':votes[1]},
            'records':[dict(zip(['id','question','answer','purpose','model','tokens','seconds',
                'cost','timestamp','session_id','user_answer','prompt','instructions'],r)) for r in records]}


DIST = ROOT / 'frontend' / 'dist'
if DIST.exists():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')


@app.get('/', include_in_schema=False)
def frontend():
    if not (DIST / 'index.html').exists():
        raise HTTPException(503, '前端尚未构建，请在frontend执行npm run build')
    return FileResponse(DIST / 'index.html')
