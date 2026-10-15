import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = PROJECT_DIR / "data" / "knowledge.json"

REQUIRED_FIELDS = {
    "课程",
    "章节",
    "主题",
    "知识点内容",
    "关键词",
    "知识点id",
}

def load_knowledge_data(path = DEFAULT_DATA_PATH):
    """读取并检查本地知识库，返回本地知识列表"""

    path= Path(path)

    with path.open("r", encoding="utf-8") as f:
        knowledge_data = json.load(f)

    if not isinstance(knowledge_data, list):
        raise ValueError(f"知识库数据格式错误，期望为列表，实际为 {type(knowledge_data)}")

    seen_ids = set()

    for idx, item in enumerate(knowledge_data):
        if not isinstance(item, dict):
            raise ValueError(f"知识库第 {idx} 条数据格式错误，期望为字典，实际为 {type(item)}")
        
        for field in REQUIRED_FIELDS:
            if field not in item:
                raise ValueError(f"知识库第 {idx} 条数据缺少必需字段 '{field}'")
            
        for field in REQUIRED_FIELDS - {"关键词"}:
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f"知识库第 {idx} 条数据字段 '{field}' 不能为空")

        keywords = item.get("关键词", [])

        if(
            not isinstance(keywords, list)
            or not keywords
            or any(
                not isinstance(word, str) or not word.strip()
                for word in keywords
            )
        ):
            raise ValueError(
                f"第 {idx} 条的「关键词」必须是非空字符串列表"
            )

        knowledge_id = item["知识点id"]

        if knowledge_id in seen_ids:
            raise ValueError(f"知识点 ID 重复：{knowledge_id}")

        seen_ids.add(knowledge_id)

    return knowledge_data




if __name__ == "__main__":
    documents = load_knowledge_data()

    print(f"成功读取 {len(documents)} 条知识点")

    if documents:
        print(
            json.dumps(
                documents[0],
                ensure_ascii=False,
                indent=2,
            )
        )
