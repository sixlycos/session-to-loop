# {{name}}

## 先看这里

推荐回复：`{{recommended_action}}`

模式：`{{mode_display}}`

目标：

{{first_run_goal}}

在当前对话回复其中一行：

{{start_options}}

## 第一轮

1. Clarify：{{first_run_observe}}；{{first_run_decide}}。
2. Act：{{first_run_act}}。
3. Verify：{{first_run_verify}}
4. Deliver / Stop：更新 `{{managed_state_file}}`；停止于 {{first_run_stop_after}}；审查边界：{{first_run_human_gate}}

## 验证和停止

验证方式：

{{control_verify}}

停止条件：

{{control_stop}}

它会在这些情况前返回给你：

{{control_must_ask}}

当前模式下不会做：

{{control_will_not}}

## 为什么值得做

{{control_why}}

这个判断可能错在哪里：

{{where_this_may_be_wrong}}

```yaml
id: "{{id}}"
decision: "{{decision}}"
confidence: "{{confidence}}"
mechanism: "{{mechanism}}"
work_shape: "{{work_shape}}"
loop_archetype: "{{loop_archetype}}"
```

## 详情

现在可启动：`{{can_use_now}}`

可确认：`{{can_confirm}}`

可托管：`{{can_delegate}}`

托管前缺少：

- {{missing_before_delegate}}

下一步：`{{next_action}}`

## 摘要

{{summary}}

## 触发时机

- {{trigger}}

## 建议产物

- {{artifact}}

## 机制判断

为什么是这个机制：

{{why_this_mechanism}}

为什么不更小：

{{why_not_smaller}}

为什么不更自动：

{{why_not_more_autonomous}}

## 验证框

主验证：

{{primary_verifier}}

检查者：

{{checker}}

需要的通过证据：

{{pass_evidence_required}}

内部状态协议：

`DONE`、`CONTINUE`、`BLOCKED`、`NEEDS_HUMAN` 或 `BUDGET_STOPPED`

## 退出协议

仅在以下条件成立时继续：

{{exit_continue_only_if}}

返回 `DONE` 的条件：

{{exit_done_when}}

返回人工审查的条件：

{{exit_needs_human_when}}

返回 `BLOCKED` 的条件：

{{exit_blocked_when}}

返回 `BUDGET_STOPPED` 的条件：

{{exit_budget_stopped_when}}

状态协议：

{{exit_status_protocol}}

## 模式阶梯

当前模式：`{{current_rung}}`

下一模式：`{{next_rung}}`

升级标准：

{{managed_promotion_criteria}}

降级标准：

{{managed_demotion_criteria}}

## Loop 经济性

预计触发频率：`{{expected_trigger_frequency}}`

预计单次成本：`{{expected_per_run_cost}}`

自动拒绝信号：

{{automatic_rejection_signals}}

人工审查负担：`{{human_review_load}}`

降级条件：

{{demote_if}}

## Loop 运行手册

目标：

{{managed_objective}}

节奏或触发：

{{managed_trigger}}

发现来源：

{{managed_discovery_sources}}

触发节奏：

`{{managed_heartbeat}}`

内部成熟度：

`{{managed_recommended_maturity}}`

用户可见模式：

`{{managed_display_mode}}`

状态文件：

`{{managed_state_file}}`

状态结构：

{{managed_state_schema}}

输入：

- {{input}}

循环步骤：

{{managed_cycle_steps}}

选择策略：

{{managed_selection_policy}}

每轮最多事项数：

{{managed_max_items_per_cycle}}

每次运行最多迭代数：

{{managed_max_iterations_per_run}}

## 验收协议

验收标准：

{{contract_success_criteria}}

验证命令：

{{contract_verifier_commands}}

评估者：

{{contract_evaluator_agent}}

需要的通过证据：

{{contract_pass_evidence_required}}

拒绝条件：

{{contract_reject_conditions}}

无进展策略：

{{contract_no_progress_policy}}

变更策略：

{{managed_change_policy}}

交付物：

{{managed_deliverables}}

验证：

- {{verification}}

恢复策略：

{{managed_resume_policy}}

失败策略：

{{managed_failure_policy}}

升级标准：

{{managed_promotion_criteria}}

降级标准：

{{managed_demotion_criteria}}

停止条件：

- {{stop_condition}}

## 安全边界

自治级别：`{{autonomy_level}}`

需要批准的动作：

- {{approval_required_action}}

人工检查点：

- {{human_checkpoint}}

预算上限：

- {{budget_caps}}

## 拒绝或降级说明

{{downgrade_notes}}

## 证据附录

公开产物默认隐藏证据片段。完整脱敏证据见私有 `candidates.json`。

| 来源 | 信号 | 证据指针 |
| --- | --- | --- |
| {{source}} | {{signal_kind}} | {{snippet}} |
