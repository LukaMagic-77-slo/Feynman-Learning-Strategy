import time
from langchain.agents.middleware import wrap_model_call
from langchain.messages import AIMessage
from types import SimpleNamespace
from monitoring.call_record import LLMCallRecord, calculate_cost
import os
import json

def create_monitor(call_records):
    @wrap_model_call
    def monitor_model_call(request, handler):

        messages = list(request.messages)

        if request.system_message is not None:
            messages.insert(0, request.system_message)

        prompt_snapshot = json.dumps(
            [message.model_dump(mode="json") for message in messages],
            ensure_ascii=False,
        )

        start = time.perf_counter()
        response = handler(request)
        elapsed = time.perf_counter() - start
        for message in response.result:
            if not isinstance(message, AIMessage):
                continue
            usage = message.usage_metadata
            model = os.getenv("DASHSCOPE_MODEL")

            record = LLMCallRecord(
                model=model,
                prompt=prompt_snapshot,
                instructions=request.system_message.text,
                answer=message.text,
                prompt_tokens=usage["input_tokens"],
                completion_tokens=usage["output_tokens"],
                total_tokens=usage["total_tokens"],
                response_time=elapsed,
                cost=calculate_cost(model, SimpleNamespace(**usage)),
            )

            call_records.append(record)
        return response
    return monitor_model_call