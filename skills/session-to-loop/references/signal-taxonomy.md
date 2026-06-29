# Signal Taxonomy

Use this taxonomy to classify evidence from AI coding sessions. Count recurrence across separate task episodes or sessions whenever possible.

## Repeated Human Intervention

Signals:

- The user repeatedly corrects agent behavior.
- The user restates a project rule the agent should have known.
- The user asks the agent to stop, narrow scope, inspect first, or avoid a risky action.

Likely mechanism:

- Stable project instruction: rule.
- Person-specific preference: memory.
- Safety boundary: approval gate.

## Repeated Failure

Signals:

- Similar error appears across multiple sessions.
- The agent tries the same failed fix pattern.
- The same file, command, dependency, or environment setup causes repeated trouble.

Likely mechanism:

- Debug playbook: skill.
- Pre-action warning: rule or checklist.
- Deterministic guard: hook if a command can catch it.

## Repeated Verification

Signals:

- The same command is required before completion.
- The user asks for screenshots, local build, lint, test, CI status, health checks, or logs.
- The agent often claims completion before verification.

Likely mechanism:

- Deterministic lifecycle command: hook.
- On-demand verification workflow: skill.
- Repeated external status check with state, resume policy, and stop conditions: loop.

## Project Auxiliary Evidence

Signals:

- Browser audits, screenshots, snapshots, i18n checks, soak tests, eval outputs, CI logs, or result files show repeated observe-decide-act-verify work.
- The evidence is project-specific but not a complete Codex or Claude transcript.
- The loop shape is concrete enough to define trigger, inputs, cycle steps, verification, stop conditions, start mode, and review boundary.

Likely mechanism:

- Draft loop when the cycle is reversible, bounded, and verifiable.
- Skill when the workflow is on-demand but does not need state or resume behavior.
- Checklist or approval gate when the evidence includes release, production, migration, credentials, billing, or product judgment.

## Repeated Context Repair

Signals:

- The user repeatedly explains project structure, package manager, environment variables, test accounts, deployment flow, or branch policy.
- The agent re-discovers the same project facts in multiple sessions.

Likely mechanism:

- Project fact: `AGENTS.md` or `CLAUDE.md` rule.
- Long detailed domain knowledge: reference file inside a skill.

## Repeated Polling or Waiting

Signals:

- CI, deploys, reviews, logs, queues, or monitors require wait-check-act cycles.
- The agent repeatedly checks status, reads new failures, fixes, and checks again.

Likely mechanism:

- Loop when the cycle is reversible, can run after one approval, records state, resumes cleanly, verifies outcomes, and has clear stop conditions.
- Checklist when the cycle includes irreversible decisions.

## Repeated Human Decision

Signals:

- The agent must ask before merging, deploying, deleting, migrating, changing permissions, upgrading dependencies, or touching production.
- The user repeatedly rejects autonomous action in these areas.

Likely mechanism:

- Approval gate.
- Checklist.
- Rule stating the boundary.

## One-off Event

Signals:

- The pattern appears once.
- The evidence is tied to a unique incident.
- No reusable trigger or verification signal exists.

Likely mechanism:

- No automation.
- Mention only as context if it explains a current recommendation.
