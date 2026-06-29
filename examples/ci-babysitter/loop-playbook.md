# SixLoops Start Plans

Recommended 1 startable loop plan(s). Choose a mode, shrink the idea, reject it, or rerun with narrower evidence.

## Recommended Start Plans

### 1. CI Babysitter Loop

Recommended start: `start ci-babysitter as low-risk edit`

Decision: `draft` | Mechanism: `loop, skill` | Confidence: `high`

Can start now: `limited` | Can confirm: `yes` | Can delegate: `yes`

Next action: `start`

Start with one:

- `start ci-babysitter as read-only`
- `start ci-babysitter as low-risk edit`
- `start ci-babysitter as worktree draft`
- `start ci-babysitter as PR draft`
- `shrink ci-babysitter to skill`
- `reject ci-babysitter`

What it does: Keep CI failures moving toward a verified fix without guessing.

Work shape: `goal-driven` | Archetype: `engineering-maintenance`

Heartbeat: `goal` | Mode: `low-risk edit` | Internal maturity: `goal-loop`

First cycle:

- Observe: read the state file, current inputs, and latest verifier evidence
- Decide: choose at most 3 item(s), the next action, and any review boundary
- Act: pick at most 3 directly evidenced item(s)
- Verify: Run the focused project checks listed in verification.
- State: .session-to-loop/state/ci-babysitter.json
- Stop after: 8 iterations, repeated failure, no progress across two iterations, or a review boundary

Trigger:

- When CI is pending or failed on the current branch.

Loop cycle:

- Read the previous state file if it exists.
- Inspect CI status, failed logs, and current git diff.
- Pick at most 1-3 actionable failures by impact and confidence.
- Attempt only low-risk local fixes with direct evidence.
- Run focused verification and record the result.

Verification:

- Relevant local test passes.
- CI becomes green or is clearly blocked.

Stop conditions:

- CI is green.
- Same failure repeats twice.
- Push or merge is required.

Iteration cap: 8 run iteration(s)

Review boundary: push; merge

Acceptance checks:

- Relevant local test passes.
- CI becomes green or is clearly blocked.

Loop exits:

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

Why this mechanism: This needs repeated observe-decide-act-verify behavior with state, verification, stop conditions, and resume behavior. Repeated user requests to inspect CI logs before patching and to avoid pushing before verification. Basis: repeated user-language evidence.

## Start, Shrink, Or Reject

Choose which proposal to start, shrink, or reject from `CI Babysitter Loop`. If the chosen mode allows edits, run the first controlled cycle in that mode; otherwise generate the run packet and state convention.

- `start ci-babysitter as read-only`
- `start ci-babysitter as low-risk edit`
- `start ci-babysitter as worktree draft`
- `start ci-babysitter as PR draft`
- `shrink ci-babysitter to skill`
- `reject ci-babysitter`

## Smaller Mechanisms

These are useful only if you reject or downgrade the loop proposals.

### Rules and Memory Candidates

None.

### Skill Candidates

- `ci-babysitter`: Repeated user requests to inspect CI logs before patching and to avoid pushing before verification.

### Hook Candidates

None.

### Checklist or Approval Gates

None.

### Rejected Candidates

None.

## Decision Index

| Candidate | Mechanism | Decision | Confidence |
| --- | --- | --- | --- |
| CI Babysitter Loop | loop, skill | draft | high |

Loop candidates:

- `ci-babysitter`: Repeated user requests to inspect CI logs before patching and to avoid pushing before verification.

## Run Notes

Project: `session-to-loop`

Analysis window: `explicit local inputs`

Input sources: `1 file(s), 5 record(s)`

Redaction: `enabled`

Source limitations:

Files: 1; records: 5; providers: generic=4; source types: generic-jsonl=4

## Private Outputs

- .session-to-loop/private/candidates.json

## Shareable Outputs

- examples/ci-babysitter/cards/ci-babysitter.md
- examples/ci-babysitter/ci-babysitter-loop.md
- examples/ci-babysitter/ci-babysitter-skill.md
- examples/ci-babysitter/summary.json


## Analysis Scope

Approved: `True`

Allowed roles: `user, tool`

Redacted snippets: `enabled`

Output visibility: `private`
