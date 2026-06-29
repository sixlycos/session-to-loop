# Final Response Contract

Use this contract when presenting SixLoops results to a user.

## Lead With The Loop

Start with 1-3 concrete proposals the user can say yes or no to. Do not lead with transcript limitations, redaction notes, evidence tables, or file inventories unless the source quality blocks any recommendation.

For demand-driven goal design, lead with the generated goal loop: goal, first cycle, team shape, verifier, stop condition, human gate, and artifact paths. Make clear that the source is the user's current objective rather than historical transcript evidence.

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
- Cycle: the observe-decide-act-verify steps.
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

After the user confirms `adopt <candidate-id> as <level>`, generate the adoption packet with
`scripts/adopt_candidate.py`. The user-facing next artifact should be concrete: `GOAL.md`,
`STATE.json`, `HANDOFF.md`, and a draft `AGENTS-snippet.md`. Do not silently install the
snippet into project instructions.

When the user asks to design from a goal, generate the goal-design packet with
`scripts/design_goal_loop.py`. The user-facing artifacts should be `GOAL.md`, `TEAM.md`,
`STATE.json`, `HANDOFF.md`, and `goal-loop-design.json`.

When the user explicitly asks to start a team loop and subagent tools are available, state which
roles will run this cycle, then use `TEAM.md` prompts for the needed subagents. Do not spawn maker
roles unless edit scope is explicit.

## Language

Match the user's language in the final response. Use English for internal JSON fields, script names, and artifact identifiers.

## Evidence Placement

Put evidence after the proposal. Evidence should answer "why this loop" instead of becoming the product itself.

When source quality is limited, say it plainly:

- Native Codex or Claude transcript: strong source for user-language patterns.
- Project auxiliary evidence: good source for draft development loops, weaker source for user preference.
- Generic JSONL: usable only when the semantic shape is clear.
