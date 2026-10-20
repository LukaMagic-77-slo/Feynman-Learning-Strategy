# 函数与极限：80 道独立知识理解问题

主文件：[`calculus_independent_80.json`](calculus_independent_80.json)。每条均有 `id`、`question`、`relevant_ids`、`type` 和 `source`。`relevant_ids` 是可接受的知识条目 ID 列表；对多知识点问题，可按“命中任一 ID”统计 Hit@k，并另报完整覆盖率，避免两种口径混淆。

本集覆盖 `data/calculus/catalog.json` 中“函数与极限”的全部 53 个条目。题目限定于概念、定理条件、适用边界、反例与证明思路，没有要求具体求极限的计算题。公开提问来源的题目是根据英文讨论主题独立改写的中文问题，并非逐字翻译，也不是本产品真实用户日志；其余题目据知识条目与常见误区独立编写。公开链接保存在每条题目的 `source.url` 中。

本集没有进入知识索引，也未用于撰写现有典型问法、开发 42 题或调整 BM25/RRF 权重。生成脚本 [`build_calculus_independent.py`](build_calculus_independent.py) 会核对题数、ID、覆盖范围，以及与开发题和典型问法的逐字重复。后续评测前应固定候选检索参数；若基于本集结果再次调参，本集就不再是最终独立测试集。
