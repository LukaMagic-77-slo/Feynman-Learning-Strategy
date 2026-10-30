from langchain.tools import tool
from functools import lru_cache
from vector import create_vector_store

@lru_cache(maxsize=1)
def get_index():
    return create_vector_store()

@tool
def search(query: str) -> list[dict]:
    """在知识库中搜索五条和问题相关的知识,根据问题在知识库当中寻找相关知识"""
    return get_index().search(query)