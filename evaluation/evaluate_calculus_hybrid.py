"""Frozen development-set ablation; never rewrites the original baseline."""
import hashlib
import json
from time import perf_counter

from calculus_index import CATALOG, ROOT, token_count
from calculus_retrieval import MODES


def evaluate(index):
    path = ROOT / "evaluation/calculus_questions.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    model = index.store.embedder
    for case in cases:
        if token_count(model.tokenizer, case["question"]) > model.max_seq_length:
            raise ValueError("评测问题超过模型限制")
    start = perf_counter()
    snapshot = index.snapshot()
    load_ms = (perf_counter()-start)*1000
    start = perf_counter()
    vectors = model.encode([c["question"] for c in cases], batch_size=16,
                           normalize_embeddings=True, show_progress_bar=True)
    encode_ms = (perf_counter()-start)*1000
    report = {
        "dataset": "原42道知识理解开发集；已用于分析改进，非独立盲测",
        "metric": "Hit@5 / Hit@20 (distinct parents)",
        "question_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "catalog_sha256": hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        "model": index.store.embedding_model,
        "parameters": {"rrf_k": 60, "candidate_parents_per_branch": 20,
                       "bm25_k1": 1.5, "bm25_b": 0.75},
        "snapshot_load_ms": load_ms, "batch_query_encode_ms": encode_ms,
        "modes": {},
    }
    for mode in MODES:
        results = []
        start = perf_counter()
        for case, vector in zip(cases, vectors):
            found = snapshot.rank(case["question"], vector, mode, num_results=20)
            ids = [r["知识点id"] for r in found]
            relevant = set(case["relevant"])
            results.append({**case, "retrieved": ids, "hit5": bool(relevant & set(ids[:5])),
                            "hit20": bool(relevant & set(ids)), "top5_details": found[:5]})
        report["modes"][mode] = {
            "total": len(cases), "hits5": sum(r["hit5"] for r in results),
            "hit_rate5": sum(r["hit5"] for r in results)/len(cases),
            "hits20": sum(r["hit20"] for r in results),
            "hit_rate20": sum(r["hit20"] for r in results)/len(cases),
            "mean_ranking_ms": (perf_counter()-start)*1000/len(cases), "cases": results,
        }
    (ROOT/"evaluation/calculus_hybrid_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({mode: {k: v for k, v in result.items() if k != "cases"}
                      for mode, result in report["modes"].items()}, ensure_ascii=False, indent=2))
