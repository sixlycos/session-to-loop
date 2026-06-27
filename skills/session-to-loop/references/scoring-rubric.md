# Scoring Rubric

Score only after extracting concrete evidence. Prefer conservative recommendations when evidence is thin.

## Weighted Score

```text
Loop Score =
  25% frequency
+ 20% pain
+ 20% verifiability
+ 15% safety / reversibility
+ 10% artifactability
+ 10% project-person fit
```

## Dimensions

Work shape:

- Process-shaped: steps and order are known, results are predictable. Prefer script, hook, or traditional automation.
- Tool-assisted: the human still chooses direction often. Prefer skill, checklist, or approval gate.
- Goal-driven: the agent can choose next actions inside clear boundaries and objective checks. Consider a managed loop.

Frequency:

- High: appears across three or more sessions or task episodes.
- Medium: appears twice with clear similarity.
- Low: appears once.
- Project auxiliary evidence may count as repeated only when it has multiple observable records in the same bounded engineering workflow; keep confidence at `medium` until the user confirms fit.

Pain:

- High: caused failed completion, repeated user rescue, long wait cycles, broken CI, or production risk.
- Medium: caused extra clarification or reruns.
- Low: minor preference or style correction.

Verifiability:

- High: has deterministic commands, logs, status checks, screenshots, or assertions.
- Medium: can be checked with a human-readable checklist.
- Low: mostly subjective.

Safety / reversibility:

- High: local, reversible, no data mutation.
- Medium: changes code but can be reviewed before merge.
- Low: deploys, deletes, migrations, permissions, secrets, payments, or production calls.

Artifactability:

- High: can become a concrete rule, skill, hook, managed loop, eval, or script.
- Medium: can become a checklist or documented convention.
- Low: too vague to encode.

Loop closure:

- High: has objective, trigger or cadence, input discovery, prioritization, bounded actions, change policy, verification, state file, resume policy, failure policy, hard iteration cap, and stop conditions.
- Medium: has most cycle mechanics but needs user review before delegation.
- Low: repeats steps but cannot run unattended after initial approval.

Project-person fit:

- High: specific to this user's repeated workflow or this repo's recurring constraints.
- Medium: useful but generic.
- Low: generic advice with little local evidence.

## Decision Bands

- `commit`: strong evidence, safe mechanism, clear artifact.
- `draft`: good evidence but needs user review or implementation.
- `rule-only`: stable instruction, not a loop.
- `checklist-only`: useful but not safe or deterministic enough to automate.
- `needs-human`: high-impact or ambiguous decision boundary.
- `reject`: one-off, unverifiable, unsafe, or too costly to automate.

## Hard Downgrades

- If it appears only once, do not recommend a loop.
- If it is process-shaped with no meaningful agent decision, recommend script or hook instead of loop.
- If it is tool-assisted and still needs frequent human direction, recommend skill, checklist, or approval gate before loop.
- If it appears only in project auxiliary evidence, keep the result as `draft` and explain that it is weaker than repeated user transcript evidence.
- If there is no observable feedback signal, do not recommend a loop.
- If it lacks state persistence, resume policy, verification, hard iteration cap, or stop conditions, do not recommend a loop.
- If it is only a stable preference, recommend a rule or memory.
- If it involves irreversible or production-impacting action, require human approval.
- If evidence contains secrets, redact and lower confidence if evidence cannot be safely cited.
- If transcript evidence conflicts with current project files, mark the finding stale until reverified.

## Cost Cadence

Frequency drives cost more than wording. Prefer `goal` or `event` heartbeats before scheduled runs. A daily loop with a maker/checker pair can be cheap; the same loop every few minutes can become expensive without improving accepted output.
