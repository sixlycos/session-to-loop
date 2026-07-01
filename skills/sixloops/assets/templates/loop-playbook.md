# SixLoops Start Plans

{{summary}}

## Start Here

{{proposal_overview}}

## Default Reply

{{default_next_step}}

## How To Use

- The `start ...`, `shrink ...`, and `reject ...` strings are one-line replies in this chat, not terminal commands.
- After a start reply, the agent reads/updates the state file and runs until `DONE`, review-needed, `BLOCKED`, or `BUDGET_STOPPED` without step-by-step prompting.
- Each card contains the first-cycle steps, verifier, exit contract, and explicit return points; `claude-loops/<id>.md` is the handoff file for another agent.

## Candidate Summaries

{{loop_proposals}}

## Details And Smaller Options

These are useful when you choose not to launch one of the loop proposals yet.

### Rules and Memory Candidates

{{rules_and_memory}}

### Skill Candidates

{{skill_candidates}}

### Hook Candidates

{{hook_candidates}}

### Checklist or Approval Gates

{{approval_gates}}

### Rejected Candidates

{{rejected_candidates}}

## Decision Index

| Candidate | Mechanism | Decision | Confidence |
| --- | --- | --- | --- |
{{decision_index}}

Loop candidates:

{{loop_candidates}}

## Run Notes

Project: `{{project}}`

Analysis window: `{{analysis_window}}`

Input sources: `{{transcript_source_summary}}`

Redaction: `{{redaction_status}}`

Source limitations:

{{source_limitations}}

## Private Outputs

- {{private_output}}

## Shareable Outputs

- {{shareable_output}}
