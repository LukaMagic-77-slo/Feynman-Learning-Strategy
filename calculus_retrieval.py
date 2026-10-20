"""Small-corpus exact dense/BM25 retrieval, fused at the parent level."""
from collections import Counter
import math
import re
import unicodedata

import numpy as np

MODES = ("dense_baseline", "dense", "bm25", "hybrid", "hybrid_bm25_2")


def lexical_tokens(text):
    """Chinese character bigrams + Latin/math tokens; no segmentation dependency.

    Preserve negations and operator direction. Normalize only spelling aliases,
    not mathematical equivalence. This is not a symbolic algebra matcher.
    """
    text = unicodedata.normalize("NFKC", text).lower()
    for old, new in (("cauchy", "柯西"), ("heine", "海涅"),
                     ("bolzano", "波尔查诺"), ("weierstrass", "魏尔斯特拉斯"),
                     (r"\varepsilon", "epsilon"), (r"\epsilon", "epsilon"),
                     ("ε", "epsilon"), (r"\delta", "delta"), ("δ", "delta"),
                     (r"\infty", "infinity"), ("∞", "infinity"),
                     (r"\to", "→"), (r"\leq", "≤"), (r"\geq", "≥")):
        text = text.replace(old, new)
    tokens = []
    for part in re.findall(r"[\u4e00-\u9fff]+|[a-z]+|\d+(?:\.\d+)?|[≤≥≠<>→=+*/^-]", text):
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            tokens.extend(part[i:i+2] for i in range(len(part)-1))
            if len(part) == 1:
                tokens.append(part)
        else:
            tokens.append(part)
    return tokens


class BM25:
    def __init__(self, texts, k1=1.5, b=0.75):
        self.docs = [Counter(lexical_tokens(t)) for t in texts]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.average = sum(self.lengths) / max(1, len(self.docs))
        df = Counter(t for d in self.docs for t in d)
        self.idf = {t: math.log(1 + (len(self.docs)-n+0.5)/(n+0.5)) for t, n in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query):
        terms = set(lexical_tokens(query))
        return [
            sum(self.idf.get(t, 0) * d[t] * (self.k1+1) /
                (d[t] + self.k1*(1-self.b+self.b*length/(self.average or 1)))
                for t in terms if d[t])
            for d, length in zip(self.docs, self.lengths)
        ]


def parent_ranking(children, scores, positive_only=False):
    best = {}
    for child, score in zip(children, scores):
        if positive_only and score <= 0:
            continue
        pid, cid = child["parent_id"], child["id"]
        if pid not in best or (-float(score), cid) < (-best[pid][0], best[pid][1]):
            best[pid] = (float(score), cid)
    return sorted(((pid, score, cid) for pid, (score, cid) in best.items()),
                  key=lambda r: (-r[1], r[0]))


def rrf(rankings, k=60, weights=None):
    """Each branch contributes once per parent; missing candidates add zero."""
    scores = {}
    if weights is None:
        weights = [1] * len(rankings)
    if len(weights) != len(rankings) or any(w <= 0 for w in weights):
        raise ValueError("RRF weights must be positive and match the rankings")
    for ranking, weight in zip(rankings, weights):
        seen = set()
        for pid, *_ in ranking:
            if pid in seen:
                continue
            seen.add(pid)
            scores[pid] = scores.get(pid, 0.0) + weight/(k+len(seen))
    return sorted(scores, key=lambda pid: (-scores[pid], pid)), scores


class RetrievalSnapshot:
    """One consistent filtered DB snapshot; deliberately no stale global cache."""
    def __init__(self, rows):
        self.parents = {p["id"]: p for p, _, _ in rows}
        self.children = [c for _, c, _ in rows]
        self.vectors = np.asarray([v for _, _, v in rows], dtype=np.float32)
        self.lexical = BM25([c["text"] for c in self.children])

    def rank(self, query, vector, mode="hybrid", num_results=5, window=20):
        if mode not in MODES:
            raise ValueError(f"Unknown retrieval mode: {mode}")
        if not self.children:
            return []
        dense_scores = self.vectors @ np.asarray(vector, dtype=np.float32)
        children, scores = self.children, dense_scores
        if mode == "dense_baseline":
            pairs = [(c, s) for c, s in zip(children, scores) if c["kind"] != "question"]
            children, scores = zip(*pairs) if pairs else ([], [])
        dense = parent_ranking(children, scores)
        lexical = parent_ranking(self.children, self.lexical.scores(query), positive_only=True)
        # Widen the candidate pool if the caller requests more than the default.
        size = max(window, num_results)
        dr = {pid: (i+1, score, cid) for i, (pid, score, cid) in enumerate(dense[:size])}
        br = {pid: (i+1, score, cid) for i, (pid, score, cid) in enumerate(lexical[:size])}
        if mode in ("hybrid", "hybrid_bm25_2"):
            weights = (1, 2) if mode == "hybrid_bm25_2" else (1, 1)
            ordered, fused = rrf((dense[:size], lexical[:size]), weights=weights)
        else:
            ranking = lexical if mode == "bm25" else dense
            ordered, fused = [r[0] for r in ranking], {}
        results = []
        for pid in ordered[:num_results]:
            p = self.parents[pid]
            d, b = dr.get(pid), br.get(pid)
            results.append({
                "知识点id": pid, "课程": p["course"], "章节": p["group"], "主题": p["topic"],
                "知识点内容": p["content"]+"\n证明思路或理解要点："+p["proof_sketch"],
                "关键词": p["keywords"], "使用范围": p["scope"], "来源": p.get("source"),
                "检索方式": mode,
                "相似度": d[1] if d else None,
                "BM25分数": b[1] if b else None, "RRF分数": fused.get(pid),
                "向量排名": d[0] if d else None, "BM25排名": b[0] if b else None,
                "命中子块": (b if mode == "bm25" else d or b)[2],
                "向量命中子块": d[2] if d else None, "BM25命中子块": b[2] if b else None,
            })
        return results
