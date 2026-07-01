# {{loop_name}}

这是一份给智能体执行的运行包。按下面的执行协议运行；不要每一步都问用户。

## 1. 目标

{{goal}}

## 2. 改造图景

{{managed_change_map}}

## 3. 自动运行

{{autopilot_contract}}

## 4. 状态

先读这个文件；停止前必须更新：

`{{state_file}}`

状态结构：

{{state_schema}}

## 5. 执行范围

每轮最多处理 {{max_items_per_cycle}} 个事项，单次最多 {{max_iterations_per_run}} 轮。

{{cycle_steps}}

选择规则：

{{selection_policy}}

## 5.5 推进节奏

每轮不是重跑同一个提示，而是为下一轮留下可接续的位置和证据目标。

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

## 5.6 自主决策

用模型判断选择下一步有边界动作。不要把普通工程优先级问题交给用户。

自主决策：

{{managed_autonomy_decision_policy}}

自我迭代：

{{managed_autonomy_self_iteration}}

子角色启停：

{{managed_autonomy_subagent_control}}

交还用户：

{{managed_autonomy_human_return}}

## 6. 验收方式

验收标准：

{{contract_success_criteria}}

验证方式：

{{contract_verifier_commands}}

需要留下的通过证据：

{{contract_pass_evidence_required}}

## 7. 停止和交还

停止条件：

{{contract_reject_conditions}}

需要用户判断时：

{{exit_needs_human_when}}

没有进展时：

{{contract_no_progress_policy}}

变更策略：

{{change_policy}}

完成前需要明确批准的动作：

{{approval_required_action}}
