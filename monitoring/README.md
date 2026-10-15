# 监控接入说明

保留原导入路径。前端或测试入口需与当前运行环境一样，保证项目根目录、monitoring和evaluation目录可被导入；本次未重构导入。

## 问答

继续使用assistant.create_assistant()创建RAGWithRecord，调用assistant.rag(question)。现在rag成功后自动调用save_conversation，不要在前端再重复保存同一条。记录ID在assistant.last_conversation_id，记录对象在assistant.last_call。

若模型调用失败，旧last_call和ID会清空，异常继续抛出。若模型成功但数据库写入失败，仍返回答案，last_conversation_id为None，last_monitor_error包含错误；前端应提示记录保存失败且隐藏反馈按钮。

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

