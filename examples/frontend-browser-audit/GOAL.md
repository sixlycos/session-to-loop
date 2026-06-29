# Frontend Verification Loop

Use this as a SixLoops run packet.

## Objective

After frontend route or i18n changes, verify browser screenshots, fix low-risk UI regressions, and stop when product or visual judgment is needed.

## Loop Shape

- Domain: `frontend`
- Archetype: `frontend-verification`
- Start mode: `worktree draft`
- Internal level: `isolated-draft`
- Team mode: `phased`

## Acceptance Checks

- Target routes render without blocking errors.
- Desktop/mobile screenshots or snapshots confirm the main path.
- Console and network checks show no blocking errors.
- i18n/copy output shows no missing key, raw key, or unintended fallback locale.

## Cycle

1. Read prior state, current goal, changed UI files, and project instructions.
2. Identify the smallest route/state/locale set that proves the change, including default locale and one non-default locale when relevant.
3. Choose at most 1-3 visible or user-path regressions by impact, risk, and verifier availability.
4. Apply only obvious, reversible UI fixes such as missing keys, broken routes, console errors, or text overflow inside the approved scope.
5. Run focused static checks and browser verification, capture desktop/mobile screenshots when useful, inspect console/network/i18n fallback, and update state.

## Selection Policy

- Choose at most 3 item(s) per cycle.
- Prefer high-impact work with clear verifier evidence.
- Defer work that needs product, release, data, or architecture judgment.

## Verification

- Run the focused project verifier identified during the Decide step.

Required pass evidence:

- Route URL list.
- Locale list.
- Screenshot paths or snapshot summaries.
- Console/network result.
- i18n/copy finding summary.

## Stop Conditions

- Same visible failure repeats twice.
- No new screenshot, console, network, or i18n evidence appears across two iterations.
- The browser verifier or dev server is unavailable.
- A product copy, translation tone, visual direction, route behavior, or scope-expansion decision is required.

Also stop after `8` iteration(s), repeated no-progress, or a review boundary.

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

## State

- State file: `STATE.json`
- Read state before work.
- Update state before returning any final status.

## Human Gate

- visual direction changes
- product copy decisions
- translation tone or terminology decisions
- route behavior changes
- auth or data fixture changes
- scope expansion
- irreversible changes

## Final Status

Return exactly one internal status: `DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.
In user-facing copy, treat `NEEDS_HUMAN` as return-for-review.

## First Run Retro

Before the next run, update `STATE.json` with whether this loop reduced repeated human correction,
created false positives, required too much human judgment, should be downgraded to a skill/checklist,
or has enough accepted output to keep its current autonomy level.
