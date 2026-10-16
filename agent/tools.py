from vector import create_vector_store
from .register_tools import register_tool
from functools import lru_cache

search_tool = {
    "type": "function",
    'name': "search",
    'description': "在知识库中搜索五条和问题相关的知识",
    'parameters': {
        "type": "object",
        "properties": {
            'query': {
                "type": "string",
                "description": '根据问题在知识库当中寻找相关知识'
            }
        },
        "required": ['query'],
        'additionalProperties': False
    }
}

@lru_cache(maxsize=1)
def get_index():
    return create_vector_store()


@register_tool(search_tool)
def search(query):
    return get_index().search(query)

