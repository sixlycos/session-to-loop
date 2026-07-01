# SixLoops 启动建议

{{summary}}

## 建议先看这里

{{proposal_overview}}

## 默认回复

{{default_next_step}}

## 怎么用

- 上面的 `start ...` / `shrink ...` / `reject ...` 是你在当前聊天里回复的一行，不是终端命令。
- 启动后智能体会先读/更新对应状态文件，连续运行到 `DONE`、review-needed、`BLOCKED` 或 `BUDGET_STOPPED`，不会每一步都问你。
- 每张卡片里有第一轮步骤、验证方式、退出协议和明确返回点；把 `claude-loops/<id>.md` 交给另一个智能体也能直接执行。

## 候选摘要

{{loop_proposals}}

## 如果不启动这些方案

如果你暂时不启动上面的方案，这些更小做法才有用。

### 固定规则

{{rules_and_memory}}

### 可复用步骤

{{skill_candidates}}

### 自动触发

{{hook_candidates}}

### 检查清单或审批门

{{approval_gates}}

### 已拒绝候选

{{rejected_candidates}}

## 简要判断

| 候选项 | 做法 | 建议 | 置信度 |
| --- | --- | --- | --- |
{{decision_index}}

可持续运行候选：

{{loop_candidates}}

## 运行备注

项目：`{{project}}`

分析窗口：`{{analysis_window}}`

输入来源：`{{transcript_source_summary}}`

脱敏：`{{redaction_status}}`

来源限制：

{{source_limitations}}

## 私有输出

- {{private_output}}

## 可共享输出

- {{shareable_output}}
