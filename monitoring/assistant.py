import sys
import os

from dotenv import load_dotenv
from openai import OpenAI

from vector import create_vector_store

load_dotenv()
from call_record import RAGWithRecord
def create_assistant():
    index = create_vector_store()

    return RAGWithRecord(
        index = index,
        llm_client=OpenAI(
            api_key=os.getenv('DASHSCOPE_API_KEY'),
            base_url=os.getenv('DASHSCOPE_BASE_URL'),
            timeout=60.0,
            max_retries=2,
        )
    )
