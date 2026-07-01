# Adopt Loop Runbook

Use this workflow when the user replies with `start ...`, `continue ...`,
`run ...`, or asks to execute an existing SixLoops candidate.

## Goal

Run the next useful cycle inside the approved mode, update the Change Map,
progression fields, and state, and return one clear status: `DONE`,
`CONTINUE`, review-needed, `BLOCKED`, or `BUDGET_STOPPED`.

## Workflow

1. Identify the selected candidate and mode.
   - Use the exact reply string when present.
   - Prefer the most capable mode that is approved, reversible, and verifiable.
   - Do not infer approval for merge, deploy, production, credentials, data,
     payment, deletion, or schema changes.

2. Read the latest card or adoption packet.
   - Candidate card: `cards/<candidate-id>.md`.
   - Agent handoff: `claude-loops/<candidate-id>.md`.
   - Adoption packet: `GOAL.md`, `STATE.json`, `HANDOFF.md`, and optional
     `AGENTS-snippet.md`.

3. Create an adoption packet when stateful reuse is needed and none exists:

   ```bash
   python skills/sixloops/scripts/adopt_candidate.py \
     --candidates <candidates.json> \
     --candidate-id <candidate-id> \
     --mode "<mode>" \
     --out-dir <adoption-dir>
   ```

4. Run one bounded cycle.
   - Read state first.
   - Refresh the Change Map: current X, target B, user perception, affected
     surfaces, regression path, rollout waves, and open decisions.
   - Select at most 1-3 active items.
   - Prefer the next wave that improves the Change Map, lowers blast radius, or
     produces verifier evidence.
   - Act only inside the approved mode.
   - When a product, architecture, release, data, UI, or migration judgment is
     needed, write a decision packet with options, impact, regression path, and
     recommendation before returning for review.
   - Verify with the listed verifier.
   - Before returning `CONTINUE`, record the exact `next_cursor`,
     `next_expected_evidence`, `next_verifier`, and `human_friction_delta`.
   - `next_cursor` must be one selected, non-blocked path. Put other plausible
     next steps in `candidate_next_items`. If a human decision blocks the
     selected path, return review-needed instead of `CONTINUE`.
   - When multiple next actions are plausible, rank them by value, verifier,
     reversibility, risk, and approved mode; choose the best non-blocking shot
     before asking the user.
   - Start only the subagent roles needed for that shot, and stop them after
     their evidence or output is integrated into state.
   - Update state before stopping.

5. Return status.
   - `DONE`: acceptance checks passed with evidence.
   - `CONTINUE`: another cycle can improve the Change Map, verified certainty,
     or regression evidence; `next_cursor`, `next_expected_evidence`, and
     `next_verifier` are concrete; and budget remains.
   - review-needed: human judgment or explicit approval is required after the
     decision packet or approval evidence is ready.
   - `BLOCKED`: reliable progress is not possible with current evidence, or the
     next cursor / expected evidence / verifier is vague.
   - `BUDGET_STOPPED`: item, iteration, time, token, or cost cap was reached.

## Ask Before High-Impact Finalization

- Install `AGENTS-snippet.md` into project instructions.
- Push, merge, deploy, migrate, delete data, change credentials, alter billing,
  or call production APIs.
- Expand scope beyond the selected candidate and approved mode.
