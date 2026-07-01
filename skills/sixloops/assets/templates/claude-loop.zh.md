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
