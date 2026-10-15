import csv
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from vector import create_vector_store
from search_eval import compute_relevance_metric, hit_rate, mrr


class EvaluationIndex:
    def __init__(self, store):
        self.store = store

    def search(self, query):
        return [{"id": doc["知识点id"]} for doc in self.store.search(query)]


if __name__ == "__main__":
    with (PROJECT_DIR / "data" / "ground_truth.csv").open(
        encoding="utf-8-sig", newline=""
    ) as file:
        ground_truth = list(csv.DictReader(file))

    if not ground_truth:
        raise ValueError("ground_truth.csv没有测试问题")

    index = EvaluationIndex(create_vector_store())
    relevances = compute_relevance_metric(ground_truth, index)

    print(f"评估问题数：{len(ground_truth)}")
    print(f"Hit Rate@5：{hit_rate(relevances):.4f}")
    # 当前mrr函数返回倒数排名的总和，在这里计算平均值。
    print(f"MRR@5：{mrr(relevances):.4f}")
