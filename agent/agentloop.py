from call_record import LLMCallRecord
import os
import json
import time
from dotenv import load_dotenv
from . import tools  # 执行工具定义，触发注册
from .register_tools import tool_list, tool_handlers
from openai import OpenAI
from .qa_prompts import build_qa_instructions

load_dotenv()

AGENT_INSTRUCTIONS = build_qa_instructions('概率论')

client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url=os.environ["DASHSCOPE_BASE_URL"]
)

def calculate_cost(model, usage):
    cost = 0
    if "qwen3.8-flash" in  model:
        cost = (
            usage.input_tokens * 0.8
            + usage.output_tokens * 2.7
        ) / 1_000_000

    return cost

class RAGWithAgent:
    def __init__(
            self, 
            client = client,
            Agent_instruction = AGENT_INSTRUCTIONS
    ):
        self.client = client
        self.tool_list = tool_list
        self.tool_handlers = tool_handlers
        self.instruction = Agent_instruction
        self.call_record = []
        self.model = os.getenv("DASHSCOPE_MODEL")

    def make_call(self, call):
        args = json.loads(call.arguments)
        handler = self.tool_handlers[call.name]
        results = handler(**args)
        results_json = json.dumps(results, ensure_ascii=False)

        function_call_record = {
            "type": "function_call_output",
            "call_id": call.call_id,
            "output": results_json,
        }
        
        return function_call_record

    def agent_loop(self, query, history=None):
        input = [
            {"role": "system", "content": self.instruction}
        ]

        input.extend(history or [])

        input.append({
            "role": "user",
            "content": query,
        })

        while True:
            function_call = False
            start_time = time.perf_counter()

            prompt_snapshot = json.dumps(
                [
                    item.model_dump(mode="json")
                    if hasattr(item, "model_dump")
                    else item
                    for item in input
                ],
                ensure_ascii=False,
                indent=2,
            )
        
            response = self.client.responses.create(
                model = self.model,
                input = input,
                tools = self.tool_list
            )
            response_time = time.perf_counter() - start_time
            usage = response.usage
            cost = calculate_cost(self.model, usage)

            record = LLMCallRecord(
                model = self.model,
                prompt = prompt_snapshot,
                instructions = self.instruction,
                answer=response.output_text,
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
                response_time=response_time,
                cost=cost,
            )

            self.call_record.append(record)


            input.extend(response.output)

            for item in response.output:

                if item.type == "function_call":
                    function_call = True
                    call = self.make_call(item)
                    input.append(call)

                elif item.type == "message":
                    answer = item.content[0].text

            if not function_call:
                break

        return answer
