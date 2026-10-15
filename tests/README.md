# 后端测试

测试用于检查数据格式、业务连接和接口行为，不用于证明模型教学效果。

## 运行

从项目根目录执行：

```bash
uv run python -m unittest discover -s tests -v
```

运行完整测试前安装依赖、配置 .env、初始化知识与监控表，并构建 frontend/dist。test_web_api.py 会验证静态主页，且 Dashboard 用例读取本地数据库。

## 文件职责

- test_pipeline.py：本地数据与 RAG 链路的基础检查。
- test_practice_topic.py：练习知识选择和主题关联的回归检查。
- test_web_api.py：输入校验、问答重复请求、反馈归属、练习评分对应关系及 Dashboard 响应。

模型和反馈写入通过替身验证，不调用真实付费模型。Dashboard 检查会读取数据库；因此不要将完整测试描述为完全不需要数据库的纯离线测试。

前端浏览器交互测试位于 [frontend/tests](../frontend/tests/README.md)。

## 添加测试

修复缺陷时优先添加能够复现的测试。重点检查所选知识不能串主题、题目与解释评分不能错配、保存失败不吞掉已生成答案，以及重复投票不能不断新增记录。

使用虚构问题和模型响应，不把真实密钥、用户解释、数据库快照或完整错误日志放进测试。

