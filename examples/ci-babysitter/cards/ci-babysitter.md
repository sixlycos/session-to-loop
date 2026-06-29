# CI Babysitter Loop

## Start Plan

Recommended start: `start ci-babysitter as low-risk edit`

Mode: `low-risk edit`

This loop will do:

- Read the previous state file if it exists.
- Inspect CI status, failed logs, and current git diff.
- Pick at most 1-3 actionable failures by impact and confidence.
- Attempt only low-risk local fixes with direct evidence.
- Run focused verification and record the result.

This loop will not do in the current mode:

- Land or finalize review-boundary actions without the matching mode: push, merge.
- If a fix is low risk and directly evidenced, use an isolated branch or worktree when available. Do not push or merge without approval.

It returns to you before:

- push
- merge

It verifies with:

- Run the focused project checks listed in verification.

It stops when:

- Same failure repeats twice.
- Push or merge required.

Why this loop should exist:

This needs repeated observe-decide-act-verify behavior with state, verification, stop conditions, and resume behavior.

Where this may be wrong:

- The packet set may omit current project state or newer failures.

Reply with one:

- `start ci-babysitter as read-only`
- `start ci-babysitter as low-risk edit`
- `start ci-babysitter as worktree draft`
- `start ci-babysitter as PR draft`
- `shrink ci-babysitter to skill`
- `reject ci-babysitter`

```yaml
id: "ci-babysitter"
decision: "draft"
confidence: "high"
mechanism: "loop, skill"
work_shape: "goal-driven"
loop_archetype: "engineering-maintenance"
```

## Start Options

Start from the weakest useful mode. Move up only when the verifier and review results justify it.

Reply with one:

- `start ci-babysitter as read-only`
- `start ci-babysitter as low-risk edit`
- `start ci-babysitter as worktree draft`
- `start ci-babysitter as PR draft`
- `shrink ci-babysitter to skill`
- `reject ci-babysitter`

First cycle packet:

```text
Objective:
Keep CI failures moving toward a verified fix without guessing.

Acceptance checks:
- Relevant local test passes.
- CI becomes green or is clearly blocked.

First cycle:
1. Observe: read the state file, current inputs, and latest verifier evidence
2. Decide: choose at most 3 item(s), the next action, and any review boundary
3. Act: pick at most 3 directly evidenced item(s)
4. Verify: Run the focused project checks listed in verification.
5. Update state: .session-to-loop/state/ci-babysitter.json

Stop after:
8 iterations, repeated failure, no progress across two iterations, or a review boundary

Return for review:
Ask before push, merge.
```

## Run Card

Can start now: `limited`

Can confirm: `yes`

Can delegate: `yes`

Missing before delegate:

- None.

Next action: `start`

## Summary

Repeated user requests to inspect CI logs before patching and to avoid pushing before verification.

## Trigger

- CI is pending or failed.

## Proposed Artifact

- loop-card
- draft-skill

## Mechanism Decision

Why this mechanism:

This needs repeated observe-decide-act-verify behavior with state, verification, stop conditions, and resume behavior.

Why not smaller:

A rule, skill, or checklist alone would not preserve state or drive repeated verification.

Why not more autonomous:

Start at `goal-loop` until verifier evidence and accepted outputs justify promotion.

## Verifier Box

Primary verifier:

- Run the focused project checks listed in verification.

Checker:

Use deterministic checks first; use a read-only checker when commands cannot decide.

PASS evidence:

- Command output, CI status, or explicit verifier note.

Internal status protocol:

`DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`

## Exit Contract

Continue only if:

- Objective is unchanged.
- Next action stays inside approved scope.
- A verifier can reject bad output.
- New evidence changed or is likely from the next verifier.
- Fewer than 3 item(s) are active in this cycle.
- Fewer than 8 iteration(s) have run.

Return `DONE` when:

- Relevant local test passes.
- CI becomes green or is clearly blocked.

Return for review when:

- push is required.
- merge is required.

Return `BLOCKED` when:

- Same failure repeats twice.
- Verifier is unavailable or ambiguous.

Return `BUDGET_STOPPED` when:

- More than 3 item(s) would be required in one cycle.
- 8 iteration(s) are reached.

Status protocol:

- CONTINUE: Only when another cycle can increase verified certainty.
- DONE: Acceptance checks passed with required evidence; return for acceptance.
- NEEDS_HUMAN: Return for review because human judgment or explicit approval is required.
- BLOCKED: Reliable progress is not possible with current evidence or verifier.
- BUDGET_STOPPED: Item, iteration, time, token, or cost cap was reached.

## Mode Ladder

Current mode: `low-risk edit`

Next mode: `worktree draft`

Promotion criteria:

- Promote only after repeated runs pass verification and human review accepts the output.

Demotion criteria:

- Demote when outputs are rejected, verification is inconclusive, cost grows, or human judgment is repeatedly required.

## Loop Economics

Expected trigger frequency: `unknown`

Expected per-run cost: `unknown`

Automatic rejection signals:

- Relevant local test passes.
- CI becomes green or is clearly blocked.

Human review load: `medium`

Demote if:

Demote when fewer than half of reviewed outputs are accepted, verifier evidence stays weak, or human judgment dominates the loop.

## Loop Runbook

Objective:

Keep CI failures moving toward a verified fix without guessing.

Cadence or trigger:

- When CI is pending or failed on the current branch.

Discovery sources:

- CI status
- failed job logs
- git diff

Heartbeat:

`goal`

Internal maturity:

`goal-loop`

User-facing mode:

`low-risk edit`

State file:

`.session-to-loop/state/ci-babysitter.json`

State schema:

- items: Tracked work items with status: inbox, active, blocked, done.
- attempts: Attempt log with action, verification result, and timestamp.
- failures: Failure signatures, repeat count, and blocker reason.
- next_cursor: Where the next run should resume.
- human_decisions: Approvals, rejections, or decisions that changed the loop boundary.

Inputs:

- CI status
- failed job logs
- git diff

Cycle steps:

- Read the previous state file if it exists.
- Inspect CI status, failed logs, and current git diff.
- Pick at most 1-3 actionable failures by impact and confidence.
- Attempt only low-risk local fixes with direct evidence.
- Run focused verification and record the result.

Selection policy:

- Prefer failures blocking merge.
- Ignore flakes without new evidence.

Max items per cycle:

3

Max iterations per run:

8

## Acceptance Contract

Acceptance checks:

- Relevant local test passes.
- CI becomes green or is clearly blocked.

Verifier commands:

- Run the focused project checks listed in verification.

Evaluator:

Use deterministic checks first; use a read-only checker when commands cannot decide.

Pass evidence required:

- Command output, CI status, or explicit verifier note.

Reject conditions:

- Same failure repeats twice.
- Push or merge required.

No-progress policy:

Stop when the same failure repeats twice or no evidence changes across two iterations.

Change policy:

If a fix is low risk and directly evidenced, use an isolated branch or worktree when available. Do not push or merge without approval.

Deliverables:

- Status summary
- Patch or branch/PR draft when verification passes
- Updated state file

Verification:

- Relevant local test passes.
- CI becomes green or is clearly blocked.

Resume policy:

On the next run, read the state file and continue unresolved failures before new ones.

Failure policy:

If the same failure repeats twice or verification is inconclusive, record the blocker and stop.

Promotion criteria:

- Promote only after repeated runs pass verification and human review accepts the output.

Demotion criteria:

- Demote when outputs are rejected, verification is inconclusive, cost grows, or human judgment is repeatedly required.

Stop conditions:

- CI is green.
- Same failure repeats twice.
- Push or merge is required.

## Safety

Autonomy level: `draft-only`

Requires approval for:

- push
- merge

Human checkpoint:

- None.

Budget caps:

- None.

## Rejection or Downgrade Notes



## Evidence Appendix

Evidence snippets are hidden by default in public artifacts. Use private `candidates.json` for full redacted evidence.

| Source | Signal | Evidence pointer |
| --- | --- | --- |
| session:synthetic-ci-1#event-1 | verification-request / user / unknown / unknown / inspect_failed_ci_before_guessing | [snippet hidden; see private candidates.json] |

## Decision Trace

Analysis basis: AI semantic candidate with deterministic scope, recurrence, loop, and safety gates applied.

Primary evidence role: `user`

Role counts:

- user: 3
- tool: 1
- assistant: 0
- unknown: 0

Intents: ci_failed_status, do_not_push_before_verification, inspect_failed_ci_before_guessing, wait_read_log_patch_failing_test

Loop eligibility:

- eligible: yes
- requested_loop_mechanism: yes
- recurs_across_sessions: yes
- has_user_primary_evidence: yes
- has_project_context_evidence: no
- has_primary_or_project_evidence: yes
- has_observable_state: yes
- has_repeatable_action: yes
- has_verification_signal: yes
- has_stop_conditions: yes
- has_safety_gate: yes
- has_state_file: yes
- has_state_schema: yes
- has_discovery_sources: yes
- has_cycle_steps: yes
- has_selection_policy: yes
- has_iteration_cap: yes
- has_completion_contract: yes
- has_change_policy: yes
- has_resume_policy: yes
- has_failure_policy: yes
- has_human_checkpoint: yes
- has_budget_cap: yes
- has_loop_exit_contract: yes
- has_all_exit_statuses: yes
- has_continue_gate: yes
- has_budget_stop: yes
- exit_contract_bound_to_verifier: yes
- exit_contract_bound_to_human_gate: yes

Missing loop criteria: None.

Hard downgrades: None.
