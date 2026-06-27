# {{name}}

```yaml
id: "{{id}}"
decision: "{{decision}}"
confidence: "{{confidence}}"
mechanism: "{{mechanism}}"
```

## Summary

{{summary}}

## Trigger

- {{trigger}}

## Proposed Artifact

- {{artifact}}

## Managed Goal Loop Spec

Goal:

{{managed_objective}}

Cadence or trigger:

{{managed_trigger}}

State file:

`{{managed_state_file}}`

Inputs:

- {{input}}

Cycle steps:

{{managed_cycle_steps}}

Selection policy:

{{managed_selection_policy}}

Max items per cycle:

{{managed_max_items_per_cycle}}

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

Stop conditions:

- {{stop_condition}}

## Safety

Autonomy level: `{{autonomy_level}}`

Requires approval for:

- {{approval_required_action}}

## Rejection or Downgrade Notes

{{downgrade_notes}}

## Evidence

| Source | Signal | Redacted evidence |
| --- | --- | --- |
| {{source}} | {{signal_kind}} | {{snippet}} |
