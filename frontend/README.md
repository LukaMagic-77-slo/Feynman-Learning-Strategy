# React 学习界面

新版界面使用 React、Vite、Tailwind、Lucide 图标及 Markdown / KaTeX 公式渲染。根目录 app.py 的 Streamlit 版本继续保留，两者不互相替代文件。

## 页面与后端

- 知识问答：输入问题、查看回答和知识来源、查看用量、提交赞踩。
- 费曼练习：选择章节 / 主题、获取问题、提交解释、阅读评价并反馈。
- 学习记录：从数据库读取调用、用量、费用估算、反馈及调用详情。

知识问答与费曼练习页均明确提示知识库较小，仅支持库内知识点。顶部课程选择可切换概率论和高等数学；高数目前仅收录“函数与极限”，其中 48 条可用于知识问答与费曼练习，5 条数学分析扩展仅用于知识问答。高数费曼练习按“函数与极限 → 第一节、第二节……”选择，未入库的模块不显示。不要把界面描述成任意学科或完整课程助手。

src/App.jsx 组织页面、请求和状态；src/styles.css 定义布局与响应式样式；src/main.jsx 是入口。业务模型调用和持久化位于 Python 后端，不在浏览器中执行。

## 安装、开发与构建

需要 Node.js 22.12+ 或兼容的较新 LTS。从本目录执行：

```bash
npm ci
npm run dev
```

另一个终端在项目根目录启动后端：

```bash
uv run uvicorn api:app --host 127.0.0.1 --port 8000
```

开发地址 http://localhost:5173，Vite 将 /api 代理到 8000。构建：

```bash
npm run build
```

构建生成 dist/，由 FastAPI 在 http://localhost:8000 提供。dist/ 被 Git 忽略，首次克隆需自行构建。提交源码与 package-lock.json，不提交 node_modules/。日常运行已有构建不需要 Node 服务。

## 会话、反馈与错误

使用后端 HttpOnly 匿名会话 cookie，不是登录系统。操作携带 request_id，重复反馈通过后端更新同一投票。已生成但保存失败的结果仍展示，并提示状态；无记录 ID 时不提供反馈。

当前练习状态由后端单进程会话保留，重启或过期后要重新出题。不要增加多个 workers 后直接假定会话共享。Dashboard 展示全库数据，不具备用户权限隔离。

不要把 API 密钥、数据库连接串放进前端变量或代码。调用详情可能包含用户输入和提示词，不应在未加权限前公开部署。

## 浏览器测试

后端需运行且本地数据库可用。从本目录执行：

```bash
npx playwright install chromium
npm run test:ui
```

测试配置还支持 PLAYWRIGHT_BASE_URL 与 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH。浏览器测试模拟模型与反馈写入，读取真实会话 / 健康检查 / Dashboard；不是付费模型端到端质量验证。

欢迎改进无障碍、手机布局、状态管理和组件拆分，请保留范围提示、保存失败状态、练习题与评价对应关系。接口细节见 [WEB_README.md](../WEB_README.md)。

