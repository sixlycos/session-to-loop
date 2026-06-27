# {{loop_name}}

Use this as a managed agent goal after the user approves the loop.

## Goal

{{goal}}

## Cadence or Trigger

{{cadence_or_trigger}}

## State

Read this file first. Create or update it before stopping:

`{{state_file}}`

## Inputs to Inspect Each Cycle

{{context_source}}

## Selection Policy

Pick at most {{max_items_per_cycle}} item(s) per cycle.

{{selection_policy}}

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

## Stop Conditions

{{stop_condition}}

## Safety Boundaries

- Autonomy level: `{{autonomy_level}}`
- Requires approval for:

{{approval_required_action}}

- Do not push, merge, deploy, delete data, migrate schemas, change permissions, or call production APIs without explicit user approval.
- Stop and ask the user when the next action requires product, release, security, or data-loss judgment.
