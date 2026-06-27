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
managed_loop:
  objective: "Keep CI failures moving toward a verified fix without guessing."
  cadence_or_trigger:
    - "When CI is pending or failed on the current branch."
  state_file: ".session-to-loop/state/ci-babysitter.json"
  cycle_steps:
    - "Read the previous state file if it exists."
    - "Inspect CI status, failed logs, and current git diff."
    - "Pick at most 1-3 actionable failures by impact and confidence."
    - "Attempt only low-risk local fixes with direct evidence."
    - "Run focused verification and record the result."
  selection_policy:
    - "Prefer failures blocking merge."
    - "Ignore flakes without new evidence."
  max_items_per_cycle: 3
  change_policy: "If a fix is low risk and directly evidenced, use an isolated branch or worktree when available. Do not push or merge without approval."
  deliverables:
    - "Status summary"
    - "Patch or branch/PR draft when verification passes"
    - "Updated state file"
  resume_policy: "On the next run, read the state file and continue unresolved failures before new ones."
  failure_policy: "If the same failure repeats twice or verification is inconclusive, record the blocker and stop."
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
  providers:
    codex: 8
    claude: 4
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
    provider: "codex"
    source_type: "native-transcript"
    classification_confidence: "high"
    classification_reason: "matched Codex session_meta/response_item/event_msg shape"
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
provider: "codex"
event_kind: "message"
source_type: "native-transcript"
source_confidence: "high"
source: "session:synthetic-ci-1#event-1"
source_file: "evals/fixtures/repeated-ci-failure.jsonl"
session_id: "synthetic-ci-1"
role: "user"
tool_name: null
text: "CI is red again. Please inspect the failed job logs before guessing."
text_hash: "9b2f5c7e1d0a4b33"
text_truncated: false
redacted: true
structured:
  response_item:
    type: "message"
    role: "user"
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
    provider: "codex"
    event_kind: "message"
    source_type: "native-transcript"
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
managed_loop:
  objective: "Keep CI failures moving toward a verified fix without guessing."
  cadence_or_trigger:
    - "When CI is pending or failed."
  state_file: ".session-to-loop/state/ci-babysitter.json"
  cycle_steps:
    - "Read previous state."
    - "Inspect current CI and logs."
    - "Pick at most 1-3 high-value failures."
    - "Attempt low-risk fixes."
    - "Verify and record state."
  selection_policy:
    - "Prefer blockers with clear logs."
  max_items_per_cycle: 3
  change_policy: "If a fix is low risk and directly evidenced, use an isolated branch or worktree when available. Do not push or merge without approval."
  deliverables:
    - "Status summary"
    - "Draft PR or patch when verified"
    - "Updated state file"
  resume_policy: "Continue unresolved items from the state file before new work."
  failure_policy: "Record blocker and stop when verification fails twice or needs human judgment."
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
