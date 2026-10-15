# 费曼练习模块

让用户选择知识主题，再把理解讲给“AI 学生”听。当前只支持数据库内已收录的概率论知识，不覆盖整门课程。

## 单轮流程

1. get_sections(course) 返回课程章节。
2. get_topics(course, section) 返回该章节主题。
3. get_knowledge(course, section, topic) 用参数化 SQL 精确取得对应知识。
4. practice.py 中的 feynman 函数根据知识生成学生角色的问题。
5. 用户输入解释。
6. judge.py 中的 judge_answer 根据问题、当次知识与解释输出结构化评价。

这里不使用向量搜索，也不需要加载嵌入模型；但知识表需要先通过根目录 vector.py 入库。SQL 查询面向 feynman_knowledge。

## 文件职责

- get_knowledge.py：数据库连接与课程 / 章节 / 主题精确查询，返回中文字段的知识记录。
- match_topic.py：本地 JSON 文档的匹配辅助函数，不是在线页面的 SQL 查询入口。
- practice.py：学生出题提示词及模型调用，返回问题和 usage。
- judge.py：解释评价提示词、模板、Pydantic 输出结构及评分调用。

评价包含 reasoning、score、missing_points、errors、suggestion。score 为 good、partial、bad 或 unjudgeable。它评判一次解释，不等于判断用户是否完全掌握整个主题。

## 推荐接入方式

界面通过 [monitoring/practice_record.py](../monitoring/practice_record.py) 的 PracticeWithRecord 使用本模块：

```python
exercise = PracticeWithRecord(client)
question, usage = exercise.ask(section, topic)
# 将同一个 exercise 对象保留到用户提交解释
evaluation, usage = exercise.judge(user_answer)
```

以上是业务调用片段，不是独立运行脚本；client 与类的导入由入口配置。FastAPI 已完成接入，可按 [项目 README](../README.md) 启动界面测试。

包装对象精确获取所选主题、保存当次资料快照，并记录出题与评价。不要用全部 documents 替代所选知识，也不要在提交解释前重新创建练习对象。直接调用基础函数不会自动写监控记录。

## 边界与贡献

用户不应在答题前收到隐藏参考内容。切换主题后应重新出题，评分必须使用该题的原始知识依据。网络或结构化输出失败不代表用户解释错误，应作为调用失败处理。

当前尚缺独立的解释评分基准集。欢迎提交匿名解释样例、遗漏 / 错误标注，以及“模型评分不合理”的复现案例，帮助完善评分可靠性。

