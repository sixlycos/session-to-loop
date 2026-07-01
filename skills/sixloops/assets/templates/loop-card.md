# {{name}}

## Start Here

Recommended reply: `{{recommended_action}}`

Mode: `{{mode_display}}`

Goal:

{{first_run_goal}}

## What It Does For You

{{user_value}}

## Change Map

{{change_map}}

It will:

{{control_will_do}}

## Autopilot

{{autopilot_contract}}

Reply in this chat with one line:

{{start_options}}

## First Cycle

1. Clarify: {{first_run_observe}}; {{first_run_decide}}.
2. Act: {{first_run_act}}.
3. Verify: {{first_run_verify}}
4. Deliver / Stop: update `{{managed_state_file}}`; stop after {{first_run_stop_after}}; return point: {{first_run_human_gate}}

## Verify And Stop

It verifies with:

{{control_verify}}

It stops when:

{{control_stop}}

It returns to you before:

{{control_must_ask}}

This stays outside the current mode:

{{control_will_not}}

## Why This Loop

{{control_why}}

Where this may be wrong:

{{where_this_may_be_wrong}}

```yaml
id: "{{id}}"
decision: "{{decision}}"
confidence: "{{confidence}}"
mechanism: "{{mechanism}}"
work_shape: "{{work_shape}}"
loop_archetype: "{{loop_archetype}}"
```

## Details

Can start now: `{{can_use_now}}`

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

Internal status protocol:

`DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`

## Exit Contract

Continue only if:

{{exit_continue_only_if}}

Return `DONE` when:

{{exit_done_when}}

Return to user when:

{{exit_needs_human_when}}

Return `BLOCKED` when:

{{exit_blocked_when}}

Return `BUDGET_STOPPED` when:

{{exit_budget_stopped_when}}

Status protocol:

{{exit_status_protocol}}

## Mode Ladder

Current mode: `{{current_rung}}`

Next mode: `{{next_rung}}`

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

## Loop Runbook

Objective:

{{managed_objective}}

Cadence or trigger:

{{managed_trigger}}

Discovery sources:

{{managed_discovery_sources}}

Heartbeat:

`{{managed_heartbeat}}`

Internal maturity:

`{{managed_recommended_maturity}}`

User-facing mode:

`{{managed_display_mode}}`

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

Acceptance checks:

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

## Execution Authority

Autonomy level: `{{autonomy_level}}`

Ask before finalizing:

- {{approval_required_action}}

Return point:

- {{human_checkpoint}}

Budget caps:

- {{budget_caps}}

## Smaller-Mechanism Notes

{{downgrade_notes}}

## Evidence Appendix

Evidence snippets are hidden by default in public artifacts. Use private `candidates.json` for full redacted evidence.

| Source | Signal | Evidence pointer |
| --- | --- | --- |
| {{source}} | {{signal_kind}} | {{snippet}} |
