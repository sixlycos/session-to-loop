# Scoring Rubric

Score only after the host model has extracted concrete evidence and written a candidate. This rubric
reviews model-authored candidates; it must not generate candidates, replace semantic judgment, or
turn keyword hits into loops. Prefer conservative recommendations when evidence is thin.

## Weighted Score

```text
Loop Score =
  25% frequency
+ 20% pain
+ 20% verifiability
+ 15% reversibility / execution authority
+ 10% artifactability
+ 10% project-person fit
```

## Dimensions

Work shape:

- Process-shaped: steps and order are known, results are predictable. Prefer script, hook, or traditional automation.
- Tool-assisted: the human still chooses direction often. Prefer skill, checklist, or decision packet.
- Goal-driven: the agent can choose next actions inside clear boundaries and objective checks. Consider a managed loop.

Frequency:

- High: appears across three or more sessions or task episodes.
- Medium: appears twice with clear similarity.
- Low: appears once.
- For `loop`, require evidence that the work is likely to recur weekly or within a repeated engineering cadence. If recurrence is unclear, keep it as `draft`, `skill`, or `checklist`.
- Project auxiliary evidence may count as repeated only when it has multiple observable records in the same bounded engineering workflow; keep confidence at `medium` until the user confirms fit.

Pain:

- High: caused failed completion, repeated user rescue, long wait cycles, broken CI, or production risk.
- Medium: caused extra clarification or reruns.
- Low: minor preference or style correction.

Verifiability:

- High: has deterministic commands, logs, status checks, screenshots, or assertions.
- Medium: can be checked with a human-readable checklist.
- Low: mostly subjective.
- A managed loop needs an objective rejection signal. A model-only reviewer can support the gate, but it should not be the only reason a loop is allowed to continue.

Reversibility / execution authority:

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
- Add weight when the agent can run the code it changes and inspect fresh failure evidence. Subtract weight when the environment is read-only, missing dependencies, or cannot reproduce the failure.
- Add weight when maker/checker separation is available for nontrivial changes. Do not count self-review as a strong verifier.

Project-person fit:

- High: specific to this user's repeated workflow or this repo's recurring constraints.
- Medium: useful but generic.
- Low: generic advice with little local evidence.

## Decision Bands

- `commit`: strong evidence, reversible mechanism, clear artifact.
- `draft`: good evidence but needs user review or implementation.
- `rule-only`: stable instruction, not a loop.
- `checklist-only`: useful but not deterministic or inspectable enough to automate.
- `needs-human`: high-impact or ambiguous decision point.
- `reject`: one-off, unverifiable, irreversible without approval, or too costly to automate.

## Hard Shrinks

- If it appears only once, do not recommend a loop.
- If the work is not likely to recur weekly or on a repeated project cadence, do not recommend scheduled automation.
- If it is process-shaped with no meaningful agent decision, recommend script or hook instead of loop.
- If it is tool-assisted and still needs frequent human direction, recommend skill, checklist, or decision packet before loop.
- If it appears only in project auxiliary evidence, keep the result as `draft` and explain that it is weaker than repeated user transcript evidence.
- If there is no observable feedback signal, do not recommend a loop.
- If the only verifier is the same agent's judgment, do not recommend a managed loop.
- If the agent cannot run or inspect the changed system, require read-only or draft level until a reproduction path exists.
- If it lacks state persistence, resume policy, verification, hard iteration cap, or stop conditions, do not recommend a loop.
- If it is only a stable preference, recommend a rule or memory.
- If it involves architecture rewrites, auth, payments, credentials, security-sensitive flows, irreversible action, dependency changes, migrations, deploys, or production-impacting action, require human approval and usually recommend `needs-human` or `approval-gate` first.
- If evidence contains secrets, redact and lower confidence if evidence cannot be cited without leaking private material.
- If transcript evidence conflicts with current project files, mark the finding stale until reverified.

## Cost Cadence

Frequency drives cost more than wording. Prefer `goal` or `event` heartbeats before scheduled runs. A daily loop with a maker/checker pair can be cheap; the same loop every few minutes can become expensive without improving accepted output.

Judge cost by accepted-result cost, not by attempts. If fewer than half of outputs survive human review, shrink the scope, improve the verifier, reduce cadence, or turn the loop into a skill/checklist.
