import unittest
from calculus_index import build_chunks, split_text


class CharacterTokenizer:
    def encode(self, text, **kwargs):
        return [0] * (len(text) + 2)


class ChunkTests(unittest.TestCase):
    def test_no_loss_or_formula_break(self):
        text = "满足条件时。公式 $a_n\\to L$ 保持完整；还有后续说明。"
        chunks = split_text(text, "标题：", CharacterTokenizer(), 24)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(c) + 5 <= 24 for c in chunks))
        self.assertTrue(all(c.count("$") % 2 == 0 for c in chunks))
        self.assertTrue(any("$a_n\\to L$" in c for c in chunks))

    def test_oversized_formula_fails_instead_of_truncating(self):
        with self.assertRaises(ValueError):
            split_text("$" + "x"*30 + "$", "题", CharacterTokenizer(), 20)

    def test_scope_and_parent_relation(self):
        entries = [{"id": "extension", "topic": "定义", "scope": "qa_only",
                    "content": "完整条件。", "proof_sketch": "证明说明。"}]
        parents, children = build_chunks({"entries": entries}, CharacterTokenizer())
        self.assertFalse(parents[0]["practice_eligible"])
        self.assertEqual({c["parent_id"] for c in children}, {"extension"})
        self.assertEqual({c["kind"] for c in children}, {"content", "proof_sketch"})


if __name__ == "__main__":
    unittest.main()
