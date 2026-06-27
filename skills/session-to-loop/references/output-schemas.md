# Output Schemas

Use these structures when producing machine-readable artifacts. Markdown reports may use the same fields as headings.

## Loop Candidate

```yaml
id: "ci-babysitter"
name: "CI Babysitter Loop"
decision: "draft"
confidence: "high"
mechanism: "loop"
summary: "Diagnose failed CI, propose minimal fixes, and stop when CI is green or blocked."
evidence:
  - source: "session:2026-06-10#episode-2"
    kind: "repeated-verification"
    snippet: "User asked agent to inspect failed CI logs."
trigger:
  - "Open PR has pending or failed CI."
inputs:
  - "git diff"
  - "CI status"
  - "failed job logs"
actions:
  - "Check CI status."
  - "Fetch failed job logs."
  - "Identify likely failure."
  - "Make minimal fix only when local evidence is strong."
verification:
  - "Relevant local test passes."
  - "CI status becomes green."
stop_conditions:
  - "CI green."
  - "No actionable failure remains."
  - "Same failure repeats twice."
  - "Fix requires product or release decision."
safety:
  autonomy_level: "draft-only"
  requires_approval_for:
    - "push"
    - "merge"
    - "dependency upgrade"
    - "schema migration"
artifacts:
  - "loop-card"
  - "draft-skill"
  - "eval-case"
```

## Playbook Summary

```yaml
project: "example-repo"
analysis_window: "last-30-days"
source_summary:
  transcript_files: 12
  task_episodes: 34
  redaction: "enabled"
top_findings:
  - id: "ci-babysitter"
    decision: "draft"
    mechanism: "loop"
    confidence: "high"
rejected:
  - id: "one-off-bugfix"
    reason: "appeared once"
private_outputs:
  - ".session-to-loop/private/signals.json"
shareable_outputs:
  - ".session-to-loop/public/loop-playbook.md"
```

## Analysis Scope

```yaml
version: 1
approved: true
approval_mode: "explicit-cli-flag"
manifest: ".session-to-loop/private/discovered-sessions.json"
allowed_files:
  - path: "/absolute/path/to/session.jsonl"
    label: "session.jsonl"
    size_bytes: 12345
    mtime: "2026-06-27T00:00:00+00:00"
    format: "jsonl"
allowed_roles:
  - "user"
  - "tool"
allow_redacted_snippets: true
output_visibility: "private"
content_policy:
  read_transcript_body_after_approval: true
  raw_transcripts_stay_private: true
  assistant_messages_are_context_only: true
  tool_events_are_supporting_evidence: true
```

## Analysis Packet

```yaml
packet_id: "packet-000001"
packet_type: "transcript_event"
source: "session:synthetic-ci-1#event-1"
source_file: "evals/fixtures/repeated-ci-failure.jsonl"
session_id: "synthetic-ci-1"
role: "user"
tool_name: null
text: "CI is red again. Please inspect the failed job logs before guessing."
text_hash: "9b2f5c7e1d0a4b33"
text_truncated: false
redacted: true
```

## Semantic Candidate

```yaml
id: "ci-babysitter"
name: "CI Babysitter Loop"
decision: "draft"
confidence: "high"
mechanisms:
  - "loop"
  - "skill"
score: 90
summary: "Repeated user requests to inspect CI logs before patching."
evidence:
  - source: "session:synthetic-ci-1#event-1"
    kind: "verification-request"
    role: "user"
    intent: "inspect_failed_ci_before_guessing"
    snippet: "CI is red again..."
trigger:
  - "CI is pending or failed."
inputs:
  - "CI status"
  - "failed job logs"
actions:
  - "Check status."
verification:
  - "Relevant local test passes."
stop_conditions:
  - "CI green."
safety:
  autonomy_level: "draft-only"
  requires_approval_for:
    - "push"
    - "merge"
artifacts:
  - "loop-card"
```

## Eval Case

```yaml
id: "repeated-ci-failure"
input_fixture: "evals/fixtures/repeated-ci-failure.jsonl"
expected:
  include_mechanism:
    - "loop"
    - "skill"
  include_candidate:
    - "ci-babysitter"
  exclude_decision:
    - "commit-without-approval"
assertions:
  - "Evidence is redacted."
  - "Stop conditions are explicit."
  - "Push and merge require approval."
```
