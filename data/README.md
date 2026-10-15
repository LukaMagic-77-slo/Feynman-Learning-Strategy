# 概率论知识库 v1

创建日期：2026-10-14。范围：一维、具有密度的连续型随机变量；PDF、CDF、均匀、正态、指数分布。共40条，每组8条。未扩展到多维分布、参数估计或统计推断。

## 使用

主数据是 UTF-8 JSON 数组 `knowledge.json`，每条严格包含六个字段：课程、章节、主题、知识点内容、关键词、知识点id。关键词为字符串列表；其余为字符串。知识点id稳定且唯一，不随排序改变。章节采用项目自定义名称“连续型随机变量与常见分布”，不代表任何教材的章节编号。主题包含细分知识点标题，便于检索和选题。

```python
import json
from pathlib import Path

documents = json.loads(Path("data/knowledge.json").read_text(encoding="utf-8"))
```

建议索引主题、知识点内容和关键词；课程和章节可作过滤字段。若检索器只接受文本，先把关键词列表用空格连接。课程旧代码使用 question/answer/id 时，需要显式做字段映射，不能原样假定这些英文字段已存在。

## 表达与审核

这是整理撰写的中文教学条目，不是教材逐字摘录；例题为自行构造并计算。内容覆盖定义、公式、条件、计算示例及易错点。通用数学事实和自行推导与公开教材相互核对。未来用于学习评分时，还应人工审核并另外制作评分要点和测试问题；当前40条是知识库，不是已经验证的评估集。

约定：正态记法 N(μ,σ²)第二参数为方差；指数 Exp(λ)参数为率，尺度θ=1/λ；Φ为标准正态CDF；所有概率数值近似都标注≈或“约”。不把CDF连续等同于必有密度，不把密度值当作概率，不把概率区间当作置信区间。

## 核对来源与条目对应

以下是公开大学课程和开放教材，用于核对定义、公式及条件；章节编号与原教材保持在此处，而不混入项目章节字段。

- PDF/CDF，`prob-cont-pdf-*`、`prob-cont-cdf-*`：Penn State STAT 414 Lesson 14，14.1–14.3：https://online.stat.psu.edu/stat414/Lesson14
- 连续概率的面积和端点解释：OpenStax Introductory Statistics 2e 5.1：https://openstax.org/books/introductory-statistics-2e/pages/5-1-continuous-probability-functions
- 均匀分布，`prob-cont-uniform-*`：OpenStax 5.2：https://openstax.org/books/introductory-statistics-2e/pages/5-2-the-uniform-distribution；以及Penn State Lesson 14中的均匀分布部分。条件截断和平方变换示例根据定义自行推导。
- 正态分布，`prob-cont-normal-*`：Penn State STAT 414 Lesson 16：https://online.stat.psu.edu/stat414/Lesson16；OpenStax 6.1：https://openstax.org/books/introductory-statistics-2e/pages/6-1-the-standard-normal-distribution
- 指数分布，`prob-cont-exp-*`：OpenStax 5.3：https://openstax.org/books/introductory-statistics-2e/pages/5-3-the-exponential-distribution；Penn State STAT 414 Lesson 15：https://online.stat.psu.edu/stat414/Lesson15
- 无记忆性和泊松过程联系：UC Berkeley Probability for Data Science 15.4：https://textbook.prob140.org/notebooks-md/15_04_Exponential_Distribution.html

其中条件概率、归一化例题、尺度变化等条目是从定义和标准公式推导的补充解释。上述链接是查证入口，不表示页面上的所有应用假设都适用于本项目。

## 项目数据流与生成文件

knowledge.json 是人工维护的知识源；通过根目录 data_ingest.py 校验、vector.py 编码并写入 feynman_knowledge。问答和主题练习共用这张表。

| 文件 | 字段 / 用途 |
| --- | --- |
| ground_truth.csv | question、id；生成问题与目标知识对应 |
| aqa_answers.csv | id、question、answer_orig、answer_llm |
| aqa_judge_results.csv | question、id、score、reasoning、input_hash、usage_json |
| aqa_answers_errors.csv | 答案生成失败记录，仅本地保留 |
| aqa_judge_errors.csv | 裁判失败及诊断信息，仅本地保留 |

评估运行顺序、费用和续跑规则见 [evaluation/README.md](../evaluation/README.md)。更新知识后重新入库不会自动删除数据库中被 JSON 移除的条目；备份历史结果，避免误用旧评估。

## 贡献数据与发布检查

欢迎补充知识点、清晰解释、易错点和经过核验的例题。保持六字段格式、ID 唯一稳定；新增记录注明可核查来源，不提交无授权的教材整段内容。扩展学科时需同时检查课程过滤、模型提示词和前端知识范围说明。

提交前从项目根目录运行：

```bash
uv run python vector.py validate
```

当前知识库规模较小，只支持已收录知识。生成问题不是人工认证的标准题库；CSV 结果是开发样本，不应被当作通用质量承诺。上传已有答案或评分 CSV 前人工检查隐私、版权与模型生成内容；错误 CSV 默认忽略，勿直接公开含敏感诊断信息的日志。

