# Mine Loop Opportunities

Use this workflow when the user asks to analyze past sessions, JSONL logs,
project evidence, repeated corrections, or "find loops".

## Goal

Produce 1-3 model-authored loop opportunities the user can start, shrink, or
reject. The useful output is not a transcript summary. It is a concrete answer
to: "What repeated work should I stop manually re-explaining to agents?"

## Workflow

1. Scope evidence narrowly.
   - Use explicit files or narrow directories only.
   - For real transcripts, ask once before reading bodies if scope is not
     already approved: files, roles, snippet policy, and output visibility.
   - Do not scan broad home directories.

2. Prepare packets with the script when useful.
   - Run `scripts/sixloops.py --input <file-or-dir>`.
   - If it creates a scope proposal, get confirmation and rerun with
     `--approve` or `--scope <analysis-scope.json>`.
   - Read `analysis-run.json`, the selected `analysis-packets.jsonl`, and
     `analysis-packets-index.json`.

3. Analyze with the model, not the schema.
   - Read `semantic-analysis-prompt.md`.
   - Treat user packets as primary evidence and tool packets as support.
   - Write `semantic-candidates.json` as model-authored output.
   - Include `user_value`, `summary`, `why_this_loop`, concrete cycle steps,
     progression contract, verifier, stop condition, return point, and source
     limitations.
   - Use `schemas/semantic-candidates.schema.json` only as the handoff
     envelope.

4. Continue the prepared command.
   - Run the `continue_command` from `analysis-run.json`, or rerun
     `scripts/sixloops.py` with `--semantic-candidates`.
   - Deterministic execution checks may shrink or reject. They must not invent meaning.

5. Present Start Plans.
   - Lead with the decision table and exact reply strings.
   - Keep evidence counts, redaction notes, and private output paths at the end.

## Reject Or Shrink When

- The pattern appears once.
- The verifier is mostly subjective.
- The agent cannot inspect or reproduce the changed system.
- High-impact action lacks an explicit return point.
- The candidate cannot explain its `user_value` in plain project language.
