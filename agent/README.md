# Agent：从手写循环到 LangChain

本目录保留两种 Agent 实现，用来对照“自己组织协议”和“框架组织流程”的差异。当前入口使用 LangChain；源码保持原位置，没有把旧代码复制成多个项目。

## 先分清两组文件

| 文件 | 阶段 | 职责 |
| --- | --- | --- |
| `register_tools.py` | 手写 Agent | 保存工具定义列表与名称到函数的映射 |
| `tools.py` | 手写 Agent | 通过自定义装饰器注册搜索工具，缓存向量索引 |
| `agentloop.py` | 手写 Agent | 直接请求模型，解析 function_call、执行函数并回传结果 |
| `langchain_tools.py` | 当前 LangChain | 用 `@tool` 包装搜索函数，复用缓存的索引 |
| `langchain_framework.py` | 当前 LangChain | 创建模型与 Agent，提供 `.rag(query, history=None)` |
| `langchain_monitor.py` | 当前 LangChain | 中间件采集每次模型请求的输入、文本、用量与耗时 |

更早的固定检索生成流程在根目录 [rag.py](../rag.py)。完整演进顺序见 [迭代导览](../docs/EVOLUTION.md)。这些文件是当前仓库中保留的实现，不保证各自与某一历史提交完全一致。

## 当前调用链

```text
main.py / evaluation/run_answers_gen.py
    └─ LangChainRAG.rag()                    # 收集内存记录，不写监控表

api.py / app.py
    └─ monitoring.assistant.create_assistant()
        └─ AgentWithRecord.rag()             # 外层管理保存与汇总
            └─ LangChainRAG.rag()
                └─ create_agent(...).invoke()
                    ├─ 模型调用 → 中间件创建 LLMCallRecord
                    ├─ 工具调用 → search → PgVectorStore.search
                    └─ 再次模型调用 → 中间件创建下一条记录
            └─ _persist_calls() → conversations
```

不是每次 `invoke()` 都只调用一次模型，也不是每个工具执行都单独创建一条 LLMCallRecord。模型要求调用工具的那轮可能只有工具调用、没有回答文本，但仍产生模型消耗。

## 谁负责 RAG？

- 资料与检索算法仍由 `data/`、`data_ingest.py`、`vector.py` 实现，框架没有替代知识库。
- 工具把检索能力暴露给模型，框架执行本地函数并回传结果。
- 系统提示词指导模型如何使用资料和回答；提供工具不等于强制每题检索。当前提示词仍需明确搜索策略，正式评估时应检查实际工具轨迹。
- 外部 `.rag()` 保持稳定，所以评估和界面不必知道内部循环由谁执行。

## 历史与记录的边界

当前 `.rag()` 接收调用方提供的历史消息，没有使用 checkpointer。每次创建新消息列表，在已有历史后追加用户问题；不会自动把上一轮内部工具消息留到下一轮。

`call_record` 在初始化时交给中间件闭包，后续用 `.clear()` 清空同一个列表。每次 `.rag()` 生成新的 `session_id`；在 `finally` 中给本轮记录补齐问题和任务 ID。此对象目前不适合并发执行多个 `.rag()`，否则列表和 session_id 可能互相覆盖；先用独立任务对象或串行调用。

模型计时只包住 `handler(request)`，不包含随后本地工具执行的耗时。当前尚未用 `wrap_tool_call` 单独计时，也不把工具用时冒充模型用时。监控入库与反馈约定见 [monitoring/README.md](../monitoring/README.md)。

## 使用与下一步

在项目根目录配置环境和数据库后：

```bash
uv run python main.py "请先搜索知识库，再解释指数分布的无记忆性"
```

该命令会调用付费模型，但不写监控表。需要在线入库时通过监控工厂进入，网页入口详见 [Web 说明](../WEB_README.md)。

后续可按顺序完善：缺失用量和异常保护、任务级记录隔离、LangChain 替身测试、工具执行追踪，再考虑框架状态持久化与费曼追问。不要为一次目录整理同时修改数据库、前端和练习业务。
