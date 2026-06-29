# Frontend Verification Loop Handoff

This folder contains a goal-ready SixLoops design generated from a user objective.

## Start Here

1. Read `GOAL.md`.
2. If team tools are available and team mode is `subagent-team`, use `TEAM.md` to split planner, maker, checker, verifier, and integrator roles.
3. Keep `STATE.json` beside the run and update it before stopping.

## Exit Contract

Continue only if:

- Objective is unchanged.
- Next action stays inside approved scope.
- A verifier can reject bad output.
- New evidence changed or is likely from the next verifier.
- Risk stays below the approved mode and review boundary.
- The last cycle changed evidence, narrowed scope, reduced failures, or clarified the blocker.
- Fewer than 3 item(s) are active in this cycle.
- Fewer than 8 iteration(s) have run.

Return `DONE` when:

- Target routes render without blocking errors.
- Desktop/mobile screenshots or snapshots confirm the main path.
- Console and network checks show no blocking errors.
- i18n/copy output shows no missing key, raw key, or unintended fallback locale.

Return for review when:

- Review required for visual direction changes.
- Review required for product copy decisions.
- Review required for translation tone or terminology decisions.
- Review required for route behavior changes.
- Review required for auth or data fixture changes.
- Review required for scope expansion.
- Review required for irreversible changes.

Return `BLOCKED` when:

- Same visible failure repeats twice.
- No new screenshot, console, network, or i18n evidence appears across two iterations.
- The browser verifier or dev server is unavailable.
- A product copy, translation tone, visual direction, route behavior, or scope-expansion decision is required.

Return `BUDGET_STOPPED` when:

- More than 3 item(s) would be required in one cycle.
- 8 iteration(s) are reached.
- Token, time, cost, or tool budget is reached.

## Learning Check

After each run, record baseline friction, post-run result, saved corrections, false positives,
human acceptance, next adjustment, and demotion recommendation in `STATE.json`.

## Files

- `examples/frontend-browser-audit/GOAL.md`
- `examples/frontend-browser-audit/TEAM.md`
- `examples/frontend-browser-audit/STATE.json`
- `examples/frontend-browser-audit/goal-loop-design.json`
- `examples/frontend-browser-audit/AGENTS-snippet.md`
