# Product Operations Parser Eval

该样例覆盖 `job_parser_v1` 的 P0 关键边界：

- “本科及以上学历”是 `HARD`，且不进入能力维度；
- “熟悉 SQL 优先”必须是 `PREFERRED`，不得误判为 `HARD`；
- 职责、数据分析和跨团队推进需要拆成独立 Requirement；
- Requirement Key 从 `R1` 连续编号；
- 每条 `source_quote` 都必须来自输入 JD；
- 输出中不得出现候选人评价、最终分数或推荐等级。

后续 Prompt 版本只有在 Preferred → Hard 误判、引用落地和 Requirement
覆盖率均不退化时，才能替换生产版本。
