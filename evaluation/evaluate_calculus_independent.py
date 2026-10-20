"""Evaluate a sealed 80-question holdout with fixed 10-parent retrieval settings."""
import hashlib
import json
from pathlib import Path
from time import perf_counter

from calculus_index import CATALOG, ParentChildIndex, ROOT, token_count
from calculus_retrieval import MODES
from vector import create_vector_store

DATASET = ROOT / "evaluation/calculus_independent_80.json"
OUTPUT = ROOT / "evaluation/calculus_independent_80_results.json"


def validate(cases, catalog):
    allowed = {entry["id"] for entry in catalog["entries"]}
    if len(cases) != 80 or len({c["id"] for c in cases}) != 80:
        raise ValueError("Expected 80 distinct question IDs")
    if len({c["question"] for c in cases}) != 80:
        raise ValueError("Duplicate questions")
    for case in cases:
        relevant = case["relevant_ids"]
        if not case["question"].strip() or not relevant or set(relevant) - allowed:
            raise ValueError(f"Invalid question or label: {case['id']}")
    dev = json.loads((ROOT / "evaluation/calculus_questions.json").read_text(encoding="utf-8"))
    indexed_questions = {q["text"] for e in catalog["entries"] for q in e.get("typical_questions", [])}
    if {c["question"] for c in cases} & ({c["question"] for c in dev} | indexed_questions):
        raise ValueError("Holdout contains an exact development/index question")


def main():
    raw = DATASET.read_bytes()
    cases = json.loads(raw)
    catalog_raw = CATALOG.read_bytes()
    validate(cases, json.loads(catalog_raw))
    store = create_vector_store()
    for case in cases:
        if token_count(store.embedder.tokenizer, case["question"]) > store.embedder.max_seq_length:
            raise ValueError(f"Query exceeds MiniLM limit: {case['id']}")
    index = ParentChildIndex(store)
    started = perf_counter()
    snapshot = index.snapshot(purpose="qa")
    snapshot_ms = (perf_counter() - started) * 1000
    expected_ids = {e["id"] for e in json.loads(catalog_raw)["entries"]}
    if set(snapshot.parents) != expected_ids or len(snapshot.children) != 228:
        raise ValueError("DB index does not match the expected 53-parent / 228-child catalog")
    started = perf_counter()
    vectors = store.embedder.encode([c["question"] for c in cases], batch_size=16,
                                    normalize_embeddings=True, show_progress_bar=True)
    encode_ms = (perf_counter() - started) * 1000
    report = {
        "dataset": "80-question held-out set, evaluated once with fixed configurations",
        "question_sha256": hashlib.sha256(raw).hexdigest(),
        "catalog_sha256": hashlib.sha256(catalog_raw).hexdigest(),
        "model": store.embedding_model,
        "metric": "Hit@5 and Hit@10: any labeled parent in top k distinct parents",
        "parameters": {"returned_parents": 10, "candidate_parents_per_branch": 20,
                       "rrf_k": 60, "bm25_k1": 1.5, "bm25_b": 0.75,
                       "weighted_rrf": {"dense": 1, "bm25": 2}},
        "snapshot_load_ms": snapshot_ms, "batch_query_encode_ms": encode_ms,
        "modes": {},
    }
    for mode in MODES:
        rows = []
        started = perf_counter()
        for case, vector in zip(cases, vectors):
            found = snapshot.rank(case["question"], vector, mode=mode, num_results=10, window=20)
            ids = [r["知识点id"] for r in found]
            expected = set(case["relevant_ids"])
            rows.append({"id": case["id"], "question": case["question"],
                         "relevant_ids": case["relevant_ids"], "retrieved_ids": ids,
                         "hit5": bool(expected & set(ids[:5])),
                         "hit10": bool(expected & set(ids))})
        report["modes"][mode] = {
            "total": len(rows), "hits5": sum(r["hit5"] for r in rows),
            "hits10": sum(r["hit10"] for r in rows),
            "hit_rate5": sum(r["hit5"] for r in rows) / len(rows),
            "hit_rate10": sum(r["hit10"] for r in rows) / len(rows),
            "ranking_ms_per_question": (perf_counter() - started) * 1000 / len(rows),
            "cases": rows,
        }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: {n: v for n, v in mode.items() if n != "cases"}
                      for k, mode in report["modes"].items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
