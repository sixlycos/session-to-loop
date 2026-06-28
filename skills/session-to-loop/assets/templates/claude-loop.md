# {{loop_name}}

Use this as a managed agent goal after the user approves the loop.

## Goal

{{goal}}

## Cadence or Trigger

{{cadence_or_trigger}}

## Discovery Sources

{{discovery_sources}}

## Heartbeat

{{heartbeat}}

## Recommended Starting Level

{{recommended_maturity}}

## State

Read this file first. Create or update it before stopping:

`{{state_file}}`

State update format:

{{state_schema}}

## Acceptance Contract

Completion must resolve to one of: `DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.

Update the state file before reporting `DONE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.

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

## Inputs to Inspect Each Cycle

{{context_source}}

## Selection Policy

Pick at most {{max_items_per_cycle}} item(s) per cycle.

{{selection_policy}}

## Iteration Budget

Stop after {{max_iterations_per_run}} iteration(s) in one run unless verification passes earlier.

## Cycle Steps

{{cycle_steps}}

## Change Policy

{{change_policy}}

## Deliverables

{{deliverables}}

## Verification

{{verification_signal}}

## Resume Policy

{{resume_policy}}

## Failure Policy

{{failure_policy}}

## Promotion And Demotion

Promotion criteria:

{{promotion_criteria}}

Demotion criteria:

{{demotion_criteria}}

## Stop Conditions

{{stop_condition}}

## Safety Boundaries

- Autonomy level: `{{autonomy_level}}`
- Requires approval for:

{{approval_required_action}}

- Human checkpoint:

{{human_checkpoint}}

- Budget caps:

{{budget_caps}}

- Do not push, merge, deploy, delete data, migrate schemas, change permissions, or call production APIs without explicit user approval.
- Stop and ask the user when the next action requires product, release, security, or data-loss judgment.
