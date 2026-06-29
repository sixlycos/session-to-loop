# Skill Routing Matrix

Use this reference when a candidate loop touches frontend, backend, full-stack architecture, task decomposition, review, verification, or delivery.

Do not load every related skill. Pick the smallest relevant skill only after the loop candidate or task domain is clear.

Do not render one generic development loop for every task. Classify the task surface first, then
emit the smallest concrete artifact for that surface: frontend verification loop, backend contract
triage loop, architecture task-split checklist, maker/checker review loop, or delivery readiness loop.

For goal-first designs, use `scripts/design_goal_loop.py` to generate `TEAM.md`. If the host runtime
has subagent tools, planner/checker/verifier roles may run as separate agents. Maker roles may only
modify files after the user grants edit scope. If subagents are unavailable, execute the roles
sequentially in the current agent.

## Frontend Loops

Typical triggers:

- Route, layout, component, copy, auth UI, i18n, responsive, or visual changes.

Likely loop shape:

- Identify changed routes and core states.
- Run static checks or i18n checks.
- Use browser automation for the smallest route set.
- Capture screenshots or snapshots.
- Fix at most 1-3 confirmed regressions.
- Stop when screenshots pass, auth/data blocks verification, or design judgment is needed.

Possible skill routing:

- Browser verification: `playwright` or browser-control skills.
- UI quality review: `frontend-review`, `frontend-design`, or project-specific frontend skills.
- Framework-specific implementation: `nextjs`, `shadcn-ui`, or similar only when the repo uses them.
- Team roles: planner, frontend-maker, browser-verifier, reviewer, integrator.

## Backend Loops

Typical triggers:

- API, provider, relay, queue, database, auth, CI, migration, or deployment changes.

Likely loop shape:

- Inspect changed contract or failure logs.
- Run focused tests or acceptance checks.
- Separate transport, schema, semantic, data, and latency failures.
- Patch only low-risk evidenced failures.
- Stop for production, migration, credential, billing, or irreversible actions.

Possible skill routing:

- CI failures: `gh-fix-ci` when GitHub checks are available.
- Code review: `review` or project-specific review skills.
- Provider acceptance: generated project skill or checklist before turning into hooks.
- Team roles: planner, backend-maker, contract-verifier, reviewer, integrator.

## Full-Stack Architecture Loops

Typical triggers:

- Contract changes spanning UI/API, auth/session behavior, data model changes, or release coordination.

Likely loop shape:

- Map affected surfaces.
- Produce a task split: frontend, backend, integration, verification, delivery.
- Review interface contracts before implementation.
- Verify with both unit-level and end-to-end signals where available.
- Stop when the contract is ambiguous or migration/release approval is needed.

Possible skill routing:

- Architecture review: project-specific generated skill or `review`.
- Browser verification: `playwright`.
- CI/release: `gh-fix-ci` or release-oriented skills when explicitly needed.
- Team roles: architect, frontend-maker, backend-maker, integration-verifier, integrator.

## Development Lifecycle Loops

Task intake:

- Clarify objective, constraints, impacted surfaces, and done conditions.

Task split:

- Break into 1-3 high-value items per cycle.

Implementation:

- Make local, reversible changes only when evidence supports them.

Self-review:

- Review diff against objective, project rules, and likely regressions.

Verification:

- Run focused tests, build, browser checks, screenshots, or log checks.

Delivery:

- Produce summary, patch or PR draft, validation evidence, state file update, and next stop condition.

Required output shape:

- Frontend loop: changed routes/states, screenshot paths, console/network checks, i18n or browser verifier.
- Backend loop: failure class, contract surface, focused verifier command, reversibility, migration or production gate.
- Architecture loop: affected surfaces, interface contract, dependency order, verification per layer, human ambiguity gate.
- Review loop: maker summary, checker findings with file/line or failure path, regression risk, focused verification.
- Delivery loop: actual commands run, pass evidence, untested items, PR or handoff draft, merge/deploy approval gate.
