# Loop Foundations

Use this reference before recommending a `loop` mechanism.

## Prompt, Skill, Loop, Automation

- Prompt: one instruction, then the user decides the next step.
- Skill: reusable task instructions the agent can load on demand.
- Loop: a repeated observe-decide-act-verify cycle around a goal.
- Automation: a trigger that starts the loop without the user opening a chat.

Do not collapse these into one mechanism. A task usually matures in this order:

1. Prove one manual run works.
2. Save the reusable instructions as a skill or checklist.
3. Add loop mechanics: verification, state, iteration cap, and stop conditions.
4. Only then add scheduled or lifecycle automation.

## Loop Core

Every real loop turn has five moves:

- Discovery: find this turn's work without the human handing it a list.
- Handoff: isolate and hand the task to the agent that will do the work.
- Verification: use an independent check that can say no.
- Persistence: write state outside the conversation.
- Scheduling: make the next turn happen by trigger or cadence.

Verification is the heart of the loop. Without an external check, the agent is mostly judging its own work.

Each operational turn has four beats:

- Observe: read state, inputs, logs, diffs, queues, and prior blockers.
- Decide: choose the next item, action, verifier, and escalation path.
- Act: make the smallest bounded move that the current evidence supports.
- Verify: run the independent check, record evidence, and decide whether to stop, continue, retry, or escalate.

Each cycle also needs a progression handoff. Before returning `CONTINUE`, the agent must write:

- What changed in the Change Map or verifier evidence.
- The exact next cursor: wave, item, file, route, log, check, or decision packet.
- Exactly one selected next cursor. Mutually exclusive alternatives belong in
  `candidate_next_items` or a decision packet, not in `next_cursor`.
- The next expected evidence.
- The next verifier that can reject bad output.
- Any blocking human decision or approval in `blocking_human_queue`.
- Whether the cycle removed or added repeated human work.

If the next cursor is vague, contains an unresolved "or" between paths, is
blocked by human judgment, or the next verifier cannot reject the action, stop
or return for review instead of continuing.

Before stopping for review, the model must first exercise autonomous judgment:

- Rank plausible next actions by user value, verifier availability,
  reversibility, risk, and progress toward the Change Map.
- Choose the best non-blocking action inside the approved mode instead of
  asking the user for ordinary engineering prioritization.
- Prefer a coherent sequence of bounded shots over one oversized one-shot.
- Start planner, checker, verifier, or maker roles only when the selected shot
  needs them; stop those roles after their output is integrated into state.
- Return to the user only when the selected path needs human judgment, stronger
  approval, or all useful non-blocking work is exhausted.

The six parts that usually realize those moves are:

- Automation: schedule or event trigger.
- Worktree or isolation: separate workspace for each parallel task.
- Skill: permanent task knowledge instead of a pasted wall of prompt.
- Connector: access to CI, issues, PRs, browser, Slack, Linear, GitHub, or other external systems.
- Sub-agent or evaluator: a skeptical checker separate from the generator.
- Memory: state on disk, in a board, or in another durable store.

## Work Shape Triage

Classify the work before recommending a loop:

- Process-shaped work: steps and order are known, results are predictable. Prefer a script, hook, or traditional automation.
- Tool-assisted work: the goal is known but the path varies and the human still chooses direction often. Prefer a skill, checklist, or decision packet until the agent can keep the loop moving.
- Goal-driven work: the user can define the objective, boundaries, checks, and escalation rules, while the agent can decide the next step. This is the real loop candidate.

Do not recommend a managed loop just because a task repeats. Recommend it when the repeated work needs an agent to observe, decide, act, verify, and resume.

## 30-Second Loop Check

Before proposing a `loop`, verify the candidate passes all five checks:

- Recurrence: it happens at least weekly, or multiple times inside a bounded workflow that will keep recurring.
- Objective rejection: tests, type checks, builds, lint, screenshots, logs, assertions, or a tight rubric can reject bad output.
- Reproduction environment: the agent can run the changed code, inspect failures, and get fresh evidence.
- Hard stop: iteration, time, token, item, or cost cap is explicit.
- Explicit return point: merge, deploy, dependency, credential, schema, data, payment, and production-impacting actions require the matching user-approved mode or human decision.

If one check fails, keep the recommendation as a prompt, rule, skill, hook, checklist, or decision packet.

Good first loops:

- CI failure triage.
- Dependency update PR drafts.
- Lint-and-fix passes.
- Flaky test reproduction.
- Issue-to-PR drafts when the test suite is strong.
- Frontend browser/route audits when screenshots or scripted checks can reject regressions.

Bad first loops:

- Architecture rewrites.
- Auth, payments, credentials, or security-sensitive flows.
- Production deploys or migrations.
- Vague product, strategy, or design judgment.
- Work where "done" is mostly a human taste or approval call.

## Heartbeat Options

Every loop needs a heartbeat. Pick the cheapest heartbeat that fits the risk:

- Session: repeat inside the current chat while the user is watching. Good for a long task with fast feedback.
- Goal: run until objective criteria pass or the iteration cap is hit. Good for test-fixing, migration queues, and document batches.
- Scheduled: run at a cadence such as daily or hourly. Good only after read-only or draft runs have earned trust.
- Event: run when CI fails, a PR opens, a changelog changes, or an issue arrives. Good when the trigger is specific and observable.

Frequency is the main cost driver. Lower frequency often saves more than shorter prompts.

## Minimum Viable Loop

Build the smallest loop that can prove value:

- One automation or trigger: session, goal, scheduled, or event.
- One skill or checklist: reusable project knowledge the agent rereads.
- One state file: durable record of what was tried, what changed, what failed, and what is next.
- One gate: objective verifier that can fail the work.

Order matters:

1. Make one manual run reliable.
2. Save the reusable instructions as a skill or checklist.
3. Add loop mechanics: state, verifier, hard cap, and explicit return points.
4. Schedule only after reviewed outputs are consistently accepted.

Use accepted change rate as the product metric. If fewer than half of outputs survive review, narrow the scope, improve the verifier, or turn the loop into a smaller mechanism until it earns loop status again.

## Start Mode Ladder

Recommend the strongest useful mode that is approved, reversible, and verifiable:

- `read-only`: inspect, rank, and report only.
- `low-risk edit`: make bounded local edits with direct evidence and focused verification.
- `worktree draft`: use an isolated branch or worktree for reversible exploratory changes.
- `PR draft`: verify and prepare reviewable output; leave push, merge, deploy, and release actions to the user-approved path.
- `scheduled read-only`: run unattended but only report and update state.
- `scheduled draft`: run unattended, draft changes inside agreed isolation, notify the human, and leave landing to review.
- `human-approved action`: perform a high-impact action only when the user explicitly grants that action and scope.

Do not frame high-impact work as impossible. Frame it as requiring a stronger mode, explicit approval, or a decision packet. A loop should earn more autonomy through accepted, verified output.

## Practical Archetypes

Use these archetypes to make proposals concrete:

- Engineering maintenance: CI triage, issue triage, dependency updates, recurring bug classes, framework migrations.
- Frontend verification: route audits, i18n checks, screenshots, visual regressions, browser-console checks.
- Monitoring and research: logs, service health, API changelogs, pricing pages, competitor signals.
- Document batch work: PDF summaries, structured report generation, proposal drafts, stale-doc updates.
- Personal or office operations: inbox triage, recurring reports, customer ticket cleanup.
- Business operations: pricing signals, churn signals, sales or HR review loops, quarterly decisions made continuous.

SixLoops is mainly for software development, but these archetypes help explain the loop shape in terms a user can approve or reject.

## Required Loop Gates

Only recommend a managed loop when these gates are present:

- Repetition: the task recurs often enough to repay setup cost.
- Rejection: bad output can be automatically rejected by tests, checks, logs, screenshots, assertions, or a rubric.
- Completion: the agent can carry the work far enough without returning most of it to the user.
- Objectivity: "done" can be checked by observable criteria.
- State: each run records what was tried, what failed, and what should happen next.
- Progression: each cycle records one selected next cursor, expected evidence,
  verifier, blocking human queue, and human-friction delta before continuing.
- Autonomy: the model selects the next bounded shot and controls role start/stop
  until human judgment or stronger approval is genuinely required.
- Stop: success and failure exits are explicit.
- Iteration cap: every run has a hard attempt limit.
- Return point: high-impact or judgment-heavy work has a clear place to come back with evidence, options, impact, and a recommendation.

If any gate is missing, prefer a prompt, rule, skill, checklist, or decision packet.

## Acceptance Contract

A managed loop must compile these gates into an acceptance contract:

- Acceptance checks: observable conditions that can say DONE.
- Verifier: deterministic commands first, read-only checker when commands cannot decide.
- Pass evidence: command output, status, screenshot, schema result, or explicit verifier note.
- Reject conditions: what makes the loop stop, shrink to a smaller mechanism, or ask for a human.
- State schema: what the loop writes before stopping so the next run can resume.
- Progression contract: what changed, where the next cycle resumes, what evidence it expects, and why continuing is justified.
- Autonomy contract: how the model ranks options, chooses the next bounded shot,
  starts/stops subagents, and avoids unnecessary human prompts.
- No-progress policy: how repeated failures or unchanged evidence stop the run.
- Return point: actions that require a stronger mode, explicit approval, or human judgment before they are finalized.

Do not render a goal-ready loop artifact when the acceptance contract is missing. Render a rule,
skill, checklist, decision packet, or rejection instead.

## Loop Exit Contract

Treat the exit contract as the center of the loop, not a footnote. A loop must decide whether the
next cycle increases verified certainty or only adds more effort.

Every cycle must end with exactly one status:

- `CONTINUE`: continue only when new verifier evidence can be gained, risk stays within scope, and budget remains.
- `DONE`: success criteria passed with pass evidence; return to the human for acceptance.
- review-needed: product, design, release, security, data, cost, architecture, or high-impact approval is required. Internal JSON may call this `NEEDS_HUMAN`.
- `BLOCKED`: the same failure repeated, evidence stopped changing, or the verifier is unavailable or ambiguous.
- `BUDGET_STOPPED`: item, iteration, time, token, or cost cap is reached.

Read `loop-exit-contract.md` when rendering goal-ready artifacts. If a proposal cannot say when to
continue and when to return to the human, turn it into a skill, checklist, or prompt.
If it cannot name one selected next cursor, next expected evidence, and next
verifier, do not continue the loop; update state and return `BLOCKED`,
review-needed, or `BUDGET_STOPPED` as appropriate.

## Minimum Loop Readiness

Before recommending unattended execution or draft-producing autonomy, require:

- Success criteria that a verifier can actually check.
- Hard caps for iterations, time, token, dollar, or item count.
- Isolated branch, checkout, or worktree for edits.
- Read-only checker, deterministic verifier, or both.
- State file that is read first and updated before stopping.
- Progression fields that are updated before continuing: `next_cursor`,
  `candidate_next_items`, `next_expected_evidence`, `next_verifier`,
  `blocking_human_queue`, and `human_friction_delta`.
- Return point for risky, irreversible, product, release, security, data, or cost decisions.
- Logs or notifications so failures, blockers, and created artifacts are visible.

If any item is missing, start lower on the mode ladder.

## Common Loop Failures

- Nodding loop: verification is skipped and the maker approves its own work.
- Early-success loop: the agent declares done before the verifier proves it.
- Amnesiac loop: persistence is skipped and every run starts from zero.
- Manual loop: scheduling is skipped and the human still has to remember to run it.
- Blind loop: discovery is skipped and the human still chooses every task.
- Tangled loop: handoff or isolation is skipped and parallel agents collide.
- Drift loop: long runs lose standing constraints unless they reread the goal, state, and project rules.
- Forked-cursor loop: `CONTINUE` points to multiple unresolved alternatives, so the next run chooses direction by vibe instead of state.
- Hidden-human-gate loop: `CONTINUE` is returned even though a human decision blocks the selected next action.
- Permission-creep loop: a read-only loop gains write or production permissions without a stronger approved mode and explicit return point.

Use these names when rejecting or shrinking a candidate. They are clearer than vague warnings like "needs more safety."

## Cost And Quality

Loops are not free. Each iteration rereads goal, context, state, failures, and proposed changes. Reviewer or sub-agent patterns improve quality, but usually double the model work.

Use these heuristics:

- Keep the first version lightweight.
- Prefer deterministic verifiers before model-based review.
- Use stronger models for planning and checking, cheaper models for routine execution when quality permits.
- Limit each cycle to 1-3 high-value items.
- Stop when the same failure repeats.
- Record state compactly.
- Treat accepted-result cost as the real cost, not raw attempts.
- If fewer than half of loop outputs are accepted after review, the loop probably needs a better verifier or a smaller scope.
- Read a small sample of loop output regularly to prevent comprehension rot.
- Keep a budget cap, retry cap, or time cap before unattended execution.

The four silent costs to look for are:

- Verification debt: output passes visible checks but is not actually right.
- Comprehension rot: the codebase changes faster than the human's map of it.
- Cognitive surrender: the human stops judging because the loop feels reliable.
- Token blowout: retries and helpers multiply cost while failing quietly.

## Maker And Checker

When quality matters, separate the maker from the checker:

- Maker: fast execution, local fixes, focused patching.
- Checker: stricter review, verification, regression search, risk assessment.

Do not let the maker be the only judge of success for nontrivial loops.

## Lightweight Loop Prompt Shape

When the task is not ready for automation, propose a lightweight loop prompt:

```text
Objective:
[objective]

Acceptance checks:
- [objective criterion 1]
- [objective criterion 2]
- [objective criterion 3]

Each cycle:
1. PLAN: state the next smallest action.
2. DO: produce or improve the result.
3. VERIFY: score against every criterion and list weak points.
4. DECIDE: stop only when every criterion passes; otherwise continue by fixing the highest-leverage failing point.

Rules:
- Do not declare done before the criteria pass.
- Fix the lowest-scoring weakness first.
- Stop after [N] rounds and report the blocker.
```
