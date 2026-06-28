# Token Budget Policy

Use this reference before analyzing broad transcript sets.

## Budget Order

1. Discover files by metadata and JSONL shape.
2. Ask one scope question when needed.
3. Redact and normalize line by line.
4. Build compact analysis packets.
5. Let the host AI semantically group packets.
6. Apply deterministic guardrails.
7. Render only the top useful proposals first.

## What Not To Load

- Do not load full transcript directories into context.
- Do not read assistant reasoning as primary evidence.
- Do not load all available skills just because a loop might use them.
- Do not scan the user's home directory or whole disk by default.

## Packet Compression

Prefer small packets containing:

- provider
- source_type
- event_kind
- role
- tool_name
- source pointer
- short redacted text
- hash

Use source pointers only when snippets are not approved.

## Packet Selection

For broad transcript sets, do not send every allowed packet to the host AI. Use the packet selector:

- Prefer user correction, risk boundary, approval, and verification requests.
- Keep tool failures, command status, browser screenshots, CI logs, and assertion summaries as supporting evidence.
- Treat assistant packets as weak context unless explicitly scoped.
- Record kept and dropped counts in `analysis-packets-index.json`.
- Keep source pointers and `text_hash` so a narrow evidence window can be recovered later.

Use `--max-packets`, `--target-token-budget`, and `--role-quota role=count` when the packet file would be too large for economical semantic review.

Selection should be anchored on user semantics first. User messages reveal repeated corrections,
approval boundaries, validation habits, and risk language. Tool packets should usually enter as
small evidence windows around those anchors: first failure, final verifier, representative repeated
command, browser/screenshot status, CI status, or assertion summary.

For multilingual logs, preserve correction and risk language in the original user language. Important
Chinese cues include `不要`, `别`, `确认`, `批准`, `上线`, `生产`, `迁移`, `删除`, `截图`, `浏览器`, `测试`,
`报错`, `失败`, and `我来测`.

Prefer a two-stage semantic review for large logs:

1. Candidate pass: send compact user/tool packets and source pointers only.
2. Narrow evidence pass: recover small windows only for the top candidates before final rendering.

Do not let verbose CI logs, stack traces, browser snapshots, or soak-test output become primary
evidence by volume. Compress tool evidence into command, tool name, status, error class, counts, and
one exemplar whenever possible.

## Candidate Limits

For user-facing output, keep:

- 1-3 loop proposals.
- 1-3 smaller mechanism suggestions.
- Rejected items summarized only when they explain the recommendation.
- A hard iteration cap for every loop proposal.

For implementation, generate concrete artifacts only for user-confirmed candidates.

## Skill Loading

Load a related skill only when:

- the candidate domain is clear,
- the user confirmed adoption or asked for implementation, or
- the current task requires that skill to verify a recommendation.
