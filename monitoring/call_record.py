import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
import warnings

from rag import RAG

@dataclass
class LLMCallRecord:
    model: str
    prompt: str
    instructions: str
    answer: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    response_time: float
    cost: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: int | None = None
    question: str = ""
    course: str = "概率论"
    purpose: str = "qa_answer"
    chat_id: str | None = None
    session_id: str | None = None
    user_answer: str | None = None

def calculate_cost(model, usage):
    cost = 0
    if "qwen3.8-flash" in  model:
        cost = (
            usage.input_tokens * 0.8
            + usage.output_tokens * 2.7
        ) / 1_000_000

    return cost

class RAGWithRecord(RAG):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_call: LLMCallRecord = None
        self.last_conversation_id = None
        self.last_monitor_error = None

    def rag(self, query):
        self.last_call = None
        self.last_conversation_id = None
        self.last_monitor_error = None
        answer = super().rag(query)
        if self.last_call is not None:
            self.last_call.question = query
            self.last_call.course = self.course
            self.last_conversation_id, self.last_monitor_error = persist_record(
                self.last_call, query, self.course)
        return answer

    def llm(self, prompt):
        self.last_call = None
        start_time = time.perf_counter()
        response = self._call_llm(prompt)
        response_time = time.perf_counter() - start_time
        self._log_response(prompt, response, response_time)

        return response.output_text

    def _call_llm(self, prompt):
        input_messages = [
            {"role": "developer", "content": self.system_instructions},
            {"role": "user", "content": prompt}
        ]
        response = self.llm_client.responses.create(
            model=self.model,
            input=input_messages
        )
        return response

    def _log_response(self, prompt, response, response_time):
        usage = response.usage
        cost = calculate_cost(self.model, usage)

        call_record = LLMCallRecord(
            model = self.model,
            prompt = prompt,
            instructions = self.system_instructions,
            answer=response.output_text,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            response_time=response_time,
            cost=cost,
        )

        print(call_record)
        self.last_call = call_record


def persist_record(record, question, course):
    """监控写入失败不覆盖成功的模型结果，返回ID和可展示的错误。"""
    try:
        from save_record import save_conversation
        record_id = save_conversation(record, question, course)
        record.id = record_id
        return record_id, None
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        warnings.warn(f"监控保存失败，模型结果仍然有效：{error}", RuntimeWarning)
        return None, error
