---
name: sixloops-design
description: Use when the user gives a current development goal and asks to design a stateful agent loop, team loop, or subagent workflow, or to decide whether it should shrink to a skill or checklist.
---

# SixLoops Design

Turn a current objective into a complete Change Map and then a reusable loop
mechanism. Recommend a managed loop only when the agent can map current X to
target B, observe evidence, decide the next wave, act or draft a decision
packet, verify, preserve state, and stop without repeated user prompting.

## Workflow

1. Read `../sixloops/references/design-managed-loop.md`.
2. Build the first Change Map before choosing a start mode:
   - current X and target B,
   - how the user will perceive the transformation,
   - affected product and technical surfaces,
   - regression or compatibility checks,
   - rollout waves and decision packet triggers.
3. Test whether the goal is actually loop-shaped: recurring or continuing
   work, observable inputs, objective rejection signal, bounded actions, hard
   stop, and explicit return points for high-impact actions.
4. Run `../sixloops/scripts/design_goal_loop.py --goal "<goal>" --domain auto --team-mode auto --level auto --out-dir .sixloops/goal-design`
   only when an artifact packet is useful.
5. Present the Change Map first, then the start plan: why the user would start
   it, first cycle, verifier, stop condition, return point, selected mode, and artifact
   paths.

## Shrink Only When

- The goal is one-shot.
- The verifier cannot reject bad output.
- The work is only product judgment after evidence, impact, options, and
  regression path have already been packaged for a human.
- A rule, skill, checklist, or approval gate is the better first mechanism.
