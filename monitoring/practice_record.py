"""复用现有出题和评分函数，额外保存成功调用；不改变原函数。"""
import json
import os
import time
from uuid import uuid4

from call_record import LLMCallRecord, calculate_cost, persist_record


class PracticeWithRecord:
    def __init__(self, client, course="概率论", session_id=None):
        self.client = client
        self.course = course
        self.session_id = session_id or str(uuid4())
        self.last_call = None
        self.last_conversation_id = None
        self.last_monitor_error = None
        self.question_record_id = None
        self.judge_record_id = None
        self._question = None
        self._knowledge = None

    def _reset(self):
        self.last_call = None
        self.last_conversation_id = None
        self.last_monitor_error = None

    def _save(self, instructions, prompt, answer, usage, elapsed, purpose,
              question, user_answer=None):
        record = LLMCallRecord(
            model=os.environ["DASHSCOPE_MODEL"], prompt=prompt,
            instructions=instructions, answer=answer,
            prompt_tokens=usage.input_tokens, completion_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens, response_time=elapsed,
            cost=calculate_cost(os.environ["DASHSCOPE_MODEL"], usage),
            question=question, course=self.course, purpose=purpose,
            session_id=self.session_id, user_answer=user_answer,
        )
        self.last_call = record
        self.last_conversation_id, self.last_monitor_error = persist_record(
            record, question, self.course)

    def ask(self, section, topic):
        """只使用本课程所选章节/主题的数据库知识记录出题。"""
        from practice.get_knowledge import get_knowledge
        from practice.practice import feynman, STUDENT_INSTRUCTIONS
        self._reset()
        self.question_record_id = None
        self.judge_record_id = None
        self._question = None
        self._knowledge = None
        if not isinstance(section, str) or not section.strip():
            raise ValueError("请先选择章节")
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("请先选择主题")
        documents = get_knowledge(self.course, section, topic)
        if not documents:
            raise ValueError("所选课程、章节和主题没有对应知识资料")
        if any(doc['课程'] != self.course or doc['章节'] != section
               or doc['主题'] != topic for doc in documents):
            raise ValueError("查询结果包含所选主题以外的知识，已停止出题")
        # 快照用于后续评分，避免页面切换主题后错用资料。
        knowledge = json.loads(json.dumps(documents, ensure_ascii=False))
        start = time.perf_counter()
        question, usage = feynman(self.client, STUDENT_INSTRUCTIONS, knowledge)
        elapsed = time.perf_counter() - start
        if not question.strip():
            raise ValueError("模型返回空问题")
        self._question, self._knowledge = question, knowledge
        self._save(STUDENT_INSTRUCTIONS,
                   json.dumps(knowledge, ensure_ascii=False, indent=2),
                   question, usage, elapsed, "student_question", question)
        self.question_record_id = self.last_conversation_id
        return question, usage

    def judge(self, user_answer):
        from practice.judge import judge_answer, EXPLANATION_JUDGE_INSTRUCTIONS, EXPLANATION_JUDGE_PROMPT
        if self._question is None:
            raise ValueError("请先调用ask生成问题")
        if not user_answer.strip():
            raise ValueError("用户解释不能为空")
        self._reset()
        self.judge_record_id = None
        prompt = EXPLANATION_JUDGE_PROMPT.format(
            question=self._question,
            knowledge=json.dumps(self._knowledge, ensure_ascii=False, indent=2),
            user_answer=user_answer,
        )
        start = time.perf_counter()
        result, usage = judge_answer(self.client, self._question, self._knowledge, user_answer)
        elapsed = time.perf_counter() - start
        self._save(EXPLANATION_JUDGE_INSTRUCTIONS, prompt, result.model_dump_json(),
                   usage, elapsed, "explanation_judge", self._question, user_answer)
        self.judge_record_id = self.last_conversation_id
        return result, usage
