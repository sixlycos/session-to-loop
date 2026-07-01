# Output Schemas

Use these structures when producing machine-readable artifacts. Markdown reports may use the same fields as headings.

## Loop Classification Fields

- `work_shape`: `process-shaped`, `tool-assisted`, or `goal-driven`.
- `loop_archetype`: short label such as `engineering-maintenance`, `frontend-verification`, `monitoring-research`, `document-batch`, or `delivery-governance`.
- `user_value`: one natural sentence that tells the project owner what repeated work this removes, what the agent will inspect or change, what comes back, and where it stops.
- `team_mode`: `none`, `phased`, or `subagent-team`.
- `managed_loop.heartbeat`: `session`, `goal`, `scheduled`, or `event`.
- `managed_loop.recommended_maturity`: `read-only`, `goal-loop`, `isolated-draft`, `verified-pr-draft`, `scheduled-readonly`, or `scheduled-draft`.
- `decision_card`: user-facing readiness summary: `can_use_now`, `can_confirm`, `can_delegate`, `missing_before_delegate`, `next_action`, and `confirmation_options`.
- User-facing mode names map onto internal maturity values through `scripts/sixloops/core/mode_policy.py`: `read-only` -> `read-only`, `low-risk edit` -> `goal-loop`, `worktree draft` -> `isolated-draft`, `PR draft` -> `verified-pr-draft`, `scheduled read-only` -> `scheduled-readonly`, and `scheduled draft` -> `scheduled-draft`.
- `schemas/semantic-candidates.schema.json`: handoff envelope for host-AI output. Scripts may validate shape, but they must not use the schema, regex fallback, or defaults as the primary loop-value judge.
- `raw_ai_claims`: private copy of the host AI candidate before deterministic guardrails normalize render fields.
- `normalized_render_fields`: fields defaulted only so draft artifacts can render; defaults do not make a loop delegable.
- `delegation_gate`: raw-AI-claims-only eligibility check for `can_delegate=yes`.
- `first_run_packet`: the confirmable starter contract: `recommended_action`, `reply_to_confirm`, `starter_goal_prompt`, `first_run_mode`, `state_file`, `observe`, `decide`, `act`, `verify`, `stop_after`, and `human_gate`.
- `change_map`: the product/technical transformation picture for goal-ready loops: `current_x`, `target_b`, `user_perception`, `transformation_thesis`, `affected_surfaces`, `regression_plan`, `rollback_or_compatibility`, `research_questions`, `waves`, and `decision_packet_required_when`.
- `managed_loop.completion_contract`: mandatory for real loops; defines success criteria, verifier commands, evaluator, pass evidence, reject conditions, and no-progress policy.
- `managed_loop.loop_exit_contract`: mandatory for goal-ready loops; defines when to continue, return done, ask a human, block, or stop by budget.
- `schemas/loop-exit-contract.schema.json`: machine-readable shape for the mandatory exit contract.
- `managed_loop.state_schema`: minimal durable state ledger the loop must update before stopping.
- `managed_loop.status_protocol`: allowed statuses: `DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, and `BUDGET_STOPPED`.
- `economics`: lightweight cost and acceptance estimate: trigger frequency, expected per-run cost, automatic rejection signals, human review load, demotion threshold, and budget caps.

## Loop Candidate

```yaml
id: "ci-babysitter"
name: "CI Babysitter Loop"
decision: "draft"
confidence: "high"
mechanism: "loop"
work_shape: "goal-driven"
loop_archetype: "engineering-maintenance"
summary: "Diagnose failed CI, propose minimal fixes, and stop when CI is green or blocked."
user_value: "When CI fails, it reads the failed job logs first, patches only the evidenced failure, runs the focused check, and returns before push or merge."
evidence:
  - source: "session:2026-06-10#episode-2"
    kind: "repeated-verification"
    snippet: "User asked agent to inspect failed CI logs."
first_run_packet:
  recommended_action: "start ci-babysitter as PR draft"
  reply_to_confirm: "start ci-babysitter as PR draft"
  first_run_mode: "PR draft"
  state_file: ".sixloops/state/ci-babysitter.json"
  stop_after: "8 iterations or the same failure repeats twice"
  human_gate: "Do not push, merge, deploy, migrate, or change credentials without approval."
  starter_goal_prompt: |
    Objective: Keep CI failures moving toward a verified fix without guessing.
    Acceptance checks:
    - Failed job logs are inspected before patching.
    - A focused verifier passes, or the blocker is recorded.
    First cycle:
    1. Observe CI status, failed logs, and current diff.
    2. Decide the next failure, action, verifier, and escalation path.
    3. Act on at most 1-3 directly evidenced failures.
    4. Verify with the focused project check.
    5. Update .sixloops/state/ci-babysitter.json before stopping.
    Stop after 8 iterations, two repeated failure signatures, or a return point.
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
  heartbeat: "goal"
  recommended_maturity: "verified-pr-draft"
  cadence_or_trigger:
    - "When CI is pending or failed on the current branch."
  discovery_sources:
    - "CI status"
    - "failed job logs"
    - "git diff"
  state_file: ".sixloops/state/ci-babysitter.json"
  state_schema:
    status: "One of pending, discovering, active, verifying, done, blocked, escalated, budget_stopped, rejected."
    objective_hash: "Stable hash of objective and success criteria."
    items: "Tracked CI failures with status: inbox, active, blocked, done."
    attempts: "Attempt log with action, verification result, and timestamp."
    failures: "Failure signatures, repeat count, and blocker reason."
    progress_metrics: "Observed progress such as failures reduced, checks passing, or unchanged evidence."
    next_cursor: "Where the next run should resume."
    human_decisions: "Approvals, rejections, or merge decisions."
  status_protocol:
    - "DONE: all success criteria pass with verifier evidence."
    - "CONTINUE: progress changed and budget remains."
    - "BLOCKED: same failure repeats twice or no progress across two iterations."
    - "NEEDS_HUMAN: approval, product judgment, or uncertain verifier is required."
    - "BUDGET_STOPPED: token, time, item, or iteration cap is reached."
  change_map:
    current_x: "What the project/user experiences today."
    target_b: "What should be true after the loop succeeds."
    user_perception: "How the user/operator will notice X became B."
    transformation_thesis: "The product or technical idea that turns X into B."
    affected_surfaces:
      - "product behavior"
      - "technical contracts"
      - "tests or verification"
    regression_plan:
      - "focused verifier command"
      - "manual smoke path when commands cannot decide"
    rollback_or_compatibility:
      - "compatibility wrapper or reversible worktree slice"
    research_questions:
      - "What evidence proves current X?"
      - "Which surfaces must change for target B?"
    waves:
      - "map evidence"
      - "draft first compatible slice"
      - "verify and update state"
    decision_packet_required_when:
      - "The next action changes product semantics or requires stronger approval."
  cycle_steps:
    - "Refresh the Change Map: current X, target B, affected surfaces, regression plan, and rollout waves."
    - "Read the previous state file if it exists."
    - "Inspect CI status, failed logs, and current git diff."
    - "Decide at most 1-3 actionable failures by impact, confidence, and risk."
    - "Attempt only low-risk local fixes with direct evidence."
    - "Run focused verification and record the result."
  selection_policy:
    - "Prefer failures blocking merge."
    - "Ignore flakes without new evidence."
  max_items_per_cycle: 3
  max_iterations_per_run: 8
  completion_contract:
    success_criteria:
      - "Relevant local test passes."
      - "CI status becomes green or remaining failure is clearly blocked."
    verifier_commands:
      - "Run the focused project checks listed in the verification section."
    evaluator_agent: "Use deterministic checks first; use a read-only checker when commands cannot decide."
    pass_evidence_required:
      - "Command output, CI status, or explicit verifier note."
    reject_conditions:
      - "Same failure repeats twice."
      - "Push or merge is required."
    no_progress_policy: "Stop when the same failure repeats twice or no evidence changes across two iterations."
  loop_exit_contract:
    continue_only_if:
      - "Objective is unchanged."
      - "Next action stays inside approved scope."
      - "A verifier can reject bad output."
      - "New evidence changed or is likely from the next verifier."
      - "Risk stays below the approved mode and explicit return points."
      - "Iteration and item budgets remain."
    done_when:
      - "Relevant local test passes."
      - "CI status becomes green or remaining failure is clearly blocked."
    needs_human_when:
      - "Push or merge is required."
      - "Product, release, security, data, cost, or architecture judgment is required."
    blocked_when:
      - "Same failure repeats twice."
      - "No evidence changes across two iterations."
      - "Verifier is unavailable or ambiguous."
    budget_stopped_when:
      - "Iteration, item, time, token, or cost cap is reached."
    status_protocol:
      CONTINUE: "Only when another cycle can increase verified certainty."
      DONE: "Acceptance checks passed with required evidence; return for acceptance."
      NEEDS_HUMAN: "Return to user because human judgment or explicit approval is required."
      BLOCKED: "Reliable progress is not possible with current evidence or verifier."
      BUDGET_STOPPED: "Item, iteration, time, token, or cost cap was reached."
  change_policy: "If a fix is low risk and directly evidenced, use an isolated branch or worktree when available. Do not push or merge without approval."
  deliverables:
    - "Status summary"
    - "Patch or branch/PR draft when verification passes"
    - "Updated state file"
  resume_policy: "On the next run, read the state file and continue unresolved failures before new ones."
  failure_policy: "If the same failure repeats twice or verification is inconclusive, record the blocker and stop."
  promotion_criteria:
    - "Promote only after repeated runs pass verification and human review accepts the output."
  demotion_criteria:
    - "Demote when outputs are rejected, verification is inconclusive, cost grows, or human judgment is repeatedly required."
safety:
  autonomy_level: "draft-only"
  requires_approval_for:
    - "push"
    - "merge"
    - "dependency upgrade"
    - "schema migration"
  human_checkpoint:
    - "Review patch or PR draft before push or merge."
  budget_caps:
    - "Stop after 8 iterations per run."
    - "Handle at most 3 items per cycle."
decision_card:
  can_use_now: "limited"
  can_confirm: "yes"
  can_delegate: "yes"
  missing_before_delegate: []
  next_action: "start"
  confirmation_options:
    - "start ci-babysitter as read-only"
    - "start ci-babysitter as low-risk edit"
    - "start ci-babysitter as worktree draft"
    - "start ci-babysitter as PR draft"
    - "shrink ci-babysitter to skill"
    - "reject ci-babysitter"
economics:
  expected_trigger_frequency: "medium"
  expected_per_run_cost: "medium"
  automatic_rejection_signals:
    - "focused test failure"
    - "CI status"
    - "same failure signature repeats"
  human_review_load: "medium"
  demote_if: "Fewer than half of reviewed outputs are accepted or verifier evidence is repeatedly inconclusive."
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
  - ".sixloops/private/signals.json"
shareable_outputs:
  - ".sixloops/public/loop-playbook.md"
```

## Analysis Scope

```yaml
version: 1
approved: true
approval_mode: "explicit-cli-flag"
scope_fingerprint: "7a15c5c5e1328a0b"
scope_lease:
  fingerprint: "7a15c5c5e1328a0b"
  reuse_until_inputs_change: true
  ask_again_when:
    - "allowed files change"
    - "allowed roles change"
    - "snippet policy changes"
    - "output visibility changes"
manifest: ".sixloops/private/discovered-sessions.json"
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
interaction_kind: "user_verification_request"
turn_index: 1
prev_packet_id: null
next_packet_id: "packet-000002"
text: "CI is red again. Please inspect the failed job logs before guessing."
text_hash: "9b2f5c7e1d0a4b33"
text_truncated: false
importance_score: 65
importance_reasons:
  - "user-primary"
  - "verification"
estimated_tokens: 18
selection_reason: "importance"
redacted: true
structured:
  response_item:
    type: "message"
    role: "user"
```

## Analysis Packets Index

```yaml
version: 1
analysis_model: "ai-semantic-packets-v1"
packet_count: 80
packet_selection:
  enabled: true
  input_count: 420
  kept_count: 80
  dropped_count: 340
  max_packets: 80
  target_token_budget: 12000
  role_quotas:
    user: 40
    tool: 20
  estimated_tokens: 11870
  dropped_estimated_tokens: 46100
  kept_by_role:
    user: 45
    tool: 35
  dropped_by_role:
    user: 120
    tool: 220
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
work_shape: "goal-driven"
loop_archetype: "engineering-maintenance"
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
first_run_packet:
  recommended_action: "start ci-babysitter as PR draft"
  reply_to_confirm: "start ci-babysitter as PR draft"
  first_run_mode: "PR draft"
  state_file: ".sixloops/state/ci-babysitter.json"
  stop_after: "8 iterations or two repeated failure signatures"
  human_gate: "Do not push, merge, deploy, migrate, or change credentials without approval."
  starter_goal_prompt: "Objective: Keep CI failures moving toward a verified fix without guessing..."
  observe: "Read previous state, current CI status, failed logs, and diff."
  decide: "Choose the next failure, verifier, and escalation path."
  act: "Attempt only low-risk fixes with direct evidence."
  verify: "Run the focused verifier and record evidence."
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
  heartbeat: "goal"
  recommended_maturity: "verified-pr-draft"
  cadence_or_trigger:
    - "When CI is pending or failed."
  discovery_sources:
    - "CI status"
    - "failed job logs"
  state_file: ".sixloops/state/ci-babysitter.json"
  state_schema:
    status: "Current loop status."
    objective_hash: "Stable hash of objective and success criteria."
    items: "Tracked CI failures with status."
    attempts: "Attempt log with action and verification result."
    progress_metrics: "Observed progress or repeated no-progress evidence."
    next_cursor: "Where the next run should resume."
  status_protocol:
    - "DONE"
    - "CONTINUE"
    - "BLOCKED"
    - "NEEDS_HUMAN"
    - "BUDGET_STOPPED"
  cycle_steps:
    - "Read previous state."
    - "Inspect current CI and logs."
    - "Decide at most 1-3 high-value failures and the verifier for each."
    - "Attempt low-risk fixes."
    - "Verify and record state."
  selection_policy:
    - "Prefer blockers with clear logs."
  max_items_per_cycle: 3
  max_iterations_per_run: 8
  completion_contract:
    success_criteria:
      - "Relevant local test passes."
    verifier_commands:
      - "Run the focused project checks listed in the verification section."
    evaluator_agent: "Use deterministic checks first; use a read-only checker when commands cannot decide."
    pass_evidence_required:
      - "Command output or explicit verifier note."
    reject_conditions:
      - "CI green."
      - "Same failure repeats twice."
    no_progress_policy: "Stop when the same failure repeats twice or no evidence changes across two iterations."
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
  human_checkpoint:
    - "Review patch or PR draft before push or merge."
  budget_caps:
    - "Stop after 8 iterations per run."
decision_card:
  can_use_now: "limited"
  can_confirm: "yes"
  can_delegate: "yes"
  missing_before_delegate: []
  next_action: "start"
  confirmation_options:
    - "start ci-babysitter as read-only"
    - "start ci-babysitter as low-risk edit"
    - "start ci-babysitter as worktree draft"
    - "start ci-babysitter as PR draft"
    - "shrink ci-babysitter to skill"
    - "reject ci-babysitter"
economics:
  expected_trigger_frequency: "medium"
  expected_per_run_cost: "medium"
  automatic_rejection_signals:
    - "test"
    - "CI status"
  human_review_load: "medium"
  demote_if: "Acceptance rate falls below 50% or verifier evidence stays weak."
artifacts:
  - "loop-card"
```

## Adoption Packet Manifest

Generated only after a user starts a candidate with a mode that needs durable state.

```yaml
version: 1
created_at: "2026-06-28T00:00:00+00:00"
candidate_id: "ci-babysitter"
candidate_name: "CI Babysitter Loop"
decision: "draft"
mechanisms:
  - "loop"
  - "skill"
adoption_level: "goal-loop"
source_candidates: ".sixloops/private/candidates.json"
source_analysis_model: "user-message-primary-tool-usage-supporting-v1"
files:
  state: ".sixloops/adopted/ci-babysitter/STATE.json"
  goal: ".sixloops/adopted/ci-babysitter/GOAL.md"
  handoff: ".sixloops/adopted/ci-babysitter/HANDOFF.md"
  agents_snippet: ".sixloops/adopted/ci-babysitter/AGENTS-snippet.md"
```

## Adoption State

```yaml
version: 1
loop_id: "ci-babysitter"
name: "CI Babysitter Loop"
status: "pending"
adoption_level: "goal-loop"
objective_hash: "0f9d4d8e3c2a5b71"
objective: "Keep CI failures moving toward a verified fix without guessing."
heartbeat: "goal"
success_criteria:
  - "Relevant local test passes."
reject_conditions:
  - "Same failure repeats twice."
loop_exit_contract:
  continue_only_if:
    - "Objective is unchanged."
    - "A verifier can reject bad output."
  done_when:
    - "Relevant local test passes."
  needs_human_when:
    - "Push or merge is required."
  blocked_when:
    - "Same failure repeats twice."
  budget_stopped_when:
    - "Iteration, item, time, token, or cost cap is reached."
  status_protocol:
    CONTINUE: "Only when another cycle can increase verified certainty."
    DONE: "Acceptance checks passed with required evidence; return for acceptance."
    NEEDS_HUMAN: "Return to user because human judgment or explicit approval is required."
    BLOCKED: "Reliable progress is not possible with current evidence or verifier."
    BUDGET_STOPPED: "Item, iteration, time, token, or cost cap was reached."
approval_boundary:
  - "push"
  - "merge"
items: []
attempts: []
failure_signatures: []
progress_metrics: []
human_queue: []
next_cursor: null
last_status: null
```

## Goal Loop Design

Generated when the user starts from a current objective instead of historical transcripts.

```yaml
version: 1
design_model: "goal-to-loop-v1"
loop_id: "frontend-after-route-changes-a1b2c3d4e5"
name: "Frontend Verification Loop"
goal: "After frontend changes, verify changed routes with browser screenshots."
domain: "frontend"
work_shape: "goal-driven"
loop_archetype: "frontend-verification"
adoption_level: "goal-loop"
team_mode: "subagent-team"
managed_loop:
  objective: "After frontend changes, verify changed routes with browser screenshots."
  heartbeat: "goal"
  recommended_maturity: "goal-loop"
  cadence_or_trigger:
    - "After route, layout, component, auth UI, i18n, or copy changes."
  discovery_sources:
    - "changed frontend files"
    - "route list"
    - "browser console"
    - "screenshots"
  state_file: "STATE.json"
  cycle_steps:
    - "Read prior state, current goal, changed UI files, and project instructions."
    - "Identify the smallest route/state set that proves the change."
    - "Choose at most 1-3 visible or user-path regressions."
    - "Apply only reversible UI fixes inside the approved scope."
    - "Run focused static checks and browser verification."
  max_items_per_cycle: 3
  max_iterations_per_run: 8
  completion_contract:
    success_criteria:
      - "Target routes render without blocking errors."
    verifier_commands:
      - "Run the focused project verifier identified during the Decide step."
    evaluator_agent: "Use deterministic checks first; use a reviewer or verifier role when commands cannot decide."
    pass_evidence_required:
      - "Command output, screenshot, CI status, review finding resolution, or explicit verifier note."
    reject_conditions:
      - "Same failure repeats twice."
      - "A return point is reached."
    no_progress_policy: "Stop when no evidence changes across two iterations."
  loop_exit_contract:
    continue_only_if:
      - "Objective is unchanged."
      - "Next action stays inside approved scope."
      - "A verifier can reject bad output."
      - "New evidence changed or is likely from the next verifier."
      - "Risk stays below the approved mode and explicit return points."
      - "Iteration and item budgets remain."
    done_when:
      - "Target routes render without blocking errors."
    needs_human_when:
      - "Visual direction changes are required."
      - "Product copy decisions are required."
    blocked_when:
      - "Same failure repeats twice."
      - "No evidence changes across two iterations."
      - "Verifier is unavailable or ambiguous."
    budget_stopped_when:
      - "Iteration, item, time, token, or cost cap is reached."
    status_protocol:
      CONTINUE: "Only when another cycle can increase verified certainty."
      DONE: "Acceptance checks passed with required evidence; return for acceptance."
      NEEDS_HUMAN: "Return to user because human judgment or explicit approval is required."
      BLOCKED: "Reliable progress is not possible with current evidence or verifier."
      BUDGET_STOPPED: "Item, iteration, time, token, or cost cap was reached."
subagent_team:
  mode: "subagent-team"
  activation_rule: "If subagent tools are available, use separate agents for planner/reviewer/verifier work; otherwise run roles sequentially."
  roles:
    - id: "planner"
      title: "Planner"
      may_modify_files: false
      outputs:
        - "finding summary"
        - "recommended next action"
    - id: "browser-verifier"
      title: "Browser Verifier"
      may_modify_files: false
      outputs:
        - "route list"
        - "screenshot or snapshot evidence"
safety:
  autonomy_level: "goal-loop"
  requires_approval_for:
    - "visual direction changes"
    - "product copy decisions"
  budget_caps:
    - "Handle at most 3 item(s) per cycle."
    - "Stop after 8 iteration(s) per run."
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
