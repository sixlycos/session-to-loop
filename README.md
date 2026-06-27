# SixLoops

Turn yesterday's AI coding friction into tomorrow's reusable agent loops.

SixLoops is an open-source Agent Skill for mining local AI coding session logs and project evidence, then proposing the rules, skills, hooks, checklists, approval gates, or managed loops that would make the next agent run better.

It is not a chat summarizer. It is a loop engineering assistant for software teams and solo developers who keep correcting the same AI behaviors.

The installed Codex skill is currently named `$session-to-loop` for compatibility. The product name is SixLoops.

## Why The Name

A serious loop needs six parts: automation, isolation, skill, connector, evaluator, and memory.

SixLoops helps you find which of those parts your project is missing, then turns repeated AI-coding friction into a concrete loop proposal.

## What Is A Session Log?

A session log is the saved JSONL record of an AI coding conversation: user messages, tool calls, command output, status events, and sometimes assistant messages.

Some tools and docs call these files "transcripts." In this project, read "transcript" as "AI session log." It is not a movie subtitle file and it is not meant to be read manually.

## Why This Exists

Good developers repeatedly teach coding agents the same lessons:

- "Read the CI log before guessing."
- "Use pnpm here, not npm."
- "Do not deploy without approval."
- "After UI changes, run the browser check and screenshot the route."
- "This provider can return HTTP 200 while still failing semantic assertions."

Those lessons should not live only in one chat. SixLoops turns them into durable mechanisms the next agent can actually use.

## What You Get

The first screen is a small set of proposals, not an evidence dump.

Each proposal is a Loop Card. It says:

- Decision card: can use now, can confirm, can delegate, and next action.
- Goal: what gets better.
- Work shape: why this should be a loop instead of a script, skill, checklist, or gate.
- Heartbeat: whether it should start as a session loop, goal loop, scheduled run, or event trigger.
- Starting level: read-only report, goal loop, isolated draft, PR draft, or scheduled draft.
- Trigger: when the loop starts.
- Cycle: what the agent observes, does, and checks.
- Verification: how success is known.
- Stop conditions: when the agent must stop.
- Iteration cap: the maximum number of rounds before it reports a blocker.
- Acceptance contract: success criteria, verifier, pass evidence, reject conditions, and no-progress policy.
- Approval boundary: what still needs a human.
- Why this loop: the reason plus the evidence basis.

Example:

```text
Browser Audit Loop

Decision card: can use now = limited, can confirm = yes, can delegate = yes.
Goal: Catch frontend route, copy, and i18n regressions before handoff.
Trigger: After frontend, routing, copy, auth UI, or i18n changes.
Cycle: identify changed routes, run checks, open the route in a browser,
capture screenshots, fix at most 1-3 confirmed regressions, record state.
Verification: target routes render, screenshots confirm the main path, i18n passes.
Acceptance contract: DONE only when checks and screenshots pass; BLOCKED on auth/data/design judgment.
Stop: auth/data blocks verification, visual direction needs approval, or routes pass.
Iteration cap: 8 rounds.
Approval boundary: product copy, visual direction, auth/data fixture changes.
```

## When A Loop Is Worth It

A loop is not just a prompt that repeats. A useful loop needs four things:

- Repetition: the task happens often enough to repay setup cost.
- Rejection: bad output can be rejected by tests, type checks, lint, screenshots, logs, assertions, or a rubric.
- Completion: the agent can carry the work far enough without handing most of it back to you.
- Objectivity: "done" can be checked by observable criteria.

If those are missing, SixLoops should recommend a prompt, rule, skill, checklist, approval gate, or reject instead.

A real loop also needs five moves: discovery, handoff, verification, persistence, and scheduling. If one is missing, the loop usually becomes one of five failures: blind, tangled, nodding, amnesiac, or manual.

The safest build order is:

1. Prove one manual run works.
2. Save the reusable instructions as a skill or checklist.
3. Add loop mechanics: verifier, state file, iteration cap, and stop conditions.
4. Only then add scheduled or lifecycle automation.

SixLoops should recommend the lowest useful level first. A good proposal may start as a read-only report or goal loop before it earns isolated edits, PR drafts, or scheduled execution.

## Why Not Just Ask Codex To Notice Patterns?

You can ask an agent to "look at my past work and improve itself." The problem is that raw context is noisy, expensive, and easy to misuse.

SixLoops is more effective because it separates the job into two parts:

- Deterministic scripts do discovery, source classification, redaction, packet building, hard gates, and rendering.
- The host AI does the part it is good at: semantic grouping and judgment.

That gives you better behavior than a one-off prompt:

- It does not load entire session logs into context.
- It keeps user messages as primary evidence and tool events as supporting evidence.
- It distinguishes Codex logs, Claude Code logs, generic JSONL logs, and project auxiliary evidence.
- It asks once for analysis scope, then avoids approval theater.
- It turns findings into concrete mechanisms, not vague advice.
- It rejects one-off noise instead of overfitting a rule from a single incident.

## What Makes It Different

Most useful skills win because they have a sharp behavior:

- `grill-me` wins by changing the conversation: one question at a time until the plan is clear.
- `ponytail` wins by changing the default engineering reflex: find the smallest correct solution.
- `superpowers` wins by changing the development lifecycle: plan, implement, review, verify.

SixLoops' job is different: it learns which of those behaviors your project actually needs.

It does not try to replace planning, review, frontend QA, CI triage, or deployment gates. It proposes which of those should become a durable loop for this repository, based on evidence from your own agent sessions and project records.

## Inputs

Supported now:

- Codex JSONL session logs.
- Claude Code JSONL session logs.
- Generic JSONL logs with `user`, `assistant`, or `tool` records.
- Project auxiliary evidence such as browser audits, soak tests, CI logs, eval outputs, and result JSONL files.

Planned or partial:

- Project context packets such as `AGENTS.md`, `CLAUDE.md`, package scripts, and recent git history.
- Richer generated hooks and ready-to-install project skills.

## Outputs

- Loop Engineering Playbook.
- Loop Cards.
- Draft managed loop prompts that can be delegated like a goal after approval.
- Draft Agent Skills.
- Draft `AGENTS.md` or `CLAUDE.md` rules.
- Approval gate and checklist drafts.
- Eval cases for checking whether the generated workflow improves future sessions.

## Quick Start

Try SixLoops without private logs first:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input evals/fixtures/repeated-ci-failure.jsonl \
  --out-root .session-to-loop/tmp/repeated-ci \
  --approve \
  --rule-fallback
```

Open `.session-to-loop/tmp/repeated-ci/public/loop-playbook.md` to see the generated Loop Card.

For real local logs:

```bash
python skills/session-to-loop/scripts/session_to_loop.py --input <session-log-file-or-dir>
```

For real local logs, the pipeline stops after creating an analysis scope. Review the listed files, then approve the same narrow scope:

```bash
python skills/session-to-loop/scripts/session_to_loop.py --input <session-log-file-or-dir> --approve
```

The command creates compact packets and points the host AI to:

```text
skills/session-to-loop/references/semantic-analysis-prompt.md
```

After the host AI writes `semantic-candidates.json`, render the guarded artifacts:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input <session-log-file-or-dir> \
  --scope .session-to-loop/private/analysis-scope.json \
  --semantic-candidates .session-to-loop/private/semantic-candidates.json
```

## Install For Codex

Copy or link the skill folder into your Codex skills directory:

```powershell
$dest = "$env:USERPROFILE\.codex\skills\session-to-loop"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path .\skills\session-to-loop\* -Destination $dest -Recurse -Force
```

Then start a new Codex thread and invoke:

```text
Use $session-to-loop (SixLoops) to find the first loop in this repo worth trying. Reject weak patterns, stay read-only, and return 1-3 Loop Cards with verifier, state, stop condition, and human gate.
```

## Interaction Model

The skill should feel like this:

1. Discover likely local inputs from the explicit path you gave it.
2. Ask one scope question if reading real logs needs confirmation.
3. Build compact, redacted analysis packets.
4. Let the host AI infer repeated semantic patterns.
5. Present 1-3 loop proposals first.
6. Ask which proposal to adopt, shrink, or reject.
7. Generate concrete loop cards, skills, hooks, checklists, or approval gates only after confirmation.

It should not feel like this:

- "I found some files. Please approve every internal step."
- "Here is a pile of evidence."
- "Privacy is the main product."
- "Everything should become a loop."

## Mechanism Selection

| Pattern | Mechanism |
| --- | --- |
| Stable project fact | `AGENTS.md` or `CLAUDE.md` rule |
| Person-specific preference | Memory or local rule |
| Repeatable on-demand workflow | Agent Skill |
| Deterministic lifecycle check | Hook or script |
| Repeated observe-act-check cycle with state, verification, resume policy, and stop conditions | Loop |
| High-risk human decision | Approval gate or checklist |
| One-off event | Reject |

## Privacy And Safety

Local-first behavior is a guardrail, not the product pitch.

- No network access is needed by the pipeline.
- No whole-disk or broad home-directory scan is performed by default.
- Raw logs stay under `.session-to-loop/private/` or `.session-to-loop/tmp/`.
- Redaction runs before shareable artifacts are rendered.
- Session content is treated as untrusted data.
- The skill is read-only by default and does not install hooks, edit project files, commit, push, deploy, or call production APIs unless the user explicitly asks.

## Repository Layout

```text
skills/session-to-loop/
  SKILL.md
  agents/openai.yaml
  references/
  assets/templates/
  scripts/

evals/
  evals.json
  fixtures/
```

## Current Status

Experimental but usable.

SixLoops works today for synthetic fixtures, Codex JSONL logs, Claude Code JSONL logs, generic JSONL logs, and explicit project evidence JSONL. The next milestone is to make generated artifacts easier to install directly into a target repository.

## Development

Validate the skill:

```bash
python C:/Users/Administrator/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/session-to-loop
```

Run a representative fixture:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input evals/fixtures/auxiliary-project-evidence.jsonl \
  --out-root .session-to-loop/tmp/auxiliary \
  --approve \
  --rule-fallback
```
