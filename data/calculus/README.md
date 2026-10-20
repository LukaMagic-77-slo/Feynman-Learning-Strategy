# 高等数学知识目录（初稿）

`catalog.json` 与现有概率论 `knowledge.json` 分开保存。`modules` 按课程学习顺序排列；目前只为第一部分“函数与极限”撰写了知识条目，后续部分只有目录。

函数与极限现有 48 条同济大学数学系《高等数学》第七版上册第一章的改写条目，另有 5 条去重后的数学分析扩展条目。教材中的星号内容一并收录；推论放在对应主条目内。逐条审阅见 `latex-review/main.tex`，网页目录由同一审阅稿生成。数学分析扩展条目标有 `scope=qa_only`，仅用于知识问答，不用于费曼练习出题；其指定参考书的版次与页码仍待核。

2026-10-20 已建立独立的 `feynman_parent_knowledge` / `feynman_child_knowledge` 索引：53 个父块、228 个子块（原有 122 个陈述/证明子块，新增 106 个典型问法子块）。原概率论 `feynman_knowledge` 表不变。网页目录支持浏览陈述与证明思路；网页聊天及练习入口仍为概率论。高数检索可通过下列命令或 `PgVectorStore.search(course="高等数学")` 调用，默认启用 BM25/RRF 混合检索。

父块保留完整陈述、附属推论、证明思路、来源和使用范围。子块分别从陈述和证明思路生成，重复条目标题，按实际 MiniLM tokenizer 计数（包括特殊 token），上限 128 tokens。优先句号、分号、逗号切分；超长文字退到字符边界，`$...$` 公式保持完整，无法容纳的公式报错。子块无重叠且可无损拼回原字段，完整上下文由父块提供。

仅子块使用 `paraphrase-multilingual-MiniLM-L12-v2` 编码为归一化的 384 维向量。从数据库加载经过课程/练习范围过滤的完整候选快照，用归一化向量内积计算精确余弦相似度，另一路用 BM25 计算文本匹配分。每路对同一父块取最佳子块，再各取 20 个不同父块，以 `1/(60+rank)` 等权 RRF 合并，默认返回 Top-10 不同父块。请求多于 20 个结果时，每路候选数扩到请求数。本批数据不需要近似索引；全量加载和内存 BM25 适用于当前小库，扩库后应再评估倒排索引、快照缓存和数据库检索方案。入库在事务内替换每个输入父块的旧子块，重复运行不会累积同名子块。移除整个父条目时需要另行同步清理数据库，本命令不会自动删除输入以外的父条目。

BM25 参数为 `k1=1.5,b=0.75`，中文采用相邻双字片段，拉丁字母、数字及运算符单独分词；统一 Cauchy/柯西等拼写和部分 LaTeX/Unicode 符号。无额外分词依赖，不删除否定词，不把数学不等式视作等价，不是公式推理引擎。BM25 零匹配的文档不参与该路排名。输出分别报告向量相似度、BM25 分数、RRF 分数、各路排名与命中子块；RRF 分数不是置信度或正确概率。

每个父条目的 `typical_questions` 包含两个短问法，独立生成 `kind=question` 的子块，保留来源元数据，超出 128 tokens 时拒绝入库而不截断。问法只用于召回，不替代知识陈述，也不作为事实答案拼入回答上下文。问法继承父块使用范围。可在 `典型问法.md` 浏览：4 条参考已核对的 Mathematics Stack Exchange 公开提问主题独立整理，102 条依据父条目编写；均不冒充真实中文查询日志。来源不是知识内容的权威校对依据。

`scope=qa_only` 在父块和检索过滤中保留；`ParentChildIndex.search(..., purpose="practice")` 会排除这 5 个父块。未来接入高数练习入口时必须使用该过滤，不可复用默认 QA 检索。

在仓库根目录运行（本地 PostgreSQL 和 `.env` 需可用；模型已缓存时可设置 `HF_HUB_OFFLINE=1`）：

```powershell
.venv/Scripts/python.exe calculus_index.py ingest
.venv/Scripts/python.exe calculus_index.py search "一致连续和逐点连续有什么区别"
.venv/Scripts/python.exe calculus_index.py search "柯西准则有什么用" --mode bm25
.venv/Scripts/python.exe calculus_index.py search "函数何时连续" --mode dense
.venv/Scripts/python.exe calculus_index.py search "函数何时连续" --mode dense_baseline
.venv/Scripts/python.exe calculus_index.py search "函数何时连续" --mode hybrid_bm25_2
.venv/Scripts/python.exe calculus_index.py evaluate
.venv/Scripts/python.exe -m evaluation.verify_calculus_index
.venv/Scripts/python.exe -m evaluation.evaluate_calculus_independent
```

`index_manifest.json` 保存源目录 SHA-256、分块文本及 token 数；向量本体存于本地数据库，不提交 Git。原始 42 道测试及 25/42 结果保留在 `evaluation/calculus_questions.json` 和 `evaluation/calculus_results.json`。`evaluate` 现运行四种方式对照，将结果写入 `evaluation/calculus_hybrid_results.json`，不覆盖旧基线。

| 方式 | Hit@5 | Hit@20 |
| --- | --- | --- |
| 原陈述/证明向量（排除问法） | 25/42，59.5% | 36/42，85.7% |
| 增加问法后的向量 | 31/42，73.8% | 37/42，88.1% |
| BM25（含问法） | 38/42，90.5% | 42/42，100% |
| 等权 RRF（含问法，当前默认） | 34/42，81.0% | 42/42，100% |

当前默认按本次需求接入 RRF，但它在开发集上低于单独 BM25，不能认定融合必然更好。本轮固定参数，没有对已知题目调权重。此开发集已用于分析问题，问法在概念和意图上可能与其重合；它不是独立盲测。即使 BM25 达到 90.5%，也不能保证新问题达到 90%，更不代表回答正确率。下一步宜用未参与设计的真实查询和人工相关性标注，比较 BM25 与混合检索，再确定最终默认方案。

新增的 80 道整理题使用固定 10 条返回结果，对照原向量、问法向量、BM25、等权 RRF、BM25：向量＝2：1 的加权 RRF。等权 RRF Hit@10 为 76/80，加权 RRF 为 75/80。完整评测见 `evaluation/calculus_independent_80_results.md` 和对应 JSON。高数检索目前默认等权 RRF、返回 10 条；概率论仍默认返回 5 条。向回答模型传入 10 个完整父块时，输入 token 会相应增加。

结果中的 `mean_ranking_ms` 仅为内存排名时间，不含模型加载、数据库连接或编码；数据库快照加载和批量编码单独记录，不等于在线单请求延迟。实现参考：[Elastic RRF 文档](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)。
