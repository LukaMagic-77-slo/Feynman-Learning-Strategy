# 知识问答历史侧栏（最小版本）

沿用 save_history.py 和 record_query.py；不改变 Agent Loop、工具注册及模型调用监控。

## ID 和保存时机

- chat_id：前端首次发送或点新建聊天时生成 UUID。同一段聊天继续提问复用它；点击侧栏加载对应 ID。
- session_id：现有监控每次 Agent 任务生成的 ID，一个 chat_id 下可以有多个 session_id。
- conversation_id：chat_history 中新增的可空字段，关联最终模型调用，恢复历史时用于反馈。

POST /api/qa 增加可选 chat_id；Agent 和监控完成后，API 复制汇总记录并将最终 answer 写入 chat_history，一次用户问答只保存一条历史。原 conversations 仍每个模型 response 一条，不增加重复计费记录。没有传 chat_id 的旧调用仍能正常执行，但不保存聊天历史。

历史表补充 timestamp、conversation_id、usage_json；init_history() 幂等补列，不删旧数据。usage_json 只用于恢复页面显示的用量，不参与 Dashboard 统计。历史保存失败不会遮盖已经生成的答案，页面会显示警告。

## 查询与界面

- GET /api/chats：get_chat_list() 按 chat_id 分组，最早插入的用户提问作完整标题；最近活动的聊天在前，最多 100 段。
- GET /api/chats/{chat_id}/history：get_history(limit=None, chat_id=...) 按 id 正序返回该聊天全部问答。
- React HistorySidebar 显示标题，长标题省略但保留悬浮全文；App 保存当前 chat_id 和问答数组。
- localStorage 仅保存当前选中 chat_id，消息正文从数据库恢复。加载、切换不请求模型。
- 手机侧栏通过“打开聊天历史”按钮展开。

## 当前范围

仅知识问答；新聊天无成功保存的问答时不会出现在数据库侧栏。旧监控 conversations 不自动转换为历史，旧 chat_history 中 chat_id 为空的行不会出现在分组侧栏。

当前是本机单用户历史，非登录用户数据隔离；不适合直接公开部署。继续提问时，API 先按 chat_id 读取历史问答，按 user / assistant 交替顺序传入 Agent，再追加当前问题；生成后才保存本轮，避免重复上下文。新聊天不继承其他聊天内容。当前传入全部已保存问答，长聊天的截断或摘要尚未实现。费曼练习历史、删除、分页等另行实现。

## 验证

根目录：uv run python -m unittest discover -s tests -v

前端：npm run test:ui（需后端运行与 Playwright 浏览器配置）。模型调用使用模拟响应。数据库真实集成检查使用回滚事务，不保留测试数据。
