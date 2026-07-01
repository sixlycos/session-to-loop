# Goal Loop Designer

Use this reference when the user gives a goal and wants SixLoops to design a loop directly, even when no past session logs are available.

## When To Use

Use the demand-driven goal designer when the user says things like:

- "Design a loop for this project."
- "I want an agent to keep working toward this goal."
- "Create a loop engineering workflow for frontend/backend/review/delivery."
- "Let the user放手不管 after confirmation."
- "Use a subagent team if appropriate."

This mode is different from transcript mining. It starts from the user's current objective, produces a Change Map, then produces a goal-ready loop design that can later be improved with historical evidence.

## Design Standard

Every goal loop must include:

- A concrete objective.
- A Change Map:
  - current X,
  - target B,
  - how the user or operator will perceive X becoming B,
  - affected product and technical surfaces,
  - regression, recovery, or compatibility checks,
  - rollout waves,
  - decision packet triggers for judgment that cannot be delegated.
- A domain: `frontend`, `backend`, `fullstack`, `architecture`, `review`, `delivery`, `maintenance`, or `general`.
- A trigger or cadence.
- Discovery sources.
- Observe-decide-act-verify cycle steps.
- Selection policy for at most 1-3 high-value items.
- Verifier commands or checks.
- Success criteria and pass evidence.
- Stop conditions and no-progress policy.
- Loop exit contract with `CONTINUE`, `DONE`, review-needed, `BLOCKED`, and `BUDGET_STOPPED` boundaries. Internal JSON may still use `NEEDS_HUMAN`. `NEEDS_HUMAN` should mean that a decision packet or approval boundary is ready, not that the agent merely noticed uncertainty.
- State file and resume policy.
- Run protocol and verifier protocol.
- Review boundary and the mode required for higher-impact actions.
- Optional subagent team roles.

If the goal is vague, design a read-only or planning loop first. If the user grants edit, worktree, or PR-draft authority, make the first cycle runnable in that mode.

Before designing a managed loop, run the same fit test used for transcript-derived candidates:

- The goal is likely to recur or continue across multiple cycles.
- Objective checks can reject bad output.
- The agent can inspect or run the changed system.
- The loop has explicit item, iteration, time, token, or cost caps.
- High-impact actions require the matching user-approved mode or explicit approval before merge, deploy, dependency, credential, schema, data, payment, or production changes.

If the fit test fails, return a Change Map, read-only loop, skill, checklist, decision packet, approval gate, or rejection instead of a delegated loop.

## Change Map Standard

The first useful output for a direct goal is the transformation picture. The user should be able to answer:

- What is X today?
- What is B after the product or technical change?
- What product or technical idea turns X into B?
- What is the blast radius?
- How will the loop verify or regress it?
- What sequence of research, code mining, product function change, implementation, and verification waves will run?

For the user-group/resource-group example, the Change Map should make the picture concrete:

- X: user identity group, resource/channel group, and subscription upgrade group reuse one group namespace.
- B: product and code distinguish identity groups from resource routing groups while preserving existing data compatibility.
- User perception: operators see separate concepts and safer configuration rather than one overloaded "group" table.
- Affected surfaces: models, service helpers, controllers, rename behavior, settings UI, subscription validation, tests, and migration/release notes.
- Regression: focused group service tests, subscription tests, rename tests, admin UI smoke, compatibility checks, and migration dry run when applicable.
- Waves: evidence map, vocabulary boundary, compatible code slice, UI/config split, subscription decision packet, migration/release plan.

## Subagent Team Policy

When the host runtime exposes subagent or multi-agent tools, use a team only when it improves the loop:

- Use separate planner/checker/verifier roles for cross-surface, risky, or verification-heavy work.
- Keep maker roles inside explicit edit scope.
- Prefer independent reviewer/verifier agents after implementation when possible.
- Do not spawn a team for a tiny one-step task.
- If subagent tools are unavailable, execute the same roles sequentially in the current agent and keep the `TEAM.md` prompts as handoff prompts.

When the user explicitly asks to start, run, delegate, or use a subagent team:

- Read `TEAM.md`.
- Spawn only the roles needed for the current cycle.
- Prefer planner, checker/reviewer, verifier, and integrator as separate agents when independence matters.
- Spawn maker roles only when edit scope is explicit and bounded.
- Give each subagent one role prompt, the goal, allowed scope, expected output, and a reminder not to expand scope.
- While subagents run, continue non-overlapping work in the main thread.
- Integrate role outputs into `STATE.json` and return one status: `DONE`, `CONTINUE`, `BLOCKED`, review-needed, or `BUDGET_STOPPED`.

Default team roles:

- Planner: clarify objective, affected surfaces, 1-3 items, verifier path, and review boundaries.
- Maker: implement only approved, reversible changes.
- Checker or reviewer: inspect diff, likely regressions, missing tests, and risky assumptions.
- Verifier: run or specify the smallest check that can reject bad output.
- Integrator: merge role outputs, update state, and return final status.

## Script

Run:

```bash
python skills/sixloops/scripts/design_goal_loop.py \
  --goal "<user goal>" \
  --domain auto \
  --team-mode auto \
  --level auto \
  --out-dir .sixloops/goal-design
```

The script writes:

- `GOAL.md`
- `STATE.json`
- `RUN.md`
- `VERIFY.md`
- `TEAM.md`
- `HANDOFF.md`
- `AGENTS-snippet.md`
- `goal-loop-design.json`
- `manifest.json`

Use `--domain frontend|backend|fullstack|architecture|review|delivery|maintenance|general` when the domain is obvious.

Use `--team-mode subagent-team` only when team decomposition is useful. Use `--team-mode phased` when the same agent should run the roles sequentially.

Before presenting the result, check `loop-exit-contract.md`. The generated loop must explain when another cycle will add verified certainty and when it must return to the human. User-facing presentation should lead with the `GOAL.md` Change Map, then the execution contract and one recommended confirmation reply; `RUN.md`, `VERIFY.md`, and `STATE.json` are agent-facing harness files.

## Output First

Lead with the Change Map, then the Start Plan:

1. Current X.
2. Target B.
3. User perception.
4. Affected surfaces.
5. Regression or compatibility path.
6. Rollout waves.
7. First cycle.
8. Team shape if any.
9. Verifier.
10. Stop condition.
11. Review boundary and selected mode.
12. Generated artifact paths.

Put evidence limitations after the loop design. In demand-driven mode, the source is the user's current goal, not historical transcript evidence.
