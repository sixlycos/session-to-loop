# CI Babysitter Loop

Use this as a managed agent goal after the user approves the loop.

## Objective

Keep CI failures moving toward a verified fix without guessing.

## Cadence or Trigger

- When CI is pending or failed on the current branch.

## Discovery Sources

- CI status
- failed job logs
- git diff

## Heartbeat

goal

## Recommended Starting Level

goal-loop

## State

Read this file first. Create or update it before stopping:

`.session-to-loop/state/ci-babysitter.json`

State update format:

- items: Tracked work items with status: inbox, active, blocked, done.
- attempts: Attempt log with action, verification result, and timestamp.
- failures: Failure signatures, repeat count, and blocker reason.
- next_cursor: Where the next run should resume.
- human_decisions: Approvals, rejections, or decisions that changed the loop boundary.

## Acceptance Contract

Completion must resolve to one of: `DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.

Update the state file before reporting `DONE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.

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

## Exit Contract

Update the state file before returning any status.

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

## Inputs to Inspect Each Cycle

- CI status
- failed job logs
- git diff

## Selection Policy

Decide at most 3 item(s) per cycle.

- Prefer failures blocking merge.
- Ignore flakes without new evidence.

## Iteration Budget

Stop after 8 iteration(s) in one run unless verification passes earlier.

## Cycle Steps

- Read the previous state file if it exists.
- Inspect CI status, failed logs, and current git diff.
- Pick at most 1-3 actionable failures by impact and confidence.
- Attempt only low-risk local fixes with direct evidence.
- Run focused verification and record the result.

## Change Policy

If a fix is low risk and directly evidenced, use an isolated branch or worktree when available. Do not push or merge without approval.

## Deliverables

- Status summary
- Patch or branch/PR draft when verification passes
- Updated state file

## Verification

- Relevant local test passes.
- CI becomes green or is clearly blocked.

## Resume Policy

On the next run, read the state file and continue unresolved failures before new ones.

## Failure Policy

If the same failure repeats twice or verification is inconclusive, record the blocker and stop.

## Promotion And Demotion

Promotion criteria:

- Promote only after repeated runs pass verification and human review accepts the output.

Demotion criteria:

- Demote when outputs are rejected, verification is inconclusive, cost grows, or human judgment is repeatedly required.

## Stop Conditions

- CI is green.
- Same failure repeats twice.
- Push or merge is required.

## Safety Boundaries

- Autonomy level: `draft-only`
- Requires approval for:

- push
- merge

- Human checkpoint:

None.

- Budget caps:

None.

- Do not push, merge, deploy, delete data, migrate schemas, change permissions, or call production APIs without explicit user approval.
- Stop and ask the user when the next action requires product, release, security, or data-loss judgment.
