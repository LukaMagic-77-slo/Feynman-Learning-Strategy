from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from data_ingest import load_knowledge_data
from evaluation import llm_structured_retry
from concurrent.futures import ThreadPoolExecutor
from evaluation import map_progress
import pandas as pd
import os
import json
from pathlib import Path

class Questions(BaseModel):
    questions: list[str]

documents = load_knowledge_data()

QUESTION_GENERATION_INSTRUCTIONS = """
你是一名概率论测试题编写者。

你会收到一条知识记录，包含课程、章节、主题、
知识点内容、关键词和知识点ID。

请根据知识点内容，生成5个学生可能提出的问题。

要求：
1. 每个问题都必须能根据这条知识记录独立回答，
   不依赖其他知识记录或未提供的信息。
2. 五个问题应尽量覆盖不同角度，例如概念含义、
   公式条件、直观解释、常见误区或简单应用。
   只选择原记录确实支持的角度，不强行生成计算题。
3. 问题之间不得重复，也不能只是替换几个词。
4. 使用自然的学生提问方式，允许合理改写，
   不要机械照抄知识记录。
5. 问题应完整、明确；避免“它”“这个公式”等
   脱离上下文后含义不清的表达。
6. 不要在问题里直接给出答案。
7. 计算题必须提供必要条件，参数记法和单位必须明确。
8. 保持原记录的适用条件，不扩大结论范围。
9. 使用中文，不输出答案或解释。

只返回一个有效的JSON对象，格式为：
{
  "questions": [
    "问题1",
    "问题2",
    "问题3",
    "问题4",
    "问题5"
  ]
}

questions必须恰好包含5个非空字符串。
不要输出Markdown代码块或JSON之外的文字。
""".strip()

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url=os.getenv("DASHSCOPE_BASE_URL")
)

def generate_ground_truth(doc):
    user_prompt = json.dumps(doc)

    out, usage = llm_structured_retry(
        client, 
        QUESTION_GENERATION_INSTRUCTIONS,
        user_prompt,
        Questions
    )

    results = []
    for q in out.questions:
        results.append({
            "question": q,
            "id": doc["知识点id"]
        })

    return results, usage

def generate_all(documents):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = map_progress(pool, documents, generate_ground_truth)

    ground_truth = []
    usages = []

    for records, usage in results:
        ground_truth.extend(records)
        usages.append(usage)

    df_ground_truth = pd.DataFrame(ground_truth)

    output = Path(__file__).resolve().parents[1] / "data" / "ground_truth.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    df_ground_truth.to_csv(output, index=False)

    return df_ground_truth

def id_to_doc(documents):
    return {
        doc["知识点id"]: doc
        for doc in documents
    }