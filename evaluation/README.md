# 离线评估模块

本模块检查知识问答的两个层面：能否检索到目标知识，以及生成的答案是否正确完整。它不负责在线用户解释评分，后者位于 [practice](../practice/README.md)。

以下四步是概率论离线评估；每条知识五题不等于在线费曼练习每次出五题。

## 文件与执行顺序

从项目根目录执行，不需要切换到本目录：

| 顺序 | 命令 | 输入 | 输出 |
| --- | --- | --- | --- |
| 1 | `uv run python evaluation/run_gen_data.py` | knowledge.json | ground_truth.csv |
| 2 | `uv run python evaluation/run_eval.py` | ground_truth.csv、知识向量库 | 终端打印 Hit Rate@5、MRR@5 |
| 3 | `uv run python evaluation/run_answers_gen.py` | ground_truth.csv、知识向量库 | aqa_answers.csv |
| 4 | `uv run python evaluation/run_llm_judge.py` | aqa_answers.csv | aqa_judge_results.csv |

所有 CSV 均位于项目的 data/。运行前配置根目录 .env 并完成知识入库。步骤 1、3、4 会调用模型并消耗额度；步骤 2 需要数据库及嵌入模型，不调用生成模型。

- gen_data.py：每条知识生成五个问题，保留目标知识 ID，构建 ID 到文档的对应关系。
- search_eval.py：通过返回 ID 与目标 ID 比较产生相关性序列，计算命中率与平均倒数排名。
- llm_judge.py：定义裁判提示词、AnswerEvaluation 和评分函数；结果包含 reasoning、good/bad。
- evaluation.py：共享结构化调用、有限重试、并发进度和用量辅助逻辑。

## 结果含义

Hit Rate@5 是前五条命中目标知识的题目占比。MRR@5 是目标位置倒数的平均值，未命中计零。当前标签按知识 ID 判定，不能识别所有其他同样可回答的知识。

AQA 将问题、目标知识内容 answer_orig 与 RAG 答案 answer_llm 交给裁判。它不是对检索到的五条资料逐一评分，也不是费曼练习的用户解释评分。

## 容错和续跑

答案与裁判脚本默认六线程，使用进度条；成功结果由主线程通过临时文件替换保存，失败分别写入 aqa_answers_errors.csv 和 aqa_judge_errors.csv。失败不会阻止其他任务保存，最终仍存在失败时会提示未完成。

重新执行同一命令会补跑未完成项。答案按 (id, question) 跳过已有项；裁判还比较输入与模型 / 提示词配置指纹。生成测试问题的脚本不具有相同的逐条续跑保证。

不要同时运行多个写入同一 CSV 的实例。修改知识、RAG 或模型后请先备份旧结果并安排重新生成，避免错误复用旧答案。中断不能强制取消已经发出的请求。

## 评估边界与贡献

当前测试来自同一批小规模知识，存在合成问题偏差；LLM 裁判本身也可能误判。没有人工核验时，不能把 good 比例当作真实教学准确率。失败与重试的完整费用以服务商账单为准。

欢迎贡献独立真实问题、人工相关性标签、裁判误判案例和重复实验方案。上传结果前检查错误信息、回答内容和来源版权，移除个人信息及敏感配置。


## 高数评测入口

- `python calculus_index.py evaluate`：42 道开发题，比较原向量、问法向量、BM25、等权 RRF，结果写入 calculus_hybrid_results.json。
- `python -m evaluation.evaluate_calculus_independent`：80 道独立整理题，以 Top-10 比较五种方式（包括 BM25 权重为 2 的 RRF），同时统计 Hit@5 和 Hit@10。
- `python -m evaluation.verify_calculus_index`：校验目录、数据库父子块、384 维归一化向量与 qa_only 过滤，不调用生成模型。

高数 53 个父条目、每条两个典型问法用于索引，80 道评测题不入库。检索标注允许多个 relevant_ids，Hit@k 按至少命中其中一个计算。历史等权 RRF Hit@10=76/80，详见 calculus_independent_80_results.md；索引内容更新后需重新运行，结果不等于生成答案准确率。高数尚未把原概率论答案生成与 LLM 裁判脚本改造成完整的同一在线流程评测，因此不能宣称高数 AQA 已完成。
