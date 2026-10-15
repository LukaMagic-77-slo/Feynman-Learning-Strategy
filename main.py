import argparse
import os
from dotenv import load_dotenv
from vector import PROJECT_DIR, create_vector_store
from rag import RAG

def create_assistant():
    load_dotenv(PROJECT_DIR / '.env')
    missing = [k for k in ['DASHSCOPE_API_KEY','DASHSCOPE_BASE_URL','DASHSCOPE_MODEL'] if not os.getenv(k)]
    if missing:
        raise ValueError(f'缺少配置：{missing}')
    from openai import OpenAI
    return RAG(index=create_vector_store(), llm_client=OpenAI(
        api_key=os.environ['DASHSCOPE_API_KEY'], base_url=os.environ['DASHSCOPE_BASE_URL']),
        model=os.environ['DASHSCOPE_MODEL'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('question', nargs='?', default='概率密度为什么可以大于1？')
    args = parser.parse_args()
    print(create_assistant().rag(args.question))

if __name__ == '__main__':
    main()
