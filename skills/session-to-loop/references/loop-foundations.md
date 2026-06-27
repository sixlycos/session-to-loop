# Loop Foundations

Use this reference before recommending a `loop` mechanism.

## Prompt, Skill, Loop, Automation

- Prompt: one instruction, then the user decides the next step.
- Skill: reusable task instructions the agent can load on demand.
- Loop: a repeated observe-act-check cycle around a goal.
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

The six parts that usually realize those moves are:

- Automation: schedule or event trigger.
- Worktree or isolation: separate workspace for each parallel task.
- Skill: permanent task knowledge instead of a pasted wall of prompt.
- Connector: access to CI, issues, PRs, browser, Slack, Linear, GitHub, or other external systems.
- Sub-agent or evaluator: a skeptical checker separate from the generator.
- Memory: state on disk, in a board, or in another durable store.

## Required Loop Gates

Only recommend a managed loop when these gates are present:

- Repetition: the task recurs often enough to repay setup cost.
- Rejection: bad output can be automatically rejected by tests, checks, logs, screenshots, assertions, or a rubric.
- Completion: the agent can carry the work far enough without returning most of it to the user.
- Objectivity: "done" can be checked by observable criteria.
- State: each run records what was tried, what failed, and what should happen next.
- Stop: success and failure exits are explicit.
- Iteration cap: every run has a hard attempt limit.
- Human checkpoint: at least one door remains open for the human to review, reject, or redirect.

If any gate is missing, prefer a prompt, rule, skill, checklist, or approval gate.

## Common Loop Failures

- Nodding loop: verification is skipped and the maker approves its own work.
- Amnesiac loop: persistence is skipped and every run starts from zero.
- Manual loop: scheduling is skipped and the human still has to remember to run it.
- Blind loop: discovery is skipped and the human still chooses every task.
- Tangled loop: handoff or isolation is skipped and parallel agents collide.

Use these names when rejecting or downgrading a candidate. They are clearer than vague warnings like "needs more safety."

## Cost And Quality

Loops are not free. Each iteration rereads goal, context, state, failures, and proposed changes. Reviewer or sub-agent patterns improve quality, but usually double the model work.

Use these heuristics:

- Keep the first version lightweight.
- Prefer deterministic verifiers before model-based review.
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
Goal:
[objective]

Success criteria:
- [objective criterion 1]
- [objective criterion 2]
- [objective criterion 3]

Each round:
1. PLAN: state the next smallest action.
2. DO: produce or improve the result.
3. VERIFY: score against every criterion and list weak points.
4. DECIDE: stop only when every criterion passes; otherwise continue by fixing the weakest point.

Rules:
- Do not declare done before the criteria pass.
- Fix the lowest-scoring weakness first.
- Stop after [N] rounds and report the blocker.
```
