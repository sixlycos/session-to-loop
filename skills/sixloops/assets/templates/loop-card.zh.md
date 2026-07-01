# {{name}}

## 选择建议

推荐回复：`{{recommended_action}}`

启动方式：`{{mode_display}}`

在当前对话回复其中一行：

{{start_options}}

## 执行摘要

### 1. 目标

{{first_run_goal}}

### 2. 它会替你做什么

{{user_value}}

### 2.5 改造图景

{{change_map}}

启动后会：

{{control_will_do}}

### 3. 自动运行

{{autopilot_contract}}

### 4. 启动后怎么跑

1. 观察 / 决策：{{first_run_observe}}；{{first_run_decide}}。
2. 执行：{{first_run_act}}。
3. 验证：{{first_run_verify}}
4. 交付 / 停止：更新 `{{managed_state_file}}`；停止于 {{first_run_stop_after}}；返回点：{{first_run_human_gate}}

### 4.5 推进节奏

每轮节奏：

{{managed_progression_rhythm}}

每轮必须写入：

{{managed_progression_state_updates}}

继续下一轮前必须具备：

{{managed_progression_continue_requires}}

遇到这些情况不要继续，改为停止或交还：

{{managed_progression_stop_instead}}

交接规则：

{{managed_progression_handoff_rule}}

自主决策：

{{managed_autonomy_decision_policy}}

自我迭代：

{{managed_autonomy_self_iteration}}

子角色启停：

{{managed_autonomy_subagent_control}}

交还用户：

{{managed_autonomy_human_return}}

### 5. 当前模式外

{{control_will_not}}

### 6. 验收方式

{{control_verify}}

### 7. 停止和交还

{{control_stop}}

这些动作完成前会先交还给你：

{{control_must_ask}}

### 8. 退出协议

继续下一轮，仅当：

{{exit_continue_only_if}}

返回 `DONE`，当：

{{exit_done_when}}

返回 review-needed，当：

{{exit_needs_human_when}}

返回 `BLOCKED`，当：

{{exit_blocked_when}}

返回 `BUDGET_STOPPED`，当：

{{exit_budget_stopped_when}}

## 为什么值得做

{{control_why}}

这个判断可能错在哪里：

{{where_this_may_be_wrong}}

## 证据附录

公开产物默认隐藏证据片段。完整脱敏证据见私有 `candidates.json`。

| 来源 | 信号 | 证据指针 |
| --- | --- | --- |
| {{source}} | {{signal_kind}} | {{snippet}} |
