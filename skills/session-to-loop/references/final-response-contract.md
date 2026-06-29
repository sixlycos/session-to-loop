# Final Response Contract

Use this contract when presenting SixLoops results to a user.

## Lead With The Start Plan

Start with 1-3 concrete proposals the user can say yes or no to. Do not lead with transcript limitations, redaction notes, evidence tables, or file inventories unless the source quality blocks any recommendation.

The default close is a Start Plan, not an execution diary. The user should see what can start, which mode it needs, why it is worth trying, and the exact start string before seeing what the pipeline did.

Do not start with:

- "I processed N records..."
- "I redacted N snippets..."
- "I generated packets/artifacts..."
- A file inventory.
- A transcript quality disclaimer.

Start with:

- Recommended start: `start <candidate-id> as <mode>`, `shrink <candidate-id> to skill`, or `reject <candidate-id>`.
- What the loop will do.
- What it will not do.
- When it returns to the user for review.
- How it verifies.
- When it stops.
- Why this loop exists instead of a smaller or more autonomous mechanism.

For demand-driven goal design, lead with the generated start plan: objective, first cycle, team shape, verifier, stop condition, review boundary, and artifact paths. Make clear that the source is the user's current objective rather than historical transcript evidence.

For each proposal, include:

- Start options: one recommended mode and exact reply strings such as `start ci-babysitter as low-risk edit`, `start ci-babysitter as worktree draft`, `shrink ci-babysitter to skill`, or `reject ci-babysitter`.
- First cycle packet: a compact run packet with objective, acceptance checks, observe-decide-act-verify steps, state file, stop rule, and review boundary.
- Name: short and action-oriented.
- Run card: can start now, can confirm, can delegate, and next action.
- Objective: what the loop improves for this project.
- Mechanism decision: why this deserves a loop, why not a smaller mechanism, and why not a more autonomous scheduled loop yet.
- Heartbeat: session, goal, scheduled, or event.
- Recommended mode: read-only, low-risk edit, worktree draft, PR draft, scheduled read-only, or scheduled draft.
- Trigger: when the user or agent should run it.
- Cycle: the observe-decide-act-verify steps.
- Verifier box: primary verifier, checker, required PASS evidence, and status protocol.
- Stop conditions: when the agent must stop.
- Iteration cap: the maximum number of rounds before it reports a blocker.
- Acceptance contract: success criteria, verifier, pass evidence, reject conditions, and no-progress policy.
- Exit contract: when to return `CONTINUE`, `DONE`, review-needed, `BLOCKED`, or `BUDGET_STOPPED`.
- Review boundary: what needs a stronger mode, explicit approval, or human review.
- Why this loop: the product reason plus the evidence basis.
- Loop economics: expected trigger frequency, review load, accepted-output target, and when to demote the loop.

## Confirmation Shape

End the proposal section by asking the user to choose one of the actions rendered for that candidate. Do not show stronger modes that are not present in the card.

- `start <candidate-id> as read-only`
- `start <candidate-id> as low-risk edit`
- `start <candidate-id> as worktree draft`
- `start <candidate-id> as PR draft`
- `start <candidate-id> as scheduled read-only`
- `start <candidate-id> as scheduled draft`
- `shrink <candidate-id> to skill`
- `reject <candidate-id>`
- `rerun with narrower evidence`

Use scheduled options only for candidates whose recommended maturity is scheduled. If `can_delegate=no`, the safe start option is `read-only`; otherwise shrink, reject, or rerun with better evidence.

Ask once. Do not make the user approve each internal pipeline step after the scope has been confirmed.

Put run notes after the confirmation section, and keep them short:

- Artifact paths.
- Source quality or limitation if it affects confidence.
- Private evidence location when needed.
- Any blocker that changes the decision.

Do not narrate every internal step unless the user asks for an audit trail.

After the user confirms `start <candidate-id> as <mode>`, either run the first controlled cycle in
that mode or generate the adoption packet with
`scripts/adopt_candidate.py --mode "<mode>"`. The user-facing next artifact should be concrete: `GOAL.md`,
`STATE.json`, `HANDOFF.md`, and a draft `AGENTS-snippet.md`. Do not silently install the
snippet into project instructions.

When the user asks to design from a goal, generate the goal-design packet with
`scripts/design_goal_loop.py`. The user-facing artifacts should be `GOAL.md`, `TEAM.md`,
`STATE.json`, `HANDOFF.md`, and `goal-loop-design.json`.

When the user explicitly asks to start a team loop and subagent tools are available, state which
roles will run this cycle, then use `TEAM.md` prompts for the needed subagents. Spawn maker roles
only when the chosen mode includes edit scope.

## Language

Match the user's language in the final response. Use English for internal JSON fields, script names, and artifact identifiers.

## Evidence Placement

Put evidence after the proposal. Evidence should answer "why this loop" instead of becoming the product itself.

For weak or risky candidates, explain the rejection in product language: not recurring enough, no
objective gate, agent cannot reproduce the failure, no hard stop, review load is too high, or human
judgment is the real bottleneck.

When source quality is limited, say it plainly:

- Native Codex or Claude transcript: strong source for user-language patterns.
- Project auxiliary evidence: good source for draft development loops, weaker source for user preference.
- Generic JSONL: usable only when the semantic shape is clear.
