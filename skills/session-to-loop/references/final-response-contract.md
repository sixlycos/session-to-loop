# Final Response Contract

Use this contract when presenting SixLoops results to a user.

## Lead With The Loop

Start with 1-3 concrete proposals the user can say yes or no to. Do not lead with transcript limitations, redaction notes, evidence tables, or file inventories unless the source quality blocks any recommendation.

For each proposal, include:

- Name: short and action-oriented.
- Goal: what the loop improves for this project.
- Work shape: why this deserves a loop instead of a script, skill, checklist, or gate.
- Heartbeat: session, goal, scheduled, or event.
- Recommended starting level: read-only, goal loop, isolated draft, PR draft, or scheduled draft.
- Trigger: when the user or agent should run it.
- Cycle: the observe-act-check steps.
- Verification: how the loop knows it worked.
- Stop conditions: when the agent must stop.
- Iteration cap: the maximum number of rounds before it reports a blocker.
- Approval boundary: what still needs human approval.
- Why this loop: the product reason plus the evidence basis.

## Confirmation Shape

End the proposal section by asking the user to choose one of these actions:

- Adopt the loop and generate the concrete loop card or skill.
- Convert it to a smaller mechanism, such as a rule, checklist, hook, or approval gate.
- Reject it for now.
- Run a narrower analysis with better transcript evidence.

Ask once. Do not make the user approve each internal pipeline step after the scope has been confirmed.

## Language

Match the user's language in the final response. Use English for internal JSON fields, script names, and artifact identifiers.

## Evidence Placement

Put evidence after the proposal. Evidence should answer "why this loop" instead of becoming the product itself.

When source quality is limited, say it plainly:

- Native Codex or Claude transcript: strong source for user-language patterns.
- Project auxiliary evidence: good source for draft development loops, weaker source for user preference.
- Generic JSONL: usable only when the semantic shape is clear.
