# 项目迭代导览

这份文档按项目的学习与开发顺序串起源码，回答两个问题：**当时在解决什么问题？现在运行的是哪一层？**

不把每轮开发复制成一套目录，不搬动现有 Python 文件，也不改变导入、数据库或前端。下面是阅读阶段，不是冻结的 release；准确的历史状态以 Git 提交为准。项目概览见 [根 README](../README.md)。

## 01 · 先让知识能被读取和检索

依次阅读：

1. [data/README.md](../data/README.md)：六字段知识条目和数据边界。
2. [data_ingest.py](../data_ingest.py)：从本地 JSON 读取、校验知识。
3. [vector.py](../vector.py)：嵌入、PostgreSQL + pgvector 持久化及相似度搜索。
4. [rag.py](../rag.py)：固定执行搜索、拼上下文、调用模型并返回答案。

这一阶段由程序固定“先搜索再生成”，没有 Agent 自主选择工具。数据与检索至今仍由后续阶段复用；`rag.py` 留作显式 RAG 的基础对照。

## 02 · 再确认检索和回答是否有效

阅读 [evaluation/README.md](../evaluation/README.md)，再按下面顺序看函数：

1. `gen_data.py`、`run_gen_data.py`：根据知识内容生成问题，保留问题到知识 ID 的映射。
2. `search_eval.py`、`run_eval.py`：按 ID 匹配相关性序列，计算 Hit Rate 与 MRR。
3. `run_answers_gen.py`：问题交给被测助手，保存参考内容和生成答案。
4. `llm_judge.py`、`run_llm_judge.py`：原有结构化裁判给出 good / bad 和理由。

迁移框架不等于更换评估标准。当前答案生成已换为 LangChain，检索指标和裁判仍沿用；`aqa_answers.csv` / `aqa_judge_results.csv` 是旧版结果，带 `_langchain` 的是新版本结果。两套文件不覆盖成同一组样本。

当前答案生成入口恢复了全量 / 6 线程，但监控列表尚未隔离，建议先单线程验证；具体边界见评估 README。不要为了验证目录而直接启动付费全量生成。

## 03 · 把问答扩展成费曼练习

阅读 [practice/README.md](../practice/README.md)：

- `match_topic.py`：本地章节、主题的匹配辅助逻辑。
- `get_knowledge.py`：用户选定章节和主题后，用 SQL 精确取知识。
- `practice.py`：模型扮演学生提出问题。
- `judge.py`：用户解释后，按题目和资料输出结构化评价。

这条业务不是搜索式 RAG，也尚未迁移成 LangChain 的自适应追问循环。当前问答升级框架，不代表练习必须跟着重写。

## 04 · 保存调用与反馈，把流程放到界面

阅读 [monitoring/README.md](../monitoring/README.md) 和 [WEB_README.md](../WEB_README.md)：

- `LLMCallRecord`：统一模型调用的字段。
- `save_record.py`、`save_feedback.py`、`record_query.py`：调用记录、赞踩改票和 Dashboard 查询。
- `practice_record.py`：练习出题和评分的监控包装。
- `app.py`：保留的 Streamlit 界面。
- `api.py`、`frontend/`：React + FastAPI 界面与接口。

早期问答的 `RAGWithRecord` 仍在 `call_record.py` 中。该文件同时含当前共用记录类，不能把整个文件当成旧版本移走或删除。

## 05 · 自己组织 Agent Loop，再接连续聊天

手写 Agent 阅读顺序：

1. [register_tools.py](../agent/register_tools.py)：工具定义与 handler 两份数据如何注册。
2. [tools.py](../agent/tools.py)：搜索工具如何加入注册表。
3. [agentloop.py](../agent/agentloop.py)：模型返回工具请求，本地执行函数，回传工具结果，再调用模型。

它把固定 RAG 变成可由模型选择搜索词和调用轮数的流程。目前作为学习实现保留，不是网页使用的循环。早期的 Agent 监控包装已迭代为下面的 LangChain 包装，不是另一个冻结副本。

历史阅读 [monitoring/HISTORY_README.md](../monitoring/HISTORY_README.md)：

- `save_history.py`：每轮最终问答一条历史，不把每次模型响应都当一条聊天消息。
- `record_query.py`：按 chat_id 分组，第一轮问题作为侧栏标题。
- `api.py`：先读历史传给助手，再保存本轮最终结果。
- `frontend/src/App.jsx` 与 `components/HistorySidebar.jsx`：展示侧栏、切换与继续聊天。

## 06 · 让框架接管循环，保留自己的业务与监控

阅读 [agent/README.md](../agent/README.md)，再按此顺序阅读：

1. [langchain_tools.py](../agent/langchain_tools.py)：搜索函数成为框架工具，缓存嵌入模型 / 索引对象。
2. [langchain_framework.py](../agent/langchain_framework.py)：创建模型和 Agent，保留 `.rag(query, history=None)`。
3. [langchain_monitor.py](../agent/langchain_monitor.py)：包住每次模型请求，创建内存调用记录。
4. [monitoring/assistant.py](../monitoring/assistant.py)：继承新类，任务退出后逐条入库、汇总并返回最终 ID。
5. `main.py`、`evaluation/run_answers_gen.py`、`api.py`：分别接上命令行、离线评估和网页。

```text
当前 CLI / 离线生成 → LangChainRAG → 只收集内存调用记录
当前网页问答       → AgentWithRecord → LangChainRAG → 记录入库
当前费曼练习       → PracticeWithRecord → 原有出题 / 评价逻辑
```

模型决策与工具执行之间的协议调度交给框架，但知识库、向量检索、提示词、评估口径、记录 schema、数据库和展示仍是项目自己的逻辑。当前历史从 SQL 显式传入，没有启用框架 checkpointer。

## 当前 ID 与数据粒度

| 标识 / 数据 | 粒度 | 由谁管理 |
| --- | --- | --- |
| `record.id` | 一次已保存的模型调用 | PostgreSQL 生成，保存后回填 |
| `session_id` | 一轮用户任务，可包含多次模型调用 | `LangChainRAG.rag()` 生成 |
| `chat_id` | 一段连续聊天，包含多轮任务 | 前端创建，API 保存、查询 |
| `last_call` | 一轮任务的页面用量汇总 | 保存包装构造副本，不重复入库 |
| `chat_history` | 一轮用户输入与最终回答 | API 在回答结束后保存 |

`AIMessage.id`、框架运行 ID 和数据库主键不是同一个标识。模型请求用量与本地工具耗时也不是同一个指标。

## 哪些继续用，哪些只是保留？

| 类别 | 文件 / 目录 |
| --- | --- |
| 当前问答执行 | `agent/langchain_*.py`、`monitoring/assistant.py` |
| 基础 / 手写学习实现 | `rag.py`、`agent/agentloop.py`、`agent/register_tools.py`、`agent/tools.py`、`RAGWithRecord`、`RAGWithUsage` |
| 持续共用 | 数据、`vector.py`、评估指标与裁判、`LLMCallRecord`、数据库读写、前端 |
| 独立保留的业务 | `practice/`、`monitoring/practice_record.py` |

保留代码不意味着它们都能通过当前工厂切换：目前没有实现版本选择器，不新增开关来改变默认运行链路。

## 本次整理与后续工作的分界

本次只整理 Markdown 导览和当前说明，不改源码、表结构、已有 CSV、接口或工具注册，不修改你的学习代码。

已知后续事项：

- `tests/test_agent_monitor.py` 仍按手写 client 注入 / 注册表设计，需适配新的框架替身；不要直接运行它而期待测试不会意外进入真实模型路径。
- 中间件目前假定 Token 用量与系统消息存在，异常保护尚需补齐。
- 共享助手的并发记录需隔离；不能一边批量调用一边清空同一份列表。
- 检索策略、工具独立追踪、模型预算、长历史裁剪和框架持久化可以分别迭代，不与本次整理混在一起。

提交前使用 `git diff` 核对自己的改动；本次不创建提交、不推送，也不宣称历史评估结果等同于最新代码的完整验证。
