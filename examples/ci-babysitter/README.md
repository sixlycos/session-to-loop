# CI Babysitter

This example shows the full path from repeated CI triage friction to a startable loop.

## Story

| Stage | What happens |
| --- | --- |
| **Before** | The user keeps reminding the agent to read failed CI logs before guessing. |
| **SixLoops output** | A CI Babysitter Start Plan with state, verifier, iteration cap, and push/merge review boundary. |
| **After** | The next agent can run the CI triage cycle without repeated prompting, then stop with `DONE`, review-needed, `BLOCKED`, or `BUDGET_STOPPED`. |

## Before

The user keeps repeating:

- "CI is red again."
- "Read the failed job log before guessing."
- "Patch only the evidenced failure."
- "Do not push before local verification."

## SixLoops Output

SixLoops turns that repeated correction into **CI Babysitter Loop**:

- **Mechanism**: `loop, skill`
- **Start mode**: `low-risk edit`
- **Internal level**: `goal-loop`
- **Can delegate**: `yes`
- **Verifier**: focused project checks / CI status
- **State file**: `.session-to-loop/state/ci-babysitter.json`
- **Review boundary**: push, merge
- **Stop condition**: CI green, same failure repeats twice, or push/merge is required

## After

The next agent should:

1. Read the previous CI state.
2. Inspect current CI status, failed logs, and diff.
3. Pick at most 1-3 actionable failures.
4. Patch only direct, low-risk evidence.
5. Run the focused verifier.
6. Update state and return an exit status.

It should not finalize push/merge in low-risk edit mode, keep guessing after repeated failure, or continue when verifier evidence is stale.

## Why This Is A Loop

This is not just a rule because the work needs repeated observe-decide-act-verify cycles with durable state. It is not autonomous landing because push and merge require a stronger user-approved mode or review.

## Files

- [loop-playbook.md](loop-playbook.md): user-facing proposal summary.
- [cards/ci-babysitter.md](cards/ci-babysitter.md): Start Plan and Run Card.
- [ci-babysitter-loop.md](ci-babysitter-loop.md): managed loop prompt.
- [ci-babysitter-skill.md](ci-babysitter-skill.md): draft on-demand skill.
- [adoption/GOAL.md](adoption/GOAL.md): reusable run packet.
- [adoption/STATE.json](adoption/STATE.json): resume ledger.
- [adoption/HANDOFF.md](adoption/HANDOFF.md): how to run or resume.
- [adoption/AGENTS-snippet.md](adoption/AGENTS-snippet.md): draft project rule.

## Try This Case

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input evals/fixtures/repeated-ci-failure.jsonl \
  --out-root .session-to-loop/tmp/repeated-ci \
  --approve
```

Then let the host AI write `semantic-candidates.json`, or use the deterministic semantic fixture:

```bash
python skills/session-to-loop/scripts/session_to_loop.py \
  --input evals/fixtures/repeated-ci-failure.jsonl \
  --out-root .session-to-loop/tmp/repeated-ci \
  --scope .session-to-loop/tmp/repeated-ci/private/analysis-scope.json \
  --semantic-candidates evals/semantic-candidates/repeated-ci-failure.json
```
