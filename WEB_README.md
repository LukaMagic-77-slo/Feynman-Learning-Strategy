# React + FastAPI 前端

原Streamlit的app.py原样保留，仍可用`uv run streamlit run app.py`运行。本版新增api.py和frontend/，调用同一套Python业务与数据库。

## 日常启动

在WSL项目根目录：

```bash
cd ~/feynman-platform
docker start feynman-pg
uv run uvicorn api:app --host 127.0.0.1 --port 8000
```

浏览器打开 http://localhost:8000 。frontend/dist为构建后的前端，FastAPI同时提供静态页面与/api接口，日常运行不需要Node。

## 前端开发

frontend内包含React、Tailwind、Vite、Markdown和数学公式渲染。需要Node.js 22.12+（或支持的较新LTS）。在frontend目录：

```bash
npm ci
npm run dev
```

开发页面 http://localhost:5173 的/api请求通过Vite代理到8000端口。Python后端需同时启动。修改页面后执行`npm run build`，刷新8000端口即可看到新构建。

## 后端接口

- GET /api/session：分配HttpOnly匿名会话cookie。
- GET /api/sections，GET /api/topics?section=...：数据库精确筛选。
- POST /api/qa：通过 `monitoring.assistant.create_assistant()` 创建 `AgentWithRecord`，包装当前 `LangChainRAG`；返回最终回答、最终模型记录 ID 和整轮用量。当前独立 `sources` 列表为空，不额外执行搜索补来源。
- POST /api/practice/questions：复用PracticeWithRecord.ask(section,topic)。
- POST /api/practice/{exercise_id}/judge：复用本次练习资料快照进行评价。
- POST /api/feedback：关联该浏览器产生的记录，支持赞/踩改票。
- GET /api/dashboard：全库成功调用、估算费用、反馈和最近记录。

接口交互文档：http://localhost:8000/docs 。模型密钥和DATABASE_URL仅保存在后端.env，不放入React环境变量。

## 行为与边界

练习切换主题会清空前端旧题；后端通过exercise_id验证评分对应的当前题。浏览器不接收隐藏参考资料。操作带request_id，同会话重复提交相同已完成操作不再次调用模型；进程重启后不能保证幂等恢复。

API会话保存在单个Python进程内，闲置4小时后失效，重启后需重新出题；启动时不要增加多个workers。已保存记录和反馈留在PostgreSQL。当前仅供本机单用户原型使用，Dashboard是数据库全部成功记录，不是按登录用户隔离的个人账单。若要公开部署，需另行实现认证和数据权限。

沿用用户现有导入路径，由api.py配置monitoring、evaluation和根目录路径。Streamlit与Python业务文件不因新前端重写。

API重用嵌入模型以避免每次下载，首次问答可能较慢。网络错误在页面显示，不泄露后端配置；失败或重试的完整计费仍以模型控制台为准。不要同时操作两个前端，以免把同一学习过程拆成不同匿名会话。

## 当前后端与历史版本

当前问答链路为 `api.py → monitoring/assistant.py → agent/langchain_framework.py`。`agent/langchain_tools.py` 复用 `vector.py` 搜索；`agent/langchain_monitor.py` 收集逐次模型记录，外层包装统一入库。费曼练习仍使用 `PracticeWithRecord` 与原生模型 client，不跟随问答更换框架。

`rag.py` 和手写 `agent/agentloop.py` 保留用于学习对照，不是当前 API 问答入口。聊天历史仍由 API 查询、传入并保存，不使用框架 checkpointer；一次最终问答写一条 `chat_history`，一次模型调用写一条 `conversations`。完整阅读顺序见 [项目迭代导览](docs/EVOLUTION.md)。
