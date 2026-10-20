import unittest

from calculus_index import build_chunks
from calculus_retrieval import BM25, RetrievalSnapshot, lexical_tokens, parent_ranking, rrf
from tests.test_calculus_chunks import CharacterTokenizer


class HybridTests(unittest.TestCase):
    def test_bm25_no_matches_and_rare_terms(self):
        bm = BM25(["极限 极限 数列", "极限 柯西", "函数 连续"])
        self.assertEqual(bm.scores("不存在词abcdef"), [0, 0, 0])
        self.assertGreater(bm.scores("Cauchy")[1], bm.scores("Cauchy")[0])
        self.assertEqual(lexical_tokens("Cauchy"), lexical_tokens("柯西"))
        self.assertNotEqual(lexical_tokens("x<0"), lexical_tokens("x>0"))
        self.assertTrue(all(score >= 0 for score in bm.scores("极限")))

    def test_parent_dedup_and_rrf_missing_branch(self):
        children = [{"parent_id": "a", "id": "a:1"}, {"parent_id": "a", "id": "a:2"},
                    {"parent_id": "b", "id": "b:1"}]
        ranking = parent_ranking(children, [0.9, 0.8, 0.7])
        self.assertEqual([r[0] for r in ranking], ["a", "b"])
        ids, scores = rrf([ranking, [("b", 9, "b:1"), ("b", 8, "b:2")]])
        self.assertEqual(ids, ["b", "a"])
        self.assertAlmostEqual(scores["a"], 1/61)
        self.assertAlmostEqual(scores["b"], 1/62+1/61)
        weighted_ids, weighted_scores = rrf([ranking, [("b", 9, "b:1")]], weights=(1, 2))
        self.assertEqual(weighted_ids[0], "b")
        self.assertAlmostEqual(weighted_scores["b"], 1/62+2/61)
        with self.assertRaises(ValueError):
            rrf([ranking], weights=(1, 2))

    def test_question_chunks_not_answer_or_baseline(self):
        entry = {"id": "a", "topic": "测试", "group": "组", "keywords": [],
                 "scope": "qa_only", "content": "完整陈述", "proof_sketch": "证明",
                 "typical_questions": [{"text": "误解的问法", "origin": "authored_from_knowledge"}]}
        parents, children = build_chunks({"entries": [entry]}, CharacterTokenizer())
        self.assertFalse(parents[0]["practice_eligible"])
        rows = [(parents[0], c, [1., 0.] if c["kind"] == "question" else [0., 1.])
                for c in children]
        snapshot = RetrievalSnapshot(rows)
        dense = snapshot.rank("误解的问法", [1., 0.], "dense")
        baseline = snapshot.rank("误解的问法", [1., 0.], "dense_baseline")
        self.assertIn(":question:", dense[0]["命中子块"])
        self.assertNotIn(":question:", baseline[0]["命中子块"])
        self.assertNotIn("误解", dense[0]["知识点内容"])
        self.assertEqual(snapshot.rank("abcdefgh", [1., 0.], "bm25"), [])
        self.assertEqual(RetrievalSnapshot([]).rank("问题", [1., 0.]), [])

    def test_question_must_not_truncate_or_fake_provenance(self):
        entry = {"id": "a", "topic": "标题", "scope": "review", "content": "条件",
                 "proof_sketch": "说明", "typical_questions": [
                     {"text": "问"*130, "origin": "authored_from_knowledge"}]}
        with self.assertRaises(ValueError):
            build_chunks({"entries": [entry]}, CharacterTokenizer())
        entry["typical_questions"] = [{"text": "问题", "origin": "public_question_inspired"}]
        with self.assertRaises(ValueError):
            build_chunks({"entries": [entry]}, CharacterTokenizer())


if __name__ == "__main__":
    unittest.main()
