# Frontend Browser Audit

This example shows the goal-first path: start from a current frontend objective, then generate a runnable loop packet.

## Story

| Stage | What happens |
| --- | --- |
| **Before** | The user repeatedly asks the agent to verify changed routes, screenshots, console/network state, and i18n fallback after UI work. |
| **SixLoops output** | A Frontend Verification Start Plan with route discovery, screenshot evidence, state, verifier, and visual/product review boundaries. |
| **After** | The next agent can run a bounded browser verification cycle, fix only low-risk regressions, and stop when product or visual judgment is needed. |

## Objective

> After frontend route or i18n changes, verify browser screenshots, fix low-risk UI regressions, and stop when product or visual judgment is needed.

## SixLoops Output

SixLoops designs a **Frontend Verification Loop**:

- **Domain**: `frontend`
- **Team mode**: `phased`
- **Start mode**: `worktree draft`
- **Internal level**: `isolated-draft`
- **Verifier**: focused browser/static checks chosen during the Decide step
- **Pass evidence**: route list, locale list, screenshot/snapshot summaries, console/network result, i18n summary
- **Review boundary**: visual direction, product copy, translation tone, route behavior, auth/data fixtures
- **Exit statuses**: `CONTINUE`, `DONE`, review-needed, `BLOCKED`, `BUDGET_STOPPED`

## After

The next agent should:

1. Read `STATE.json` and project instructions.
2. Identify the smallest route, state, and locale set that proves the change.
3. Choose at most 1-3 visible regressions.
4. Apply only obvious, reversible UI fixes inside scope.
5. Run browser/static verification and capture pass evidence.
6. Stop on product copy, translation tone, visual direction, route behavior, auth/data fixture, or scope decisions.

## Why This Is A Loop

This is not just a checklist because verification often discovers new visible failures. It is not fully autonomous because visual direction and product copy need a stronger user-approved mode or review.

## Files

- [GOAL.md](GOAL.md): runnable loop packet.
- [TEAM.md](TEAM.md): planner, maker, verifier, reviewer, and integrator roles.
- [STATE.json](STATE.json): resume ledger with post-run learning fields.
- [HANDOFF.md](HANDOFF.md): how to run or resume.
- [AGENTS-snippet.md](AGENTS-snippet.md): draft project instruction.
- [goal-loop-design.json](goal-loop-design.json): machine-readable loop design.

## Try This Case

```bash
python skills/session-to-loop/scripts/design_goal_loop.py \
  --goal "After frontend route or i18n changes, verify browser screenshots, fix low-risk UI regressions, and stop when product or visual judgment is needed." \
  --domain frontend \
  --team-mode auto \
  --level isolated-draft \
  --out-dir .session-to-loop/tmp/frontend-browser-audit \
  --overwrite
```
