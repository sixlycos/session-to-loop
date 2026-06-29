# Draft AGENTS.md Snippet: Frontend Verification Loop

This is a draft loop instruction. Review before copying into project instructions.

When the goal matches `frontend-after-frontend-route-or-i18n-changes-351d3f2380`:

- Run as `worktree draft` (`isolated-draft` internally) with `phased` team mode.
- Objective: After frontend route or i18n changes, verify browser screenshots, fix low-risk UI regressions, and stop when product or visual judgment is needed.
- Select at most 3 item(s) per cycle.
- Stop after 8 iteration(s), repeated no-progress, or a review boundary.
- Read and update `STATE.json` before returning.
- Ask before: visual direction changes, product copy decisions, translation tone or terminology decisions, route behavior changes, auth or data fixture changes, scope expansion, irreversible changes.
