# {{name}}

```yaml
id: "{{id}}"
decision: "{{decision}}"
confidence: "{{confidence}}"
mechanism: "{{mechanism}}"
work_shape: "{{work_shape}}"
loop_archetype: "{{loop_archetype}}"
```

## Confirm This Loop

Recommended action: `{{recommended_action}}`

Reply with one:

- `{{confirm_as_read_only}}`
- `{{confirm_as_goal_loop}}`
- `{{shrink_to_smaller_mechanism}}`
- `{{reject_candidate}}`

First run prompt:

```text
Goal:
{{first_run_goal}}

Success criteria:
{{first_run_success_criteria}}

Each round:
1. Observe: {{first_run_observe}}
2. Act: {{first_run_act}}
3. Verify: {{first_run_verify}}
4. Update state: {{managed_state_file}}

Stop after:
{{first_run_stop_after}}

Human gate:
{{first_run_human_gate}}
```

## Decision Card

Can use now: `{{can_use_now}}`

Can confirm: `{{can_confirm}}`

Can delegate: `{{can_delegate}}`

Missing before delegate:

- {{missing_before_delegate}}

Next action: `{{next_action}}`

## Summary

{{summary}}

## Trigger

- {{trigger}}

## Proposed Artifact

- {{artifact}}

## Mechanism Decision

Why this mechanism:

{{why_this_mechanism}}

Why not smaller:

{{why_not_smaller}}

Why not more autonomous:

{{why_not_more_autonomous}}

## Verifier Box

Primary verifier:

{{primary_verifier}}

Checker:

{{checker}}

PASS evidence:

{{pass_evidence_required}}

Status protocol:

`DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`

## Adoption Path

Current rung: `{{current_rung}}`

Next rung: `{{next_rung}}`

Promotion criteria:

{{managed_promotion_criteria}}

Demotion criteria:

{{managed_demotion_criteria}}

## Loop Economics

Expected trigger frequency: `{{expected_trigger_frequency}}`

Expected per-run cost: `{{expected_per_run_cost}}`

Automatic rejection signals:

{{automatic_rejection_signals}}

Human review load: `{{human_review_load}}`

Demote if:

{{demote_if}}

## Managed Goal Loop Spec

Goal:

{{managed_objective}}

Cadence or trigger:

{{managed_trigger}}

Discovery sources:

{{managed_discovery_sources}}

Heartbeat:

`{{managed_heartbeat}}`

Recommended starting level:

`{{managed_recommended_maturity}}`

State file:

`{{managed_state_file}}`

State schema:

{{managed_state_schema}}

Inputs:

- {{input}}

Cycle steps:

{{managed_cycle_steps}}

Selection policy:

{{managed_selection_policy}}

Max items per cycle:

{{managed_max_items_per_cycle}}

Max iterations per run:

{{managed_max_iterations_per_run}}

## Acceptance Contract

Success criteria:

{{contract_success_criteria}}

Verifier commands:

{{contract_verifier_commands}}

Evaluator:

{{contract_evaluator_agent}}

Pass evidence required:

{{contract_pass_evidence_required}}

Reject conditions:

{{contract_reject_conditions}}

No-progress policy:

{{contract_no_progress_policy}}

Change policy:

{{managed_change_policy}}

Deliverables:

{{managed_deliverables}}

Verification:

- {{verification}}

Resume policy:

{{managed_resume_policy}}

Failure policy:

{{managed_failure_policy}}

Promotion criteria:

{{managed_promotion_criteria}}

Demotion criteria:

{{managed_demotion_criteria}}

Stop conditions:

- {{stop_condition}}

## Safety

Autonomy level: `{{autonomy_level}}`

Requires approval for:

- {{approval_required_action}}

Human checkpoint:

- {{human_checkpoint}}

Budget caps:

- {{budget_caps}}

## Rejection or Downgrade Notes

{{downgrade_notes}}

## Evidence

| Source | Signal | Redacted evidence |
| --- | --- | --- |
| {{source}} | {{signal_kind}} | {{snippet}} |
