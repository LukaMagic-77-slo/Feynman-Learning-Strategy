"""高数父子块索引：短子块编码，按父块聚合返回；导入模块无副作用。"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from vector import DEFAULT_EMBEDDING_MODEL, create_vector_store, vec_to_str

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "data/calculus/catalog.json"


def token_count(tokenizer, text):
    return len(tokenizer.encode(text, add_special_tokens=True, truncation=False, verbose=False))


def split_text(text, prefix, tokenizer, limit):
    """保留所有字符；优先句/分句边界，不拆 $...$ 公式，不依赖 encode 截断。"""
    if not text:
        return []
    atoms = re.findall(r"\$[^$]+\$|[^$]", text, flags=re.S)
    if "".join(atoms) != text:
        raise ValueError("数学公式分隔符不成对")
    chunks = []
    while atoms:
        count = 0
        preferred = 0
        body = ""
        for atom in atoms:
            if token_count(tokenizer, prefix + body + atom) > limit:
                break
            body += atom
            count += 1
            if atom in "。；！？\n，":
                preferred = count
        if not count:
            raise ValueError("标题或不可拆分公式超过模型上限，请人工拆写该公式")
        cut = count if count == len(atoms) else (preferred or count)
        chunks.append("".join(atoms[:cut]))
        atoms = atoms[cut:]
    assert "".join(chunks) == text
    return chunks


def build_chunks(catalog, tokenizer, limit=128):
    parents, children = [], []
    for entry in catalog["entries"]:
        if entry["scope"] not in ("review", "qa_only"):
            raise ValueError(f"未知使用范围: {entry['id']}")
        parent = dict(entry)
        parent["course"] = "高等数学"
        parent["practice_eligible"] = entry["scope"] == "review"
        if not entry["content"].strip() or not entry.get("proof_sketch", "").strip():
            raise ValueError(f"条目不完整: {entry['id']}")
        parents.append(parent)
        for kind, field in [("陈述", "content"), ("证明思路", "proof_sketch")]:
            prefix = entry["topic"] + "\n" + kind + "："
            for n, body in enumerate(split_text(entry[field], prefix, tokenizer, limit)):
                text = prefix + body
                children.append({
                    "id": f"{entry['id']}:{field}:{n:03}",
                    "parent_id": entry["id"], "kind": field, "ordinal": n,
                    "body": body, "text": text,
                    "tokens": token_count(tokenizer, text),
                })
    if len({p["id"] for p in parents}) != len(parents) or not parents:
        raise ValueError("父块 ID 重复或知识库为空")
    return parents, children


class ParentChildIndex:
    def __init__(self, store):
        self.store = store

    def ingest(self, catalog):
        from psycopg.types.json import Jsonb
        s = self.store
        if s.embedding_model != DEFAULT_EMBEDDING_MODEL or s.dimension != 384:
            raise ValueError("本期仅允许已选定的 MiniLM 384 维模型")
        limit = int(s.embedder.max_seq_length)
        parents, children = build_chunks(catalog, s.embedder.tokenizer, limit)
        vectors = s.embedder.encode([c["text"] for c in children], batch_size=16,
                                   normalize_embeddings=True, show_progress_bar=True)
        if len(vectors) != len(children) or any(len(v) != s.dimension for v in vectors):
            raise ValueError("向量数量或维度不匹配")
        serialized = [vec_to_str(v) for v in vectors]  # 拒绝非有限向量
        with s._connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(538401)")
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute("""CREATE TABLE IF NOT EXISTS feynman_child_config (
                singleton BOOLEAN PRIMARY KEY CHECK(singleton), model TEXT NOT NULL,
                dimension INTEGER NOT NULL, token_limit INTEGER NOT NULL)""")
            conn.execute("INSERT INTO feynman_child_config VALUES (TRUE,%s,%s,%s) ON CONFLICT DO NOTHING",
                         (s.embedding_model, s.dimension, limit))
            config = conn.execute("SELECT model,dimension,token_limit FROM feynman_child_config").fetchone()
            if config != (s.embedding_model, s.dimension, limit):
                raise ValueError("父子块索引配置不匹配")
            conn.execute("""CREATE TABLE IF NOT EXISTS feynman_parent_knowledge (
                parent_id TEXT PRIMARY KEY, course TEXT NOT NULL,
                practice_eligible BOOLEAN NOT NULL, payload JSONB NOT NULL)""")
            conn.execute(f"""CREATE TABLE IF NOT EXISTS feynman_child_knowledge (
                child_id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL REFERENCES feynman_parent_knowledge ON DELETE CASCADE,
                payload JSONB NOT NULL, embedding vector({s.dimension}) NOT NULL)""")
            conn.execute("CREATE INDEX IF NOT EXISTS feynman_child_parent ON feynman_child_knowledge(parent_id)")
            for parent in parents:
                conn.execute("""INSERT INTO feynman_parent_knowledge VALUES (%s,%s,%s,%s)
                    ON CONFLICT(parent_id) DO UPDATE SET course=EXCLUDED.course,
                    practice_eligible=EXCLUDED.practice_eligible, payload=EXCLUDED.payload""",
                    (parent["id"], parent["course"], parent["practice_eligible"], Jsonb(parent)))
                conn.execute("DELETE FROM feynman_child_knowledge WHERE parent_id=%s", (parent["id"],))
            for child, vector in zip(children, serialized):
                conn.execute("INSERT INTO feynman_child_knowledge VALUES (%s,%s,%s,%s::vector)",
                             (child["id"], child["parent_id"], Jsonb(child), vector))
        return parents, children

    def search(self, query, course="高等数学", num_results=5, purpose="qa"):
        if not isinstance(query, str) or not query.strip() or num_results < 1:
            raise ValueError("问题不能为空，结果数须为正")
        if purpose not in ("qa", "practice"):
            raise ValueError("purpose 必须为 qa 或 practice")
        s = self.store
        if token_count(s.embedder.tokenizer, query) > s.embedder.max_seq_length:
            raise ValueError("问题超过模型输入长度，请缩短问题，避免静默截断")
        vector = vec_to_str(s.embedder.encode(query, normalize_embeddings=True))
        with s._connect() as conn:
            config = conn.execute("SELECT model,dimension,token_limit FROM feynman_child_config").fetchone()
            if config != (s.embedding_model, s.dimension, int(s.embedder.max_seq_length)):
                raise ValueError("检索模型与索引配置不一致")
            # 全量精确余弦检索后对父块取最佳子块，避免多个子块占满 Top-5。
            rows = conn.execute("""WITH best AS (
                SELECT DISTINCT ON (p.parent_id) p.parent_id, p.payload,
                    c.child_id, c.embedding <=> %s::vector AS distance
                FROM feynman_parent_knowledge p
                JOIN feynman_child_knowledge c ON c.parent_id=p.parent_id
                WHERE p.course=%s AND (%s OR p.practice_eligible)
                ORDER BY p.parent_id, distance, c.child_id)
                SELECT payload,child_id,1-distance FROM best
                ORDER BY distance,parent_id LIMIT %s""",
                (vector, course, purpose == "qa", num_results)).fetchall()
        return [{
            "知识点id": p["id"], "课程": course, "章节": p["group"], "主题": p["topic"],
            "知识点内容": p["content"] + "\n证明思路或理解要点：" + p["proof_sketch"],
            "关键词": p["keywords"], "相似度": float(score), "命中子块": cid,
            "使用范围": p["scope"], "来源": p.get("source"),
        } for p, cid, score in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["ingest", "search", "evaluate"])
    parser.add_argument("query", nargs="?")
    parser.add_argument("--purpose", default="qa", choices=["qa", "practice"])
    args = parser.parse_args()
    store = create_vector_store()
    index = ParentChildIndex(store)
    if args.command == "ingest":
        raw = CATALOG.read_bytes()
        parents, children = index.ingest(json.loads(raw))
        report = {"model": store.embedding_model, "dimension": store.dimension,
                  "token_limit": store.embedder.max_seq_length,
                  "catalog_sha256": hashlib.sha256(raw).hexdigest(),
                  "parents": len(parents), "children": len(children),
                  "qa_only_parents": sum(not p["practice_eligible"] for p in parents),
                  "max_child_tokens": max(c["tokens"] for c in children),
                  "children_manifest": children}
        (CATALOG.parent / "index_manifest.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k!="children_manifest"}, ensure_ascii=False))
    elif args.command == "search":
        if not args.query:
            parser.error("search 需要问题")
        print(json.dumps(index.search(args.query, purpose=args.purpose), ensure_ascii=False, indent=2))
    else:
        cases = json.loads((ROOT / "evaluation/calculus_questions.json").read_text(encoding="utf-8"))
        results = []
        for case in cases:
            found = [r["知识点id"] for r in index.search(case["question"])]
            results.append({**case, "retrieved": found, "hit": bool(set(found)&set(case["relevant"]))})
        report = {"metric": "Hit@5 (distinct parents)", "dataset": "开发者编写的初步知识理解测试，非独立盲测",
                  "total": len(results), "hits": sum(r["hit"] for r in results),
                  "hit_rate": sum(r["hit"] for r in results)/len(results),
                  "cases": results}
        (ROOT / "evaluation/calculus_results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        print(json.dumps({k:v for k,v in report.items() if k!="cases"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
