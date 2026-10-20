"""从仓库根目录运行：python -m evaluation.verify_calculus_index。访问本地数据库。"""
import hashlib
import json
import math
from calculus_index import CATALOG, ROOT, ParentChildIndex, build_chunks
from vector import create_vector_store


def main():
    store = create_vector_store()
    index = ParentChildIndex(store)
    raw = CATALOG.read_bytes()
    catalog = json.loads(raw)
    parents, children = build_chunks(catalog, store.embedder.tokenizer, store.embedder.max_seq_length)
    expected = {p["id"]: p for p in parents}
    expected_children = {c["id"]: c for c in children}
    with store._connect() as conn:
        stored = conn.execute("SELECT parent_id,payload,practice_eligible FROM feynman_parent_knowledge WHERE course=%s",
                              ("高等数学",)).fetchall()
        vectors = conn.execute("""SELECT c.child_id,c.payload,c.embedding::text
            FROM feynman_child_knowledge c JOIN feynman_parent_knowledge p USING(parent_id)
            WHERE p.course=%s""", ("高等数学",)).fetchall()
    assert {i for i, _, _ in stored} == set(expected)
    for i, payload, eligible in stored:
        assert payload == expected[i]
        assert eligible == (payload["scope"] != "qa_only")
    assert {i for i, _, _ in vectors} == set(expected_children)
    for i, payload, vector in vectors:
        assert payload == expected_children[i]
        v = json.loads(vector)
        assert len(v) == 384 and all(math.isfinite(x) for x in v)
        assert abs(sum(x*x for x in v) - 1) < 1e-5
    for p in parents:
        for kind in ("content", "proof_sketch"):
            parts = [c for c in children if c["parent_id"] == p["id"] and c["kind"] == kind]
            assert "".join(c["body"] for c in sorted(parts, key=lambda c:c["ordinal"])) == p[kind]
    qa = index.search("上确界与下确界", num_results=100, purpose="qa")
    practice = index.search("上确界与下确界", num_results=100, purpose="practice")
    assert len(qa) == 53 and len(practice) == 48
    assert all(r["使用范围"] != "qa_only" for r in practice)
    assert len({r["知识点id"] for r in qa}) == len(qa)
    report = {"catalog_sha256": hashlib.sha256(raw).hexdigest(),
              "parents": len(parents), "children": len(children),
              "qa_results": len(qa), "practice_results": len(practice),
              "lossless_reconstruction": True, "vectors_finite_normalized_384d": True,
              "max_child_tokens": max(c["tokens"] for c in children)}
    (ROOT/"evaluation/calculus_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
