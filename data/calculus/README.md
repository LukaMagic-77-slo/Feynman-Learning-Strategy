# 高等数学知识目录（初稿）

`catalog.json` 与现有概率论 `knowledge.json` 分开保存。`modules` 按课程学习顺序排列；目前只为第一部分“函数与极限”撰写了知识条目，后续部分只有目录。

函数与极限现有 48 条同济大学数学系《高等数学》第七版上册第一章的改写条目，另有 5 条去重后的数学分析扩展条目。教材中的星号内容一并收录；推论放在对应主条目内。逐条审阅见 `latex-review/main.tex`，网页目录由同一审阅稿生成。数学分析扩展条目标有 `scope=qa_only`，仅用于知识问答，不用于费曼练习出题；其指定参考书的版次与页码仍待核。

2026-10-20 已建立独立的 `feynman_parent_knowledge` / `feynman_child_knowledge` 索引：53 个父块、122 个子块。原概率论 `feynman_knowledge` 表不变。网页目录支持浏览陈述与证明思路；网页聊天及练习入口仍为概率论。高数检索可通过下列命令或 `PgVectorStore.search(course="高等数学")` 调用。

父块保留完整陈述、附属推论、证明思路、来源和使用范围。子块分别从陈述和证明思路生成，重复条目标题，按实际 MiniLM tokenizer 计数（包括特殊 token），上限 128 tokens。优先句号、分号、逗号切分；超长文字退到字符边界，`$...$` 公式保持完整，无法容纳的公式报错。子块无重叠且可无损拼回原字段，完整上下文由父块提供。

仅子块使用 `paraphrase-multilingual-MiniLM-L12-v2` 编码为归一化的 384 维向量。数据库用精确余弦距离查找子块，对同一父块保留最佳子块得分，再返回 Top-5 不同父块；本批数据不需要近似检索索引。入库在事务内替换每个输入父块的旧子块，重复运行不会累积同名子块。移除整个父条目时需要另行同步清理数据库，本命令不会自动删除输入以外的父条目。

`scope=qa_only` 在父块和检索过滤中保留；`ParentChildIndex.search(..., purpose="practice")` 会排除这 5 个父块。未来接入高数练习入口时必须使用该过滤，不可复用默认 QA 检索。

在仓库根目录运行（本地 PostgreSQL 和 `.env` 需可用；模型已缓存时可设置 `HF_HUB_OFFLINE=1`）：

```powershell
.venv/Scripts/python.exe calculus_index.py ingest
.venv/Scripts/python.exe calculus_index.py search "一致连续和逐点连续有什么区别"
.venv/Scripts/python.exe calculus_index.py evaluate
.venv/Scripts/python.exe -m evaluation.verify_calculus_index
```

`index_manifest.json` 保存源目录 SHA-256、分块文本及 token 数；向量本体存于本地数据库，不提交 Git。首轮 42 道知识理解开发测试命中 25 道，Hit@5 为 59.5%，未达到 90%。完整标注与结果见 `evaluation/calculus_questions.json` 和 `evaluation/calculus_results.json`。这些问题由开发者编写，尚非独立盲测；指标仅评价检索，不代表生成回答准确率。后续应补充人工审定的独立测试集后再判断模型与切分方案是否达标。
