# CI Babysitter Loop Run Handoff

This packet was generated after starting `ci-babysitter` as `low-risk edit`.

## What To Run

Paste or attach `GOAL.md` as the delegated goal. Keep `STATE.json` beside it and update it before stopping.

## Why This Exists

Repeated user requests to inspect CI logs before patching and to avoid pushing before verification.

## Trigger

- When CI is pending or failed on the current branch.

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

## Learning Check

After the first run, record saved corrections, false positives, human acceptance, next adjustment,
and any demotion recommendation in `STATE.json`.

## Files

- `examples/ci-babysitter/adoption/GOAL.md`
- `examples/ci-babysitter/adoption/STATE.json`
- `examples/ci-babysitter/adoption/AGENTS-snippet.md`
- `examples/ci-babysitter/adoption/manifest.json`
