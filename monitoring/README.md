# 监控接入说明

## 当前：LangChain 问答监控

`monitoring/assistant.py` 的 `AgentWithRecord` 当前继承 `LangChainRAG`，保持 `.rag(query, history=None)` 与前端监控属性兼容。React `/api/qa` 与 Streamlit 都通过不带 client 参数的 `create_assistant()` 创建助手；练习仍单独使用原生 client，不在本次迁移范围内。

当前工具由 `agent/langchain_tools.py` 的 `@tool` 定义，在 `langchain_framework.py` 中交给 `create_agent`；旧 `tools.py`、`register_tools.py` 只服务于保留的手写循环。监控层与 API 不注入、不覆盖工具 handler。当前 API 保留 `sources` 字段为空列表；答案正文中的引用由 Agent 生成，不为展示来源额外执行搜索。

职责分为三层：

1. `LangChainRAG.rag()`：清空原列表、生成本轮 `session_id`，调用框架；退出时补齐 `question` 和 `session_id`。
2. `langchain_monitor.create_monitor(call_record)`：用 `wrap_model_call` 包围每次模型调用，保存请求快照并创建 `LLMCallRecord`，追加到同一个列表；本层不写数据库。
3. `AgentWithRecord.rag()`：在父类退出后通过 `finally` 调用 `_persist_calls()`，逐条保存、回填 ID，并提供页面汇总。

任务结束（或中途异常退出）后，复用 `persist_record / save_conversation` 逐条插入 `conversations`。常规模型调用对应一个 AIMessage、一条记录；同一任务共享 `session_id` 和用户问题。没有改表结构或 Dashboard 查询。当前采用任务退出后入库，进程强制退出时内存记录仍可能丢失。

中间件闭包持有初始化时的列表，因此父类使用 `.clear()`，不能重新赋值为新列表。同一助手目前只适合串行任务；不同请求不应并发清空或共用这份记录状态。API 每次问答新建助手，而离线生成脚本的共享对象并发仍需后续隔离。

last_call 是仅供页面展示的 Token / 耗时 / 费用汇总，不额外入库；last_conversation_id 指向成功任务的最后一条模型记录，供最终答案点赞。任一保存失败会保留答案并显示保存警告。重用助手不会重复插入之前任务的记录。

Dashboard 展示已保存模型调用次数，不是用户任务次数。工具调用轮次可能没有文本，`answer` 列为空是正常表现。每条 `prompt` 保存本次输入快照；后续模型输入可包含已执行工具的返回，但尚未独立保存完整工具执行轨迹。`response_time` 是包围模型 handler 的耗时，不包含框架随后执行的本地搜索；工具耗时与任务总耗时未单独统计。费用沿用现有估算规则，未重新核价。

聊天历史已另行接入，见 [历史侧栏说明](HISTORY_README.md)；工具执行表、费曼练习的自适应多轮追问，以及本项目显式配置的调用次数上限尚未实现。框架自带执行限制不等于业务层已经配置了自己的预算。

保留原导入路径。前端或测试入口需与当前运行环境一样，保证项目根目录、monitoring和evaluation目录可被导入；本次未重构导入。

## 问答

使用 `assistant.create_assistant()` 创建 `AgentWithRecord`，调用 `assistant.rag(question)`。不要在前端再保存一遍模型记录。最终模型记录 ID 在 `assistant.last_conversation_id`，整轮汇总对象在 `assistant.last_call`；汇总对象沿用最后一条记录 ID，但其 Token、耗时和费用已求和，不是一条新的数据库记录。

若任务失败，旧的最终反馈 ID 清空，异常继续抛出，已完成的调用仍尝试保存。若模型成功但最后一条记录保存失败，答案仍返回、`last_conversation_id` 为 None；若只有前面的记录保存失败，最终 ID 仍可能有效。任意入库错误都会汇总到 `last_monitor_error`，前端应显示警告；没有最终 ID 时不能提交反馈。

## 保留的早期实现

- `call_record.py` 的 `LLMCallRecord` 与 `calculate_cost` 仍被当前中间件复用，不是废弃文件。
- 同文件的 `RAGWithRecord` 保留早期“一次 RAG 模型调用”的监控写法，不是当前工厂创建的对象。
- 手写 `RAGWithAgent` 仍在 `agent/agentloop.py`，当前 `AgentWithRecord` 已不继承它。不要仅凭类名中的 Agent 推断底层仍是手写循环。

按演进顺序阅读见 [项目迭代导览](../docs/EVOLUTION.md)。

## 费曼练习

新增practice_record.PracticeWithRecord包装原有feynman与judge_answer，不修改它们的返回值。

```python
exercise = PracticeWithRecord(client)
question, usage = exercise.ask(selected_section, selected_topic)
# 用户输入解释后，仍使用同一个exercise对象
result, usage = exercise.judge(user_answer)
```

ask内部调用get_knowledge(course, section, topic)精确查询数据库，不接收全部documents，也不加载向量模型。课程由构造函数的course参数指定，默认概率论。空结果或不属于所选主题的结果会停止出题。

对象保存在Streamlit session_state中，不要每次页面重跑都重新创建。新建练习对象会分配新的session_id；同一个对象的出题与评分共用session_id。它还保留当次资料快照，页面换主题不应修改当前题的评估依据。

- question_record_id：出题调用记录ID。
- judge_record_id：评价用户解释的调用记录ID，评价结果的赞/踩应关联它。
- last_call、last_conversation_id、last_monitor_error：最近一次调用状态。
- 原来的feynman和judge_answer仍可独立运行，但直接调用不会自动记录；前端需使用上述包装对象。

监控用途purpose取值：qa_answer、student_question、explanation_judge。练习记录保存学生问题和用户解释，裁判结果作为JSON字符串保存在answer列。

## 反馈

```python
save_feedback(conversation_id, 'user', score=1, user_id=browser_session_id)
save_feedback(conversation_id, 'user', score=-1, user_id=browser_session_id)
```

浏览器会话ID可在session_state中用uuid生成；它是匿名会话标识，不是登录认证。若省略user_id，默认anonymous，只适合本地单用户测试。同一记录、来源、用户再次提交会更新原反馈，而不是不断新增。旧反馈user_id为NULL，不合并、不删除历史数据。

get_conversations()返回对象现在包含id、question、course、purpose、session_id、user_answer。get_stats()仍统计全部已保存成功调用，空表的统计值为0。Dashboard应显示人民币估算费用；暂未加入按用途、日期或用户过滤。

## 表结构

init_db()通过ADD COLUMN IF NOT EXISTS追加purpose、session_id、user_answer；init_feedback()追加user_id及唯一索引。重复默认初始化不会删除数据。保留的drop=True仍属手动删表操作，且有外键时可能被数据库拒绝，不要在前端调用。

当前版本只保存成功模型调用，不持久化失败请求，也不能据此计算完整失败率或实际重试账单。费用仍沿用现有calculate_cost估算，未重新核价。一次练习含出题及评分两个调用，不能将调用数量当作练习人数或会话数量。

## 文件导航与初始化

- init_db.py：创建 conversations、feedback，并为已有表追加当前需要的列。
- call_record.py：调用记录对象与带记录的问答类。
- assistant.py：创建已接入监控的问答助手。
- practice_record.py：为主题练习的出题、解释评价记录两类调用。
- save_record.py / save_feedback.py：持久化调用与用户投票。
- record_query.py：读取记录与聚合统计，供界面展示。

在项目根目录配置 .env 的 DATABASE_URL，确保 PostgreSQL 启动，然后执行：

```bash
uv run python monitoring/init_db.py
```

默认初始化不删数据；不要为修复表结构随意使用 drop=True。知识与向量表由根目录 vector.py 管理，本模块不负责知识入库。

## 新前端接入

FastAPI 的 api.py 复用本目录对象，并在后端生成匿名会话身份；React 只提交按钮选择，后端执行 save_feedback。Dashboard 由接口查询数据库后交给前端渲染，当前增加了最近记录与每日 Token 展示，但仍是全库统计，不是用户权限隔离的个人页面。

练习对象需在同一会话中跨出题、评价保留。Web 会话当前存在单个 Python 进程内，不支持直接增加 workers；重启后重新出题。完整接口说明见 [WEB_README.md](../WEB_README.md)。

## 隐私与可改进方向

记录可能包含问题、用户解释和完整提示词。公开部署前需要认证、数据权限与保留策略；不要上传数据库转储或真实用户记录。欢迎改进价格配置、失败请求观测、会话持久化、统计口径和模块边界，并提供回归测试。现有 cost 仅为估算，不能替代账单。
