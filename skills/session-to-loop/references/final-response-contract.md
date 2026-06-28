# Final Response Contract

Use this contract when presenting SixLoops results to a user.

## Lead With The Loop

Start with 1-3 concrete proposals the user can say yes or no to. Do not lead with transcript limitations, redaction notes, evidence tables, or file inventories unless the source quality blocks any recommendation.

For each proposal, include:

- Confirm this loop: one recommended action and exact reply strings such as `adopt ci-babysitter as goal-loop`, `shrink ci-babysitter to skill`, or `reject ci-babysitter`.
- First run packet: a compact starter goal prompt with goal, success criteria, each-round steps, state file, stop rule, and human gate.
- Name: short and action-oriented.
- Decision card: can use now, can confirm, can delegate, and next action.
- Goal: what the loop improves for this project.
- Mechanism decision: why this deserves a loop, why not a smaller mechanism, and why not a more autonomous scheduled loop yet.
- Heartbeat: session, goal, scheduled, or event.
- Recommended starting level: read-only, goal loop, isolated draft, PR draft, or scheduled draft.
- Trigger: when the user or agent should run it.
- Cycle: the observe-act-check steps.
- Verifier box: primary verifier, checker, required PASS evidence, and status protocol.
- Stop conditions: when the agent must stop.
- Iteration cap: the maximum number of rounds before it reports a blocker.
- Acceptance contract: success criteria, verifier, pass evidence, reject conditions, and no-progress policy.
- Approval boundary: what still needs human approval.
- Why this loop: the product reason plus the evidence basis.

## Confirmation Shape

End the proposal section by asking the user to choose one of these actions:

- `adopt <candidate-id> as read-only`
- `adopt <candidate-id> as goal-loop`
- `shrink <candidate-id> to skill`
- `reject <candidate-id>`
- `rerun with narrower evidence`

Ask once. Do not make the user approve each internal pipeline step after the scope has been confirmed.

## Language

Match the user's language in the final response. Use English for internal JSON fields, script names, and artifact identifiers.

## Evidence Placement

Put evidence after the proposal. Evidence should answer "why this loop" instead of becoming the product itself.

When source quality is limited, say it plainly:

- Native Codex or Claude transcript: strong source for user-language patterns.
- Project auxiliary evidence: good source for draft development loops, weaker source for user preference.
- Generic JSONL: usable only when the semantic shape is clear.
