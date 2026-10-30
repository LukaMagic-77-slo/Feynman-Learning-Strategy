# 费曼学习平台 · Feynman Platform

阅读入口：[项目迭代导览](docs/EVOLUTION.md) · [Agent：手写版与 LangChain 版](agent/README.md)。

模块说明：[数据](data/README.md) · [评估](evaluation/README.md) · [费曼练习](practice/README.md) · [监控与反馈](monitoring/README.md) · [聊天历史](monitoring/HISTORY_README.md) · [React 前端](frontend/README.md) · [后端测试](tests/README.md) · [浏览器测试](frontend/tests/README.md)。根目录的 RAG、向量存储和 API 说明见下文及 [Web 接入说明](WEB_README.md)。

## 当前运行版本与学习脉络

本仓库保留从基础 RAG、手写 Agent Loop 到 LangChain 的学习实现，不是三个同时运行的问答后端。当前知识问答使用 **LangChain**；费曼练习仍使用原有 SQL 选题、出题和评价逻辑，没有随问答一起迁移。

| 阶段 | 阅读位置 | 当前角色 |
| --- | --- | --- |
| 1. 数据与显式 RAG | `data_ingest.py`、`vector.py`、`rag.py` | 数据和检索继续共用；`rag.py` 保留为基础实现 |
| 2. 质量评估 | `evaluation/` | 保留检索指标与裁判；答案生成已切到 LangChain |
| 3. 费曼练习 | `practice/` | 继续运行的主题练习业务 |
| 4. 监控与界面 | `monitoring/`、`app.py`、`api.py`、`frontend/` | 共用数据库与展示接口 |
| 5. 手写 Agent 与聊天历史 | `agent/agentloop.py`、`register_tools.py`、`tools.py`；历史模块 | 手写循环保留作学习对照；聊天历史继续使用 |
| 6. LangChain 接入 | `agent/langchain_*.py` | 当前问答执行层与逐次模型调用监控 |

这是阅读与演进顺序，不是独立、冻结的版本快照。为保留现有导入与入口，本次不移动源码、不复制多套项目；完整旧版本应通过 Git 历史查看。

### 上传 GitHub 前

仓库提供 `.env.example`，复制为 `.env` 后填写本机配置。`.env`、虚拟环境、Node 依赖、构建产物及评估错误 CSV 已配置忽略；已有答案和评分 CSV 仍可提交，请先人工确认隐私、版权与内容。忽略规则不能移除已经提交到历史中的秘密，若曾泄露密钥需立即撤销并更换。

提交前运行 `git status --short`，暂存后通过 `git diff --cached --stat` 和 `git diff --cached` 检查实际上传内容。不要提交真实用户记录、数据库转储或密钥。克隆者需要自行构建前端并初始化数据库，数据库内容不会随代码自动上传。代码许可证见 [MIT License](LICENSE)；引用资料与贡献数据仍需单独确认来源和使用权限。

一个围绕概率论知识库构建的学习实践项目：不仅向 AI 提问，也尝试把知识讲给 AI 听。

项目结合 LLM Zoomcamp 中的 RAG、检索评估、LLM-as-a-Judge、调用监控与用户反馈，完成从本地知识整理到学习界面的一条完整链路。后端使用 Python，提供 React + FastAPI 界面，同时保留 Streamlit 版本。

> **当前是小规模知识库演示版，仅支持数据库内已收录的知识点。**
> 初始数据包含 40 条知识，聚焦概率密度函数、分布函数、均匀分布、正态分布和指数分布，不覆盖完整概率论课程，也不支持任意学科的开放问答。模型的回答与评价可能出错，不应代替教材、教师或人工判断。

## 两种学习方式

### 1. 知识问答：先把疑问讲清楚

用户输入问题，LangChain Agent 可以调用知识库搜索工具，取得资料后继续生成回答。每轮可能有多次模型调用。界面展示回答、调用用量，并支持点赞或点踩；当前 API 的独立 `sources` 列表为空，引用主要由答案正文展示，不为填充来源列表再额外搜索。

工具可用不代表每题都必然执行检索。是否使用工具需要通过提示词、执行轨迹或进一步的程序约束验证，不能仅凭答案正确就认为搜索已经执行。

### 2. 费曼练习：这次你来当老师

用户选择章节和主题，系统通过 SQL 精确取得该主题的知识，扮演学生提出问题。用户用自己的话解释后，模型结合当前题目和知识资料评价解释，指出遗漏、错误和改进建议。

**这一部分不进行向量搜索。** 已明确主题时，直接筛选知识比再次搜索更符合当前流程。评价针对本次解释，不代表对用户整体掌握程度的权威判断。

## 整体流程

```text
data/knowledge.json
        │ 本地读取、字段校验、向量编码与入库
        ▼
PostgreSQL + pgvector
        ├─ 问答：问题 → LangChain Agent → search 工具 → 向量检索 Top 5
        │                         ↑                       │
        │                         └──── 工具结果 ──────────┘ → 回答 / 继续调用
        └─ 练习：章节 / 主题 → SQL 精确筛选 → 学生出题 → 用户解释 → LLM 评价
                                      │
                         调用记录 / 用量 / 耗时 / 估算费用
                                      ▼
                            conversations + feedback
                                      │
                         React 界面 / Streamlit / Dashboard

离线评估：知识 → 生成测试问题 → 检索评估 → LangChain 生成答案 → 原有 LLM 裁判
```

## 项目结构

```text
feynman-platform/
├── data/                         # 原始知识、生成测试集、答案与评估结果
│   ├── knowledge.json            # 两个学习模块共用的知识源
│   ├── ground_truth.csv          # 测试问题与目标知识点 ID
│   ├── aqa_answers.csv           # 旧版 RAG 答案，保留用于对照
│   ├── aqa_judge_results.csv      # 旧版裁判结果
│   ├── aqa_answers_langchain.csv # 当前 LangChain 答案
│   ├── aqa_judge_results_langchain.csv # 当前 LangChain 答案的裁判结果
│   └── README.md                 # 数据约定、来源与审核说明
├── data_ingest.py                # 读取并校验本地知识数据
├── vector.py                     # PgVectorStore：编码、持久化、检索
├── rag.py                        # 阶段 1：显式 RAG，保留作基础实现
├── main.py                       # 当前 LangChain 命令行入口，不自动入库
├── agent/
│   ├── README.md                 # 两代 Agent 的阅读与职责对照
│   ├── agentloop.py              # 阶段 5：手写模型 / 工具循环
│   ├── register_tools.py         # 手写版工具定义与 handler 注册
│   ├── tools.py                  # 手写版搜索工具
│   ├── langchain_framework.py    # 当前 LangChainRAG：模型、Agent、rag 接口
│   ├── langchain_tools.py        # 当前搜索工具及索引缓存
│   └── langchain_monitor.py      # 当前中间件：每次模型调用生成记录
├── practice/
│   ├── get_knowledge.py          # SQL 查询章节、主题及对应知识
│   ├── match_topic.py            # 本地文档的章节 / 主题匹配辅助函数
│   ├── practice.py               # 学生角色提示词及出题函数
│   └── judge.py                  # 用户解释评价及结构化输出
├── evaluation/
│   ├── evaluation.py             # 结构化模型调用、重试与辅助工具
│   ├── gen_data.py               # 测试问题生成及知识 ID 映射
│   ├── search_eval.py            # 相关性序列、Hit Rate、MRR
│   ├── llm_judge.py              # AQA 提示词、输出结构与评分函数
│   ├── run_gen_data.py           # 生成测试集
│   ├── run_eval.py               # 运行检索评估
│   ├── run_answers_gen.py        # 并发生成答案、保存结果及失败记录
│   └── run_llm_judge.py          # 并发裁判、保存结果及失败记录
├── monitoring/
│   ├── init_db.py                # 创建 / 补充调用记录与反馈表
│   ├── call_record.py            # 共用 LLMCallRecord；保留早期 RAGWithRecord
│   ├── assistant.py              # AgentWithRecord：包装 LangChainRAG 并入库
│   ├── practice_record.py        # PracticeWithRecord：练习出题与评价监控
│   ├── save_record.py            # 调用记录写入数据库
│   ├── save_feedback.py          # 保存反馈，支持改票
│   ├── save_history.py           # 每轮最终问答保存一条聊天历史
│   ├── record_query.py           # 查询调用记录与聚合统计
│   └── README.md                 # 监控对象及接入说明
├── api.py                        # FastAPI：复用后端业务，提供接口和静态页面
├── frontend/                     # React + Vite + Tailwind 前端
├── app.py                        # 保留的 Streamlit 界面
├── tests/                        # 数据 / 业务 / API 测试
├── docs/EVOLUTION.md              # 按迭代顺序阅读代码的导览
├── WEB_README.md                  # 新前端开发、接口及会话说明
├── pyproject.toml
└── uv.lock
```

## 数据：从本地文件到知识库

数据源是 `data/knowledge.json`，不是运行时从网页抓取。每条记录包含六个字段：

| 字段 | 含义 |
| --- | --- |
| 课程 | 当前为“概率论” |
| 章节 | 当前使用项目自定义的章节名称 |
| 主题 | 具体知识点标题，用于选择和检索 |
| 知识点内容 | 定义、条件、公式、直观解释或示例 |
| 关键词 | 字符串列表，辅助知识表达与检索 |
| 知识点id | 稳定且唯一的标识，用于入库和评估匹配 |

`data_ingest.py` 校验字段和重复 ID；`vector.py` 将知识编码为向量，并写入 PostgreSQL。知识原文与向量保存在同一知识表，便于问答检索和练习精确查询共用。

目前使用多语言 SentenceTransformer 嵌入模型与余弦距离检索。向量入库按知识 ID 新增或更新，**从 JSON 删除条目不会自动删除数据库旧记录**。更换嵌入模型后应重新建立匹配的向量库，不能混用旧向量，即使维度相同。

数据的来源核对、数学记法和审核边界见 [数据说明](data/README.md)。现有内容不是经过完整教学验证的权威题库。

## RAG 与练习的核心对象

- `PgVectorStore` 管理知识向量入库与搜索；问答默认检索前 5 条知识。
- `RAG` 保留早期固定的“检索 → 构建上下文 → 构建提示词 → 调用模型”流程，不是当前网页入口。
- `RAGWithAgent` 保留手写 Agent Loop 与工具分发，当前入口不再使用这套循环。
- `LangChainRAG` 提供兼容的 `.rag(query, history=None)` 接口，内部由框架组织模型与工具调用；中间件在内存中收集 `call_record`。
- `AgentWithRecord` 包装当前 `LangChainRAG`，任务退出后逐条保存记录，并提供前端需要的汇总和最终记录 ID。
- `RAGWithRecord` 是早期基础 RAG 的监控包装，保留作学习对照。
- `PracticeWithRecord` 组织指定主题的出题与评价，并保留当次题目的知识快照，避免评价依据与题目错配。
- `LLMCallRecord` 统一表达模型、提示词、回答、Token、耗时、估算费用及调用用途。

前端负责展示和收集输入；密钥、模型请求、知识查询与数据库写入留在后端。直接使用 `LangChainRAG` 会收集内存记录，但不会自动写监控数据库；界面通过 `monitoring/assistant.py` 的工厂创建带入库的包装对象。基础 `RAG` 和练习函数也可单独调用。

## Evaluation：分别检查检索和回答

### 第一步：生成测试问题

根据每条知识生成 5 个问题，保存问题与目标知识点 ID 的对应关系。初始 40 条知识对应预期 200 个问题，实际数量以生成文件为准。问题需要人工抽查，尤其是可回答性、重复和条件完整性。

### 第二步：检索评估

用测试问题搜索知识库，将返回的知识点 ID 与目标 ID 比较，得到类似 `[0, 1, 0, 0, 0]` 的相关性序列，然后计算：

- **Hit Rate@5**：前 5 条结果中找到目标知识的题目占比。
- **MRR@5**：目标知识首次命中位置的倒数的平均值；未命中计 0，越靠前越好。

当前标签基于目标 ID，其他知识即使也能合理回答，仍可能被记为不相关。它衡量的是目标知识命中情况，不是完整的语义相关性。

### 第三步：生成 RAG 答案

`run_answers_gen.py` 当前对测试问题调用 `LangChainRAG`，将 `id`、`question`、`answer_orig` 和 `answer_llm` 保存到 `aqa_answers_langchain.csv`。参考答案来自目标知识点内容，而不是搜索出的五条资料逐条评分。旧的 `aqa_answers.csv` 不被当前脚本作为新版本结果使用。

### 第四步：AQA / LLM-as-a-Judge

裁判接收问题、参考内容和生成答案，输出 `reasoning` 与 `score`（`good` / `bad`），评判关键知识是否正确、完整，不要求逐字一致。

答案生成与裁判脚本支持并发、进度条、失败记录和断点续跑：成功结果逐条保存；失败项单独写入错误 CSV。答案按 `(id, question)` 跳过已完成项，裁判还使用输入与配置指纹判断是否需要重新评价。

当前生成脚本已配置全量数据、6 线程；但接入内存调用记录后，同一个 `LangChainRAG` 对象中的列表尚未做并发隔离。新一轮验证建议先用 `answers[:5]` 和 `max_workers=1`；增加并发前需改成任务独立对象或任务级记录隔离。不要把此问题与独立裁判请求的并发混为一谈。本次目录整理不修改评估参数或并发逻辑。

> 测试问题和参考内容来自同一小规模知识库，存在合成测试偏差。LLM 裁判也不是客观真值。当前结果用于开发对比，不应宣称为真实学生场景的准确率；后续需要独立问题、人工标注和评分一致性检查。费曼练习的系统化离线评估仍待完善。

运行顺序：

```bash
uv run python evaluation/run_gen_data.py
uv run python evaluation/run_eval.py
uv run python evaluation/run_answers_gen.py
uv run python evaluation/run_llm_judge.py
```

除检索评估外，上述流程涉及模型调用和费用。重新生成测试集前备份已有文件；知识、提示词或模型改变后，不要把旧答案当成新配置的结果，应备份并安排重新生成。不要同时运行多个写同一 CSV 的脚本。

## Monitor：调用记录、反馈与 Dashboard

数据库的主要表及职责：

| 表 | 职责 |
| --- | --- |
| `feynman_knowledge` | 知识原文、课程、章节、主题、关键词及向量 |
| `feynman_vector_config` | 嵌入模型名称与维度，用于配置一致性检查 |
| `conversations` | 模型调用内容、Token、耗时、费用估算及业务关联 |
| `feedback` | 对调用结果的用户反馈，通过记录 ID 关联 |
| `chat_history` | 一轮用户提问与最终回答，供历史侧栏恢复；不参与模型调用计费统计 |

调用用途 `purpose` 分为 `qa_answer`（问答）、`student_question`（出题）、`explanation_judge`（解释评价）。一次练习通常包含出题、评价两次模型调用，不能把调用数当作学习人数或练习次数。

LangChain 问答通过 `wrap_model_call` 在每次模型调用后创建 `LLMCallRecord`，由外层保存到 `conversations`。`record.id` 是数据库主键；`session_id` 关联一次用户任务中的多次模型调用；`chat_id` 关联连续多轮聊天。最终回答记录用于反馈，页面用量为整轮汇总，汇总不再重复入库。模型请求耗时不包含独立执行的本地搜索耗时，也不是整轮任务总耗时。

两个模块都支持结果反馈：问答关联回答记录，练习评价关联裁判记录。同一记录、来源和会话用户再次投票会更新原反馈，支持赞踩改票，避免重复点击不断新增。匿名会话 ID 不是登录身份。

模型已生成答案但记录保存失败时，仍向用户展示结果，并提示保存失败；没有记录 ID 时不能提交对应反馈。Dashboard 展示已保存的调用、Token、平均耗时、估算费用、反馈及记录详情。

**统计边界：** 当前仅持久化成功模型调用，不完整记录失败与重试费用；费用为代码中的价格规则估算，未保证实时更新，以服务商账单为准。Dashboard 是全库统计，不是按登录用户隔离的个人账单。

## 本地运行

推荐在 WSL 的 Linux 文件系统内运行项目。需要 Python 3.13+、uv、Docker，以及可用的模型服务配置。

### 1. 安装依赖并配置环境

在项目根目录执行：

```bash
uv sync
```

自行创建 `.env`（不要提交真实密钥）：

```dotenv
DASHSCOPE_API_KEY=你的密钥
DASHSCOPE_BASE_URL=你的服务区域对应且支持当前接口的地址
DASHSCOPE_MODEL=你的账号可用且支持当前接口的模型名称
DATABASE_URL=postgresql://user:change_me@localhost:5434/feynman
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

当前问答使用 LangChain 的 OpenAI 模型适配器；练习与离线结构化裁判仍直接使用 SDK / Responses API。不能把 `agent.invoke()` 等同于固定调用 Responses API，也不能仅凭“兼容 OpenAI”就假定工具调用、结构化输出和所有供应商字段均可用。请确认所选区域、模型、接口与配额可用。首次加载嵌入模型需要下载，模型下载网络与 LLM API 网络是两个独立环节。

### 2. 首次创建数据库容器

```bash
docker run -d --name feynman-pg \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=change_me \
  -e POSTGRES_DB=feynman \
  -p 127.0.0.1:5434:5432 \
  -v feynman_pgdata:/var/lib/postgresql/data \
  pgvector/pgvector:pg17
```

示例密码仅用于本地开发，需与 `.env` 一致；已有容器不要重复创建，后续执行 `docker start feynman-pg`。数据卷持久化数据库，重启 Docker 不会清空表。普通 PostgreSQL 镜像不一定包含 vector 扩展。

### 3. 校验、入库和初始化监控表

```bash
uv run python vector.py validate
uv run python vector.py ingest
uv run python monitoring/init_db.py
```

已有知识向量不需要每次启动重新生成；更新知识后再入库。监控默认初始化不会删除历史记录；不要在真实数据上使用 `drop=True`，它会尝试删除调用表及其数据。

### 4. 启动新版界面

```bash
uv run uvicorn api:app --host 127.0.0.1 --port 8000
```

浏览器打开 **http://localhost:8000**，接口文档位于 **http://localhost:8000/docs**。

若 `frontend/dist` 尚未构建，先在安装了合适 Node.js 版本的环境中执行：

```bash
cd frontend
npm ci
npm run build
cd ..
```

日常使用已有构建时不需要运行 Node。前端开发、代理配置与接口说明见 [WEB_README.md](WEB_README.md)。

### 保留的其他入口

```bash
# Streamlit 界面
uv run streamlit run app.py

# 当前 LangChain 命令行问答（不写监控数据库）
uv run python main.py "概率密度为什么可以大于1？"

# 单独验证检索
uv run python vector.py search "指数分布为什么具有无记忆性？"
```

## 测试与当前限制

```bash
uv run python -m unittest discover -s tests -v
```

测试覆盖数据、业务链路及 API；模型操作通过替身验证，不代表真实模型质量。API Dashboard 测试可能读取本地数据库，需要有效的数据库配置。前端浏览器测试位于 `frontend/tests/`，可在配置好 Playwright 浏览器环境后执行 `npm run test:ui`。

**迁移中的测试状态：** `tests/test_agent_monitor.py` 仍按手写 Agent 的 client 注入和注册表设计，尚未适配当前 LangChain 包装类，不能宣称完整测试集已通过。迁移时先更新模型替身与中间件测试，不要直接把旧测试当作当前接线的证明；本次整理不运行可能漏掉模型替身的旧监控测试。

当前版本是本机单用户原型：没有完整登录、权限和生产部署方案。FastAPI 匿名会话保存在单进程内，闲置过期或进程重启后需要重新出题，不应直接增加多个 workers。Dashboard 含问题、解释、完整提示词等内容，**不要直接公开暴露接口或提交含个人信息的数据库 / CSV**。

导入路径、配置管理、异常处理和模块边界仍有整理空间。本项目优先跑通可理解的端到端流程，尚不是生产级学习平台。

## 欢迎参与：数据、反馈与代码改进

这个项目目前最大的限制之一是 **知识库太小**。期待有兴趣的同学共同把它变得更可靠、更有学习价值。

- **贡献知识数据**：补充已有主题的解释、例题与常见误区，或逐步扩展知识范围。请遵循六字段格式，保持 ID 唯一，注明可核查来源，确认内容有权使用。扩展新学科时还需同步调整提示词、筛选与页面范围说明，不能只添加数据就宣称支持。
- **贡献真实用户反馈**：使用点赞 / 点踩，或提交具体问题、预期答案、错误描述及复现步骤。尤其欢迎“解释哪里不清楚”和“评价哪里不合理”的反馈，请移除个人信息与密钥。
- **贡献评估数据**：提供独立于现有知识措辞的真实问题、人工相关性标注和用户解释样例，帮助检查检索、答案正确性与裁判一致性。
- **优化代码结构与逻辑**：欢迎改进导入与配置管理、业务分层、并发与超时、测试覆盖、会话持久化，以及监控统计的准确性。尽量保持已有可运行链路，附上改动理由和验证方式。

可以通过仓库 Issue 讨论问题或想法，通过 Pull Request 提交数据和代码。数据改动建议先做校验并抽查受影响的问答与练习；功能改动请附测试或最小复现步骤。请勿提交 `.env`、API 密钥、虚拟环境、个人对话和未经授权的教材全文。

希望这里不只是一个“能回答问题”的工具，而是一个能帮助我们发现理解漏洞、练习解释、逐渐把知识讲清楚的小空间。
