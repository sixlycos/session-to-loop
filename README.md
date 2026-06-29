# SixLoops

**Turn repeated AI coding mistakes into reusable agent loops.**

SixLoops is an open-source Agent Skill that looks at local Codex / Claude Code session logs, project evidence, or a direct development goal, then proposes the **rules, skills, hooks, checklists, approval gates, or managed loops** your repo should have.

It is not a chat summarizer. It is a **loop engineering assistant** for software teams and solo developers who keep correcting the same agent behavior.

The **six** in SixLoops is the control surface every useful coding loop needs: **scope, state, verifier, budget, human gate, and adoption feedback**. This is why SixLoops does not just make prompts longer; it decides whether a repeated behavior deserves a loop at all.

The repository is named `sixloops`. The installed skill folder remains `session-to-loop` for Codex / Claude compatibility, so invoke it as `$session-to-loop` in Codex or `session-to-loop` in Claude Code.

![Let's loop meme](assets/readme/lets-loop-meme.png)

## Before / After

| Before | After |
| --- | --- |
| "CI is red again. Read the logs before guessing." | **CI Babysitter Loop** with state, verifier, iteration cap, and push/merge review boundary. |
| "Don't use npm in this repo." | **Package-manager rule** or checklist, not a full loop. |
| "After UI changes, open the route and screenshot it." | **Browser Audit Loop** with route discovery, screenshot evidence, and visual/product stop gates. |
| "Deploy only after I approve." | **Approval gate**, not autonomous deployment. |

See complete examples:

- [CI Babysitter](examples/ci-babysitter/README.md)
- [Frontend Browser Audit](examples/frontend-browser-audit/README.md)

## What It Does

SixLoops helps you answer one practical question:

**What should my agent remember, check, automate, or stop doing next time?**

It can turn repeated patterns like these:

- "Read the CI log before guessing."
- "Use pnpm here, not npm."
- "Do not deploy without approval."
- "After UI changes, run the browser check and screenshot the route."
- "HTTP 200 is not enough; run the semantic assertion too."

Into concrete artifacts:

- **Start Plans**: 1-3 confirmable loop proposals, not an evidence dump.
- **Goal loops**: `GOAL.md`, `STATE.json`, `HANDOFF.md`, and optional `TEAM.md`.
- **Rules / skills / hooks / checklists**: smaller mechanisms when a full loop is too much.
- **Approval gates**: hard boundaries for deploys, migrations, credentials, schema changes, and other high-impact work.
- **Eval cases**: fixtures that check whether generated workflows behave better over time.

## Why It Is Useful

Asking an agent to "notice patterns in my history" is expensive and unreliable. Raw session logs are noisy, long, and easy to misuse.

SixLoops makes the job smaller:

1. **Local scripts** discover, normalize, redact, select compact packets, and apply deterministic guardrails.
2. **The host AI** reads the compact packets and performs semantic judgment.
3. **The renderer** returns startable loop plans with stop conditions, verifier, state, and review boundaries.

![SixLoops semantic analysis turns noisy packets into loop cards](assets/readme/semantic-kitchen.png)

This is more useful than a long prompt because SixLoops:

- Keeps user messages as primary evidence and tool events as supporting evidence.
- Avoids loading whole session logs into context.
- Separates semantic judgment from deterministic safety checks.
- Rejects one-off noise instead of creating fake rules.
- Produces a mechanism you can actually start, shrink, or reject.

## Quick Start

Pasting the GitHub URL into Codex or Claude does not automatically install the skill. Run an install command, or copy the `skills/session-to-loop` folder into your local skills directory.

### 1. Install For Codex

From this repo:

```powershell
.\scripts\install.ps1 -Target codex
```

One-line install from GitHub:

```powershell
git clone https://github.com/sixlycos/sixloops.git; cd sixloops; .\scripts\install.ps1 -Target codex
```

Then start a new Codex thread and ask:

```text
Use $session-to-loop to find the first loop in this repo worth trying.
Return 1-3 Start Plans with verifier, state, stop condition, and review boundary.
Reject weak patterns.
```

Manual Codex install:

```powershell
$dest = "$env:USERPROFILE\.agents\skills\session-to-loop"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path .\skills\session-to-loop\* -Destination $dest -Recurse -Force
```

### 2. Install For Claude Code

User-level install:

```powershell
.\scripts\install.ps1 -Target claude -Scope user
```

One-line user install from GitHub:

```powershell
git clone https://github.com/sixlycos/sixloops.git; cd sixloops; .\scripts\install.ps1 -Target claude -Scope user
```

Project-level install for a repo:

```powershell
.\scripts\install.ps1 -Target claude -Scope project -ProjectPath E:\path\to\your-project
```

Manual Claude Code install:

```powershell
$dest = "$env:USERPROFILE\.claude\skills\session-to-loop"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path .\skills\session-to-loop\* -Destination $dest -Recurse -Force
```

Then invoke the skill in Claude Code by name:

```text
Use session-to-loop to design a loop for this project.
```

### 3. Try It Without Private Logs

Run the synthetic fixture demo:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input evals/fixtures/repeated-ci-failure.jsonl \
  --out-root .session-to-loop/tmp/repeated-ci \
  --approve \
  --rule-fallback
```

Open:

```text
.session-to-loop/tmp/repeated-ci/public/loop-playbook.md
```

You should see actions like:

- `start ci-babysitter as read-only`
- `start ci-babysitter as low-risk edit`
- `start ci-babysitter as worktree draft`
- `start ci-babysitter as PR draft`
- `shrink ci-babysitter to skill`
- `reject ci-babysitter`

### 4. Design A Loop From A Goal

You do not need session logs to start:

```bash
python skills/session-to-loop/scripts/design_goal_loop.py \
  --goal "After frontend changes, verify changed routes with browser screenshots, fix low-risk regressions, and stop when review or product judgment is needed." \
  --domain frontend \
  --team-mode auto \
  --level auto \
  --out-dir .session-to-loop/tmp/frontend-goal \
  --overwrite
```

The output folder contains:

- `GOAL.md`
- `TEAM.md`
- `STATE.json`
- `HANDOFF.md`
- `AGENTS-snippet.md`

![SixLoops can design a small agent team around one controlled loop](assets/readme/subagent-loop-table.png)

## Real Session Log Workflow

Run against an explicit file or narrow directory:

```bash
python skills/session-to-loop/scripts/session_to_loop.py --input <session-log-file-or-dir>
```

For real logs, SixLoops first creates an analysis scope. Review the files and approve the same narrow scope:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input <session-log-file-or-dir> \
  --approve
```

For larger approved sets, cap the semantic review cost:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input <session-log-file-or-dir> \
  --approve \
  --max-packets 120 \
  --target-token-budget 16000 \
  --role-quota user=60 \
  --role-quota tool=40
```

This creates:

```text
.session-to-loop/private/analysis-packets.jsonl
.session-to-loop/private/analysis-packets-index.json
.session-to-loop/private/analysis-run.json
```

The host AI reads:

```text
skills/session-to-loop/references/semantic-analysis-prompt.md
skills/session-to-loop/schemas/semantic-candidates.schema.json
.session-to-loop/private/analysis-packets.jsonl
```

Then it writes:

```text
.session-to-loop/private/semantic-candidates.json
```

Continue with the command stored in `analysis-run.json`, or run:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input <session-log-file-or-dir> \
  --scope .session-to-loop/private/analysis-scope.json \
  --semantic-candidates .session-to-loop/private/semantic-candidates.json
```

`--rule-fallback` exists for offline fixtures, synthetic evals, and host-AI-unavailable mode. It is not the main product path.

## Package A Release Zip

Create a portable skill archive:

```bash
python scripts/package_skill.py
```

This writes:

```text
dist/sixloops-skill.zip
```

Unzip it into one of these directories:

- Codex user skills: `~/.agents/skills/`
- Claude Code user skills: `~/.claude/skills/`
- Project skills: `<repo>/.agents/skills/` or `<repo>/.claude/skills/`

## What The User Sees

The first useful screen should be **1-3 Start Plans**.

Each card says:

- **What this loop will do**
- **What it will not do**
- **When it returns to you**
- **How it verifies**
- **When it stops**
- **Why it is worth existing**
- **How to start, shrink, or reject it**

Example:

```text
Browser Audit Loop

Start: start browser-audit as low-risk edit
Objective: Catch frontend route, copy, and i18n regressions before handoff.
Trigger: After frontend, routing, copy, auth UI, or i18n changes.
Cycle: identify changed routes, run checks, open the route in a browser,
capture screenshots, fix at most 1-3 confirmed regressions, record state.
Verifier: target routes render, screenshots confirm the main path, i18n passes.
Stop: auth/data blocks verification, visual direction needs approval, or routes pass.
Review boundary: product copy, visual direction, auth/data fixture changes.
```

## When A Loop Is Worth It

A loop is not a long prompt. It is a controlled state machine that finds work, hands it to an agent, checks the result, writes state, and decides the next move.

Use a loop only when the work passes the fast loop check:

- **Repeats often enough**: usually weekly or more. One-off work should stay a prompt.
- **Has an objective gate**: tests, type checks, builds, lint, screenshots, logs, assertions, or a tight rubric can reject bad output.
- **Can be reproduced by the agent**: the agent can run the code, inspect the failure, and see whether it improved.
- **Has a hard stop**: iteration, time, token, item, or cost cap.
- **Keeps a review boundary**: merge, deploy, dependency, credential, schema, data, payment, and production-impacting actions require the matching user-approved mode or review.

Good first loops are small, recurring, and machine-checkable:

- CI failure triage.
- Dependency update PR drafts.
- Lint-and-fix passes.
- Flaky test reproduction.
- Issue-to-PR drafts on codebases with strong tests.
- Frontend route/browser audit after UI changes.

Bad first loops should be rejected or downgraded:

- Architecture rewrites.
- Auth, payments, credentials, or security-sensitive flows.
- Production deploys and migrations.
- Vague product or design judgment.
- Anything where "done" is mostly taste, politics, or strategy.

The minimum viable loop is deliberately boring:

1. Make one manual run reliable.
2. Save the repeatable knowledge as a skill or checklist.
3. Add one state file, one verifier, one hard cap, and one review boundary.
4. Only then add a schedule or event trigger.

The most important part is the exit contract:

![SixLoops exit gates: continue, done, or ask the human](assets/readme/exit-gates.png)

- `CONTINUE`: another cycle can increase verified certainty.
- `DONE`: success criteria passed; return to the human for acceptance.
- Review needed: product, design, release, data, security, cost, architecture, or approval judgment is required.
- `BLOCKED`: the same failure repeated, evidence stopped changing, or the verifier is unavailable or ambiguous.
- `BUDGET_STOPPED`: the iteration, item, time, token, or cost cap was reached.

If the pattern is weak, rare, risky, or mostly human judgment, SixLoops should recommend a smaller mechanism: rule, skill, hook, checklist, approval gate, or reject.

The metric that matters is **cost per accepted change**. If fewer than half of loop outputs survive review, the loop is not saving work yet; shrink the scope, improve the gate, or demote it to a skill/checklist.

SixLoops should explicitly guard against common money pits:

- **Early-success loops**: the agent declares done before the verifier proves it.
- **Self-grading loops**: the maker is the only checker.
- **Amnesiac loops**: no state file, so every run restarts from zero.
- **Goal drift**: long runs forget constraints unless they reread the standing goal/spec.
- **Comprehension debt**: code changes faster than humans read and understand it.
- **Permission creep**: a read-only loop quietly becomes write-capable without a fresh gate.

## Supported Inputs

- **Direct user goals** for goal-ready loop design.
- **Codex JSONL session logs**.
- **Claude Code JSONL session logs**.
- **Generic JSONL logs** with `user`, `assistant`, or `tool` records.
- **Project auxiliary evidence** such as browser audits, soak tests, CI logs, eval outputs, and result JSONL files.

## Outputs

- `loop-playbook.md`
- Start Plans
- Draft managed loop prompts
- Goal-first loop designs with `GOAL.md`, `TEAM.md`, `STATE.json`, and `HANDOFF.md`
- Draft Agent Skills
- Draft `AGENTS.md` / `CLAUDE.md` snippets
- Approval gate and checklist drafts
- Eval cases

## Install Modes

### Codex

| Mode | Best For | Command |
| --- | --- | --- |
| User install | Personal daily use | `.\scripts\install.ps1 -Target codex` |
| One-line GitHub install | Quick local tryout | `git clone https://github.com/sixlycos/sixloops.git; cd sixloops; .\scripts\install.ps1 -Target codex` |
| Release zip | Offline or pinned version install | Unzip `sixloops-skill.zip` into `%USERPROFILE%\.agents\skills` |
| Manual install | Environments without PowerShell script execution | Copy `skills/session-to-loop` to `%USERPROFILE%\.agents\skills\session-to-loop` |
| Direct path invocation | Testing without installing | Reference `skills/session-to-loop/SKILL.md` directly in a Codex prompt |

### Claude Code

| Mode | Best For | Command |
| --- | --- | --- |
| User install | Personal use across projects | `.\scripts\install.ps1 -Target claude -Scope user` |
| Project install | Team-shared repo workflow | `.\scripts\install.ps1 -Target claude -Scope project -ProjectPath <repo>` |
| One-line GitHub install | Quick local tryout | `git clone https://github.com/sixlycos/sixloops.git; cd sixloops; .\scripts\install.ps1 -Target claude -Scope user` |
| Release zip | Offline or pinned version install | Unzip `sixloops-skill.zip` into `%USERPROFILE%\.claude\skills` |
| Manual install | Environments without script execution | Copy to `~/.claude/skills/session-to-loop` or `<repo>/.claude/skills/session-to-loop` |

### macOS / Linux

```bash
chmod +x scripts/install.sh
./scripts/install.sh codex user
./scripts/install.sh claude user
./scripts/install.sh claude project /path/to/your-project
```

### Claude.ai

SixLoops is designed for local coding agents because it needs filesystem access to session logs and project evidence. Claude.ai custom-skill upload can carry the instructions, but the local pipeline is most useful in Claude Code.

## How It Works

```text
explicit input path
  -> discover sessions
  -> ask one scope question
  -> redact + normalize
  -> build compact analysis packets
  -> host AI semantic analysis
  -> deterministic guardrails
  -> Start Plans / playbook / adoption packet
```

The host AI decides:

- What the user repeatedly corrects.
- What tool use reveals about failure paths.
- Which verification actions are habits.
- Which boundaries must return to the human.
- Whether the mechanism should be rule, skill, hook, loop, checklist, approval gate, or reject.

The scripts decide:

- Which files are in scope.
- What packet budget is passed to the AI.
- Whether output structure is valid.
- Whether a candidate can be delegated.
- Whether public artifacts contain obvious sensitive data.

## Default Boundaries

Local-first behavior is a guardrail, not the main product pitch.

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
  schemas/
  assets/templates/
  scripts/

assets/readme/
  *.png

evals/
  evals.json
  fixtures/
  semantic-candidates/

scripts/
  install.ps1
  install.sh
  package_skill.py
```

## Development

Validate the skill:

```bash
python C:/Users/Administrator/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/session-to-loop
```

Run transcript evals:

```bash
python evals/run_evals.py --keep-going
```

Run goal-design evals:

```bash
python evals/run_goal_design_evals.py --keep-going
```

Run a representative fixture:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input evals/fixtures/auxiliary-project-evidence.jsonl \
  --out-root .session-to-loop/tmp/auxiliary \
  --approve \
  --rule-fallback
```

## Design References

SixLoops follows the common skill pattern used by modern agent platforms: keep the skill folder self-contained, put the trigger and workflow in `SKILL.md`, keep heavy references/scripts bundled, and make installation copyable.

Useful references:

- [OpenAI Codex Skills](https://developers.openai.com/codex/skills)
- [Claude Code Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Anthropic public skills](https://github.com/anthropics/skills)
- [Claude Cookbooks skills guide](https://github.com/anthropics/claude-cookbooks/blob/main/skills/README.md)
- [Dimillian Skills](https://github.com/Dimillian/Skills)
- [onmyway133 Super Skills](https://github.com/onmyway133/skills)
- [awesome-claude-skills](https://github.com/ComposioHQ/awesome-claude-skills)
