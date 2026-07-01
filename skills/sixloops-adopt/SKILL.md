---
name: sixloops-adopt
description: Use when the user replies start, continue, run, adopt, shrink, or reject for an existing SixLoops candidate, or asks to execute one stateful loop cycle.
---

# SixLoops Adopt

Run the next useful cycle of an existing SixLoops candidate, or shrink/reject
it when the candidate is not ready for automation. A cycle must keep the Change
Map alive: current X, target B, affected surfaces, regression path, rollout
waves, and decision packets.

## Workflow

1. Read `../sixloops/references/adopt-loop-runbook.md`.
2. Identify the selected candidate and mode from the user's exact reply string.
3. Read the latest card or adoption packet. Create one with
   `../sixloops/scripts/adopt_candidate.py` only when stateful reuse is needed.
4. Run at most one stateful cycle inside the approved mode.
   - Refresh the Change Map before choosing work.
   - Pick work by wave order, impact, verifier evidence, and reversibility.
   - If product, architecture, release, UI, data, or migration judgment appears,
     produce a decision packet with options, impact, regression path, and a
     recommendation before returning for review.
5. Update state and return exactly one status: `DONE`, `CONTINUE`,
   review-needed, `BLOCKED`, or `BUDGET_STOPPED`.

## Ask Before High-Impact Finalization

- Install generated project instructions.
- Push, merge, deploy, migrate, delete data, change credentials, alter billing,
  or call production APIs.
- Expand scope beyond the selected candidate and approved mode.
