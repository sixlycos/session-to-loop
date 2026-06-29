# Goal Loop Designer

Use this reference when the user gives a goal and wants SixLoops to design a loop directly, even when no past session logs are available.

## When To Use

Use the demand-driven goal designer when the user says things like:

- "Design a loop for this project."
- "I want an agent to keep working toward this goal."
- "Create a loop engineering workflow for frontend/backend/review/delivery."
- "Let the user放手不管 after confirmation."
- "Use a subagent team if appropriate."

This mode is different from transcript mining. It starts from the user's current objective, then produces a goal-ready loop design that can later be improved with historical evidence.

## Design Standard

Every goal loop must include:

- A concrete objective.
- A domain: `frontend`, `backend`, `fullstack`, `architecture`, `review`, `delivery`, `maintenance`, or `general`.
- A trigger or cadence.
- Discovery sources.
- Observe-decide-act-verify cycle steps.
- Selection policy for at most 1-3 high-value items.
- Verifier commands or checks.
- Success criteria and pass evidence.
- Stop conditions and no-progress policy.
- State file and resume policy.
- Approval boundary.
- Optional subagent team roles.

If the goal is vague, design a read-only or planning loop first. Do not invent edit authority.

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
- Integrate role outputs into `STATE.json` and return one status: `DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.

Default team roles:

- Planner: clarify objective, affected surfaces, 1-3 items, verifier path, and approval gates.
- Maker: implement only approved, reversible changes.
- Checker or reviewer: inspect diff, likely regressions, missing tests, and risky assumptions.
- Verifier: run or specify the smallest check that can reject bad output.
- Integrator: merge role outputs, update state, and return final status.

## Script

Run:

```bash
python skills/session-to-loop/scripts/design_goal_loop.py \
  --goal "<user goal>" \
  --domain auto \
  --team-mode auto \
  --level goal-loop \
  --out-dir .session-to-loop/goal-design
```

The script writes:

- `GOAL.md`
- `TEAM.md`
- `STATE.json`
- `HANDOFF.md`
- `AGENTS-snippet.md`
- `goal-loop-design.json`
- `manifest.json`

Use `--domain frontend|backend|fullstack|architecture|review|delivery|maintenance|general` when the domain is obvious.

Use `--team-mode subagent-team` only when team decomposition is useful. Use `--team-mode phased` when the same agent should run the roles sequentially.

## Output First

Lead with what the loop will do:

1. Goal.
2. First cycle.
3. Team shape if any.
4. Verifier.
5. Stop condition.
6. Human gate.
7. Generated artifact paths.

Put evidence limitations after the loop design. In demand-driven mode, the source is the user's current goal, not historical transcript evidence.
