# Design Managed Loop

Use this workflow when the user gives a current objective and asks to design a
loop, team loop, or subagent workflow.

## Goal

Turn the user's current objective into a Change Map plus a bounded loop plan
that can run after one explicit approval, or shrink to a skill/checklist when
delegation is not justified.

## Workflow

1. Read `goal-loop-designer.md`.
2. Draft the Change Map before judging the mechanism:
   - current X and target B,
   - how the user or operator perceives the transformation,
   - affected product and technical surfaces,
   - regression, recovery, or compatibility checks,
   - rollout waves,
   - decision packets needed before human review.
   - progression fields required before `CONTINUE`: `next_cursor`,
     `next_expected_evidence`, `next_verifier`, and `human_friction_delta`.
   - autonomy policy: model chooses the next bounded shot, controls necessary
     roles, and asks the user only for true human judgment or stronger approval.
3. Decide whether the goal is loop-shaped:
   - continued or recurring work,
   - observable inputs,
   - objective rejection signal,
   - bounded actions,
   - hard iteration cap,
   - explicit return points for high-impact work.
4. Write a model-authored design JSON before running the direct goal script.
   The JSON is the semantic handoff; the script only normalizes and renders it:

   ```json
   {
     "domain": "architecture",
     "team_mode": "subagent-team",
     "level": "isolated-draft",
     "change_map": {
       "current_x": "...",
       "target_b": "...",
       "user_perception": "...",
       "transformation_thesis": "...",
       "affected_surfaces": ["..."],
       "regression_plan": ["..."],
       "rollback_or_compatibility": ["..."],
       "research_questions": ["..."],
       "waves": ["..."],
       "decision_packet_required_when": ["..."]
     },
     "rationale": {
       "why_this_loop": "...",
       "why_not_smaller": "...",
       "why_not_more_autonomous": "...",
       "fit_summary": "..."
     }
   }
   ```

5. Run the direct goal script when an artifact packet is useful:

   ```bash
   python skills/sixloops/scripts/design_goal_loop.py \
     --goal "<user goal>" \
     --model-design-file <model-authored.json> \
     --out-dir .sixloops/goal-design
   ```

   Do not use `auto` fields as semantic analysis when a capable host model is
   available; they are fallback scaffolding only.

6. Read generated `GOAL.md`, `STATE.json`, `RUN.md`, `VERIFY.md`, `TEAM.md`,
   `HANDOFF.md`, and `goal-loop-design.json`.
7. Present the Change Map first, then the start plan:
   - what X is,
   - what B is,
   - what it touches,
   - how it regresses or rolls back,
   - what waves the loop will execute,
   - why the user would start it,
   - first cycle,
   - progression rhythm,
   - autonomous decision and role-control policy,
   - verifier,
   - stop condition and return point,
   - selected mode,
   - generated artifact paths.

## Team Policy

Use team roles only when separation improves planning, implementation, review,
or verification. Spawn maker roles only inside explicit edit scope. If subagent
tools are unavailable, run the same roles sequentially and keep `TEAM.md` as a
handoff prompt.

## Shrink Only When

- The goal is one-shot and not worth state.
- The verifier cannot reject bad output.
- The work is only product judgment after the loop has already produced the
  evidence map, options, impact, regression path, and recommendation.
- The better first mechanism is a rule, skill, checklist, or approval gate.
