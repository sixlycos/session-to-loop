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
