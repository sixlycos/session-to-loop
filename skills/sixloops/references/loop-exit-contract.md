# Loop Exit Contract

Use this reference before rendering any goal-ready loop, team loop, or adoption packet.

## Core Definition

A loop is not a long prompt. A loop is a stateful mechanism with an explicit exit protocol.

Every loop cycle must end with exactly one status:

- `CONTINUE`: keep going because another cycle can increase verified certainty.
- `DONE`: success criteria passed; return to the human for acceptance.
- `NEEDS_HUMAN`: the next decision belongs to a human after the loop has packaged evidence, options, impact, regression path, and recommendation, or because explicit approval is required. In user-facing copy, call this review-needed or return-to-user.
- `BLOCKED`: the loop cannot make reliable progress.
- `BUDGET_STOPPED`: the item, iteration, time, token, or cost cap was reached.

## Continue Rule

Continue only when all are true:

- The objective is unchanged.
- The next action stays inside approved scope.
- New evidence is available or likely from the next verifier.
- The Change Map can be updated or the next action can produce evidence for it.
- A verifier can reject bad output.
- Risk remains below the approved mode and explicit return points.
- The last cycle changed evidence, narrowed scope, reduced failures, or clarified the blocker.
- `next_cursor`, `next_expected_evidence`, and `next_verifier` are concrete enough for the next cycle to resume naturally.
- `next_cursor` names one selected path; mutually exclusive alternatives are recorded in `candidate_next_items` or a decision packet.
- No blocking `human_queue` item prevents the selected next cursor.
- Iteration, item, time, token, and cost budgets remain.

If the next round only adds effort without adding verifiable information, stop.

## Return To Human

Return to the human when:

- Success criteria pass. Status: `DONE`.
- Product, design, copy, translation, release, security, data, cost, or architecture judgment is needed and the decision packet already includes options, impact, regression path, and recommendation. Status: `NEEDS_HUMAN`.
- Push, merge, deploy, migration, deletion, credential change, permission change, production config, or billing-impacting action needs a stronger user-approved mode or explicit approval. Status: `NEEDS_HUMAN`.
- The verifier is missing, unavailable, flaky, ambiguous, or cannot explain the result. Status: `BLOCKED` or `NEEDS_HUMAN`.
- The same failure repeats twice. Status: `BLOCKED`.
- No evidence changes across two iterations. Status: `BLOCKED`.
- The next cursor is vague, contains unresolved alternatives, the next expected evidence is missing, or the next verifier cannot reject the next action. Status: `BLOCKED`.
- The fix expands scope beyond the approved loop. Status: `NEEDS_HUMAN`.
- The budget cap is reached. Status: `BUDGET_STOPPED`.

## Required Schema

Every goal-ready loop should include:

```yaml
loop_exit_contract:
  continue_only_if:
    - "Objective is unchanged."
    - "Next action stays inside approved scope."
    - "A verifier can reject bad output."
    - "The Change Map can be updated or the next action can produce evidence for it."
    - "New evidence changed or is likely from the next verifier."
    - "next_cursor, next_expected_evidence, and next_verifier are concrete."
    - "next_cursor names one selected path."
    - "No blocking human_queue item prevents the selected next_cursor."
    - "Risk stays below the approved mode and explicit return points."
    - "Iteration and item budgets remain."
  done_when:
    - "All success criteria pass with required pass evidence."
  needs_human_when:
    - "Human judgment is required after options, impact, regression path, and recommendation are recorded."
    - "A high-impact action requires explicit approval."
  blocked_when:
    - "Same failure repeats twice."
    - "No evidence changes across two iterations."
    - "The next cursor, expected evidence, verifier, or selected path is vague."
    - "Verifier is unavailable or ambiguous."
  budget_stopped_when:
    - "Iteration, item, time, token, or cost cap is reached."
  status_protocol:
    CONTINUE: "Only when another cycle can increase verified certainty."
    DONE: "Success criteria passed; return for acceptance."
    NEEDS_HUMAN: "Return to user after decision evidence is packaged or explicit approval is required."
    BLOCKED: "Reliable progress is not possible."
    BUDGET_STOPPED: "Budget cap reached."
```

## Rendering Rule

Do not hide this contract under generic stop conditions. User-facing artifacts should show:

- Continue only if.
- Change Map evidence condition.
- Done when.
- Needs human when.
- Blocked when.
- Budget stopped when.

This boundary matters more than the tool list because it decides whether the next cycle reduces rework or creates more rework.
