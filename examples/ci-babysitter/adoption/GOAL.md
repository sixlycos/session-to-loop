# CI Babysitter Loop Run Packet

Use this after the user starts `ci-babysitter` as `low-risk edit`.

## Objective

Keep CI failures moving toward a verified fix without guessing.

## Start Mode

`low-risk edit` (`goal-loop` internally): Run as a delegated goal loop. Ask before edits unless the user explicitly grants edit scope.

## State

- Active state file for this adoption packet: `STATE.json`
- Suggested project state path: `.session-to-loop/state/ci-babysitter.json`
- Read state before every cycle and update it before stopping.

## Acceptance Checks

- Relevant local test passes.
- CI becomes green or is clearly blocked.

## Observe-Decide-Act-Verify Cycle

1. Read the previous state file if it exists.
2. Inspect CI status, failed logs, and current git diff.
3. Pick at most 1-3 actionable failures by impact and confidence.
4. Attempt only low-risk local fixes with direct evidence.
5. Run focused verification and record the result.

## Selection Policy

- Prefer failures blocking merge.
- Ignore flakes without new evidence.

## Verification

- Run the focused project checks listed in verification.

## Stop Conditions

- Same failure repeats twice.
- Push or merge required.

Also stop after `8` iteration(s), no progress across two iterations, or any review boundary.

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

## Human Gate

- push
- merge

## Deliverables

- Status summary
- Patch or branch/PR draft when verification passes
- Updated state file

## Status Protocol

Return one status at the end:

- `DONE`: all success criteria passed with verifier evidence.
- `CONTINUE`: progress changed and budget remains.
- `BLOCKED`: repeated failure, no progress, missing input, or uncertain verifier.
- `NEEDS_HUMAN`: return for review because approval or human judgment is required.
- `BUDGET_STOPPED`: item, iteration, time, or token cap was reached.

## First Run Retro

Before the next run, update `STATE.json` with whether this loop reduced repeated human correction,
created false positives, required too much human judgment, should be downgraded to a skill/checklist,
or has enough accepted output to keep its current autonomy level.
