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

- A compact decision table before detailed cards. Its job is to help the user choose, not to document the runbook.
- The table columns should make value obvious: rank, plan, what it does for the user, judgment, why it is ranked there, cost/risk, and the exact reply.
- "What it does for the user" should come from the AI-written `user_value` when present. It should read like a natural product promise, not a list of loop internals.
- Recommended start: `start <candidate-id> as <mode>`, `shrink <candidate-id> to skill`, or `reject <candidate-id>`.
- A short explanation of the top recommendation: why this one first, and why the others are not first.
- A compact candidate summary: what it does, how it chooses the next bounded shot, how it naturally resumes, how it verifies, when it stops or returns for review.

Do not expand Observe / Decide / Act / Verify / State for every candidate on the first screen. Put that execution protocol in the individual card or adoption packet after the user chooses a plan.

For demand-driven goal design, lead with the generated Change Map before the start plan: current X, target B, user perception, affected surfaces, regression or compatibility path, rollout waves, first cycle, autonomous next-shot policy, progression rhythm, team shape, verifier, stop condition, return point, and artifact paths. Make clear that the source is the user's current objective rather than historical transcript evidence.

For each proposal in the first screen, include only:

- Action overview row: rank, plan, what it does for the user, judgment, why it is ranked there, cost/risk, and the exact next reply.
- Start options: one recommended mode and exact reply strings such as `start ci-babysitter as low-risk edit`, `start ci-babysitter as worktree draft`, `shrink ci-babysitter to skill`, or `reject ci-babysitter`.
- Name: short and action-oriented.
- Run card: can start now, can confirm, can delegate, and next action.
- Objective: what the loop improves for this project.
- Recommended mode: read-only, low-risk edit, worktree draft, PR draft, scheduled read-only, or scheduled draft.
- Autonomous decision summary, progression summary, verifier, stop condition or return point, and the path to the full card.

Put the full first-cycle packet, mechanism decision, heartbeat, trigger, cycle steps, autonomy contract, progression contract, verifier box, iteration cap, acceptance contract, exit contract, explicit return points, and loop economics in the individual card or adoption packet. Do not make the user read those before choosing.

## Confirmation Shape

End the proposal section by asking the user to choose one of the actions rendered for that candidate. Do not show stronger modes that are not present in the card.

Make the execution surface explicit: `start <candidate-id> as <mode>` is a reply the user sends in the current chat, not a terminal command. The user does not need to copy the whole card unless they are handing the plan to another agent.

- `start <candidate-id> as read-only`
- `start <candidate-id> as low-risk edit`
- `start <candidate-id> as worktree draft`
- `start <candidate-id> as PR draft`
- `start <candidate-id> as scheduled read-only`
- `start <candidate-id> as scheduled draft`
- `shrink <candidate-id> to skill`
- `reject <candidate-id>`
- `rerun with narrower evidence`

Use scheduled options only for candidates whose recommended maturity is scheduled. If `can_delegate=no`, the first start option is `read-only`; otherwise shrink, reject, or rerun with better evidence.

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
`scripts/design_goal_loop.py`. Lead with the `GOAL.md` Change Map and execution contract. The agent-facing
harness files are `STATE.json`, `RUN.md`, `VERIFY.md`, `TEAM.md`, `HANDOFF.md`, and
`goal-loop-design.json`.

When the user explicitly asks to start a team loop and subagent tools are available, state which
roles will run this cycle, then use `TEAM.md` prompts for the needed subagents. Spawn maker roles
only when the chosen mode includes edit scope.

## Language

Match the user's language in the final response and in user-facing artifact headings, labels, explanations, and review text. Do not mix English section headings into a Chinese output or Chinese section headings into an English output.

Use English only for internal JSON fields, script names, file paths, artifact identifiers, status codes, and exact confirmation strings such as `start <candidate-id> as read-only`.

When the input is multilingual, choose the dominant language of the user's instruction and preserve exact code/status/command tokens as code spans. If the user writes in Chinese, the readable product surface should be Chinese first; do not force the user to parse English review labels.

For Chinese output, translate product labels such as "candidate", "recommendation", "return point", "first cycle", "verification", and "state" into Chinese. Keep only stable protocol tokens in English: candidate ids, file paths, commands, mode strings, status codes, and exact replies.

## Evidence Placement

Put evidence after the proposal. Evidence should answer "why this loop" instead of becoming the product itself.

For weak or risky candidates, explain the rejection in product language: not recurring enough, no
objective gate, agent cannot reproduce the failure, no hard stop, review load is too high, or human
judgment is the real bottleneck.

When source quality is limited, say it plainly:

- Native Codex or Claude transcript: strong source for user-language patterns.
- Project auxiliary evidence: good source for draft development loops, weaker source for user preference.
- Generic JSONL: usable only when the semantic shape is clear.
