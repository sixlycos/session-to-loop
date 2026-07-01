# SixLoops Architecture

This repository has two boundaries:

- The **publishable skill collection** under `skills/`.
- The **repository support layer** around it, which contains docs, examples,
  evals, packaging scripts, and local run output.

Keep the four installed skill directories stable: `sixloops`, `sixloops-mine`,
`sixloops-design`, and `sixloops-adopt`. Codex, Claude Code, install scripts,
release packaging, examples, and README commands all rely on that collection.

## Layer Map

```text
.
|-- README.md                     # Product overview, install, quick start
|-- SECURITY.md                   # Security policy
|-- docs/
|   `-- ARCHITECTURE.md           # Repository layering and placement rules
|-- skills/
|   |-- sixloops/          # Shared core plus router skill
|       |-- SKILL.md              # Host-agent operating contract
|       |-- agents/               # Host integration metadata
|       |-- references/           # Workflow references, rubrics, prompts, contracts
|       |-- schemas/              # Machine-readable handoff envelopes
|       |-- assets/templates/     # User-facing rendered artifact templates
|       `-- scripts/              # Public CLI entrypoints and Python package
|           |-- sixloops/
|           |   |-- core/          # Shared contracts, modes, transcript adapters
|           |   |-- pipeline/      # Transcript analysis pipeline stages
|           |   |-- goals/         # Direct goal design and adoption helpers
|           |   `-- paths.py       # Stable skill/package path constants
|           `-- *.py               # Documented command wrappers
|   |-- sixloops-mine/             # Log/session mining skill
|   |-- sixloops-design/           # Current-goal loop design skill
|   `-- sixloops-adopt/            # Candidate adoption/run skill
|-- evals/                        # Regression fixtures and deterministic eval runners
|   |-- fixtures/                 # Input transcript and evidence fixtures
|   |-- semantic-candidates/      # Host-AI candidate fixtures
|   |-- run_skill_collection_evals.py
|   |-- run_evals.py              # Transcript pipeline eval runner
|   `-- run_goal_design_evals.py  # Direct-goal design eval runner
|-- examples/                     # Checked-in example outputs and adoption packets
|-- scripts/                      # Repository install and release tooling
|-- assets/readme/                # README media
|-- dist/                         # Generated release archives, ignored
`-- .sixloops/             # Generated local run data, ignored
```

## Publishable Skill Collection

Everything required at runtime should live under the four installed skill
directories in `skills/`. The skill collection should not depend on `evals/`,
`examples/`, root-level `scripts/`, or generated `.sixloops/` contents.

Inside the collection:

- `sixloops/SKILL.md` is the router and shared host-agent contract.
- `sixloops-mine`, `sixloops-design`, and `sixloops-adopt` are narrow
  routeable skills with their own `SKILL.md`.
- `sixloops/references/` stores model-led workflow references, long-lived reasoning
  policy, routing rules, safety boundaries, scoring rubrics, and prompts.
- `sixloops/schemas/` stores machine-readable handoff envelopes and loop
  contract shapes. They are transport
  shapes for model-authored output, not the source of semantic decisions.
- `sixloops/assets/templates/` stores reusable rendered output shells.
- `sixloops/scripts/*.py` contains stable command wrappers for documented invocations.
- `sixloops/scripts/sixloops/core/` contains shared contracts, mode policy, and transcript
  adapters.
- `sixloops/scripts/sixloops/pipeline/` contains the transcript analysis stages.
- `sixloops/scripts/sixloops/goals/` contains direct goal-loop design and candidate
  adoption packet generation.
- `sixloops/agents/` contains integration metadata for host runtimes.

Python implementation modules in `skills/sixloops/scripts/sixloops/`
should import only the standard library and sibling `sixloops` modules unless
there is a deliberate, documented reason to cross the package boundary.

## Execution Flows

### Transcript Analysis

```text
sixloops.py
  -> discover_claude_sessions.py
  -> prepare_analysis_scope.py
  -> redact_transcripts.py
  -> build_analysis_packets.py
  -> host AI semantic review through the SixLoops skill prompt
  -> apply_guardrails.py       # safety downgrade only, not semantic rewriting
  -> render_artifacts.py
```

Main outputs:

- Private intermediates: `.sixloops/private/`
- Shareable rendered artifacts: `.sixloops/*/public/`
- Continue metadata: `.sixloops/*/private/analysis-run.json`

### Direct Goal Design

```text
design_goal_loop.py
  -> GOAL.md
  -> TEAM.md
  -> STATE.json
  -> HANDOFF.md
  -> AGENTS-snippet.md
  -> goal-loop-design.json
```

### Candidate Adoption

```text
adopt_candidate.py
  -> stateful run packet
  -> GOAL.md / STATE.json / HANDOFF.md / AGENTS-snippet.md
```

## Dependency Direction

Allowed dependency direction:

```text
README/docs
scripts/install + scripts/package
evals
examples
        -> skills/sixloops*

skills/sixloops-* -> skills/sixloops shared resources
skills/sixloops -> standard library + sibling script modules
```

Avoid reverse dependencies from the skill collection into repo support layers.
That keeps the installed skills portable after they are copied to
`~/.agents/skills/`, `~/.claude/skills/`, or a project skill directory.

## Change Placement

Use this table when adding or moving project material.

| Change type | Put it in |
| --- | --- |
| Router behavior, shared hard rules, start modes | `skills/sixloops/SKILL.md` |
| Narrow routeable mining/design/adoption behavior | `skills/sixloops-mine/`, `skills/sixloops-design/`, `skills/sixloops-adopt/` |
| Workflow references, durable policy, routing, safety model, semantic prompt, rubric | `skills/sixloops/references/` |
| JSON handoff envelope for model-authored output | `skills/sixloops/schemas/` |
| Stable documented command path | `skills/sixloops/scripts/*.py` wrapper |
| Shared contracts, modes, transcript adapters | `skills/sixloops/scripts/sixloops/core/` |
| Transcript discovery, redaction, packets, safety guardrails, rendering | `skills/sixloops/scripts/sixloops/pipeline/` |
| Direct goal design or candidate adoption packets | `skills/sixloops/scripts/sixloops/goals/` |
| Rendered markdown shells or localized artifact text | `skills/sixloops/assets/templates/` |
| Regression fixture inputs or expected semantic candidates | `evals/` |
| Checked-in demo output for users to inspect | `examples/` |
| Install, packaging, and release helper commands | `scripts/` |
| README screenshots or diagrams | `assets/readme/` |
| Raw logs, private packets, temp runs, generated eval output | `.sixloops/` |
| Release zips or other build products | `dist/` |

## Verification Map

Use the smallest relevant check for the layer changed:

```bash
python C:/Users/Administrator/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/sixloops
python evals/run_skill_collection_evals.py
python evals/run_evals.py --keep-going
python evals/run_goal_design_evals.py --keep-going
python scripts/package_skill.py
```

For docs-only edits, review links and command examples. For script or schema
edits, run the matching eval runner before release.
