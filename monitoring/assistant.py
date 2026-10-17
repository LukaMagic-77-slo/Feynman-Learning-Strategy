"""Agent问答的监控适配；不改变Agent Loop与数据库查询。"""
import os
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

from agent.agentloop import RAGWithAgent
from call_record import persist_record


class AgentWithRecord(RAGWithAgent):
    def __init__(self, client, course='概率论'):
        super().__init__(client=client)
        self.course = course
        self.last_call = None
        self.last_conversation_id = None
        self.last_monitor_error = None
        self.session_id = None

    def rag(self, query):
        self.call_record = []
        self.last_call = None
        self.last_conversation_id = None
        self.last_monitor_error = None
        self.session_id = str(uuid4())
        succeeded = False
        try:
            answer = self.agent_loop(query)
            succeeded = True
            return answer
        finally:
            # 后续工具或模型失败时，也保存循环已收集的成功模型响应。
            self._persist_calls(query, succeeded)

    def _persist_calls(self, query, succeeded):
        errors = []
        for record in self.call_record:
            record.question = query
            record.course = self.course
            record.purpose = 'qa_answer'
            record.session_id = self.session_id
            if record.id is None:
                _, error = persist_record(record, query, self.course)
                if error:
                    errors.append(error)

        if self.call_record:
            final = self.call_record[-1]
            # 只供界面展示的汇总，不再插入数据库，避免重复计费。
            self.last_call = replace(
                final,
                prompt_tokens=sum(r.prompt_tokens for r in self.call_record),
                completion_tokens=sum(r.completion_tokens for r in self.call_record),
                total_tokens=sum(r.total_tokens for r in self.call_record),
                response_time=sum(r.response_time for r in self.call_record),
                cost=sum(r.cost for r in self.call_record),
            )
            if succeeded:
                self.last_conversation_id = final.id
        self.last_monitor_error = '; '.join(errors) or None


def create_assistant(client=None):
    if client is None:
        client = OpenAI(
            api_key=os.environ['DASHSCOPE_API_KEY'],
            base_url=os.environ['DASHSCOPE_BASE_URL'],
            timeout=60.0,
            max_retries=2,
        )
    return AgentWithRecord(client=client)
