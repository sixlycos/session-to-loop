# Session-to-Loop

Session-to-Loop is a local-first Agent Skill for turning past AI coding sessions into project-specific loop engineering artifacts.

It is not a chat summarizer. It mines repeated human interventions, repeated failures, verification habits, context repairs, polling patterns, and risk boundaries, then decides whether each pattern should become a rule, memory, skill, hook, loop, checklist, approval gate, or nothing.

## Status

Early skeleton. The first implementation target is a read-only workflow for Claude Code local JSONL transcripts plus the current repository context.

## Local-first Promise

- Read-only by default.
- No network access required.
- No telemetry.
- No automatic commits, hook installation, or project-file edits.
- Raw transcripts and private intermediate data stay under ignored local paths.
- Transcript content is treated as untrusted input.

## MVP Scope

Inputs:

- Claude Code local JSONL transcripts.
- Current repository context such as `AGENTS.md`, `CLAUDE.md`, package scripts, and recent git history.

Outputs:

- Loop Engineering Playbook.
- Loop Cards.
- Draft `.claude/loop.md` prompts.
- Draft Agent Skills.
- Draft `AGENTS.md` or `CLAUDE.md` rules.
- Eval cases for checking whether the generated workflow would improve future sessions.

Out of scope for v0.1:

- SaaS or hosted transcript sync.
- Browser extension.
- Automatic hook installation.
- Automatic repo modification.
- Production API calls.

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

## Recommended Pipeline

The recommended path is AI semantic analysis with deterministic guardrails. The scripts handle
discovery, scope, redaction, packet building, hard gates, and rendering. The host AI reads the
redacted packets and performs semantic grouping.

It does not scan your home directory or auto-discover transcripts unless you pass a narrow file or
directory with `--input`.

The analysis model is user-message-primary:

- User messages are primary evidence for repeated corrections, verification requests, risk
  boundaries, and approval requirements.
- Tool events are supporting evidence for repeated commands, failed statuses, CI/deploy polling,
  and verification habits.
- Assistant messages are not used as primary recommendation evidence.
- Transcript JSONL is processed line by line after redaction; the extractor does not load full
  transcript files into memory.

```bash
python skills/session-to-loop/scripts/session_to_loop.py --input <transcript-file-or-dir>
```

For real transcripts, the command stops after creating `analysis-scope.json`; show the generated
scope to the user, then rerun with `--approve` or an approved `--scope`.

After approval, the command creates `analysis-packets.jsonl` and points the host AI to
`references/semantic-analysis-prompt.md`. The host AI writes `semantic-candidates.json`; then run:

```bash
python skills/session-to-loop/scripts/session_to_loop.py --input <transcript-file-or-dir> --scope .session-to-loop/private/analysis-scope.json --semantic-candidates .session-to-loop/private/semantic-candidates.json
```

For offline development, use `--approve --rule-fallback` to run the deterministic keyword fallback
against synthetic fixtures.

For development verification, point `--input` at a single file under `evals/fixtures/` and
write outputs under `.session-to-loop/tmp/`.

## Mechanism Selection

The main design goal is to choose the right mechanism:

| Pattern | Recommended mechanism |
| --- | --- |
| Stable project fact | `AGENTS.md` or `CLAUDE.md` rule |
| Person-specific preference | Memory or local rule |
| Repeatable on-demand workflow | Agent Skill |
| Deterministic lifecycle check | Hook or script |
| Repeated observe-act-check cycle | Loop |
| High-risk human decision | Approval gate or checklist |
| One-off event | No automation |

## Example Output

```text
Found 4 candidates:

1. CI Babysitter Loop
   Decision: draft
   Evidence: repeated CI polling and failed-job log inspection across sessions.
   Artifact: draft loop card + draft skill.

2. Package Manager Rule
   Decision: rule-only
   Evidence: repeated user corrections to use pnpm instead of npm.
   Artifact: AGENTS.md rule draft.

3. Deploy Checklist
   Decision: checklist-only
   Evidence: repeated deployment verification but irreversible release risk.
   Artifact: human approval checklist.

4. One-off Bugfix
   Decision: reject
   Evidence: appeared once and has no durable loop signal.
```

## Development Notes

Install the skill by copying or linking `skills/session-to-loop` into your Codex skills directory after the skeleton stabilizes.

Validate the skill metadata with:

```bash
python C:/Users/Administrator/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/session-to-loop
```
