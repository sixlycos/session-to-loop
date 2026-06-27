#!/usr/bin/env python3
"""Score extracted signals and select minimal loop-engineering mechanisms."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SIGNALS = Path(".session-to-loop/private/signals.json")
DEFAULT_OUT = Path(".session-to-loop/private/candidates.json")


PROFILES = {
    "ci-babysitter": {
        "summary": "Repeated CI failure triage: inspect status and logs, patch only actionable failures, then verify locally.",
        "mechanisms": ["loop", "skill"],
        "decision": "draft",
        "confidence": "high",
        "trigger": ["Open PR or branch has pending or failed CI."],
        "inputs": ["git diff", "CI status", "failed job logs", "relevant local test command"],
        "actions": [
            "Check CI status.",
            "Read the failed job log before guessing.",
            "Patch only the failing, evidenced issue.",
            "Run the relevant local verification.",
        ],
        "verification": ["Relevant local test passes.", "CI status becomes green or the remaining failure is clearly blocked."],
        "stop_conditions": ["CI is green.", "No actionable failure remains.", "The same failure repeats twice.", "A push or merge is required."],
        "managed_loop": {
            "objective": "Keep CI failures moving toward a verified fix without guessing.",
            "cadence_or_trigger": ["When CI is pending or failed on the current branch."],
            "state_file": ".session-to-loop/state/ci-babysitter.json",
            "cycle_steps": [
                "Read the previous state file if it exists.",
                "Inspect CI status, failed logs, and current git diff.",
                "Pick at most 1-3 actionable failures by impact and confidence.",
                "Attempt only low-risk local fixes with direct evidence.",
                "Run focused verification and record the result.",
            ],
            "selection_policy": ["Prefer failures blocking merge.", "Ignore flakes without new evidence."],
            "max_items_per_cycle": 3,
            "max_iterations_per_run": 8,
            "change_policy": "If a fix is low risk and directly evidenced, use an isolated branch or worktree when available. Do not push or merge without approval.",
            "deliverables": ["Status summary", "Patch or branch/PR draft when verification passes", "Updated state file"],
            "resume_policy": "On the next run, read the state file and continue unresolved failures before new ones.",
            "failure_policy": "If the same failure repeats twice or verification is inconclusive, record the blocker and stop.",
        },
        "requires_approval_for": ["push", "merge"],
        "artifacts": ["loop-card", "draft-skill", "eval-case"],
        "downgrade_notes": "Keep draft-only because push and merge require explicit approval.",
    },
    "package-manager-rule": {
        "summary": "Repeated user corrections say this project should use pnpm instead of npm.",
        "mechanisms": ["rule"],
        "decision": "rule-only",
        "confidence": "high",
        "trigger": ["Before installing dependencies or running package scripts."],
        "inputs": ["package.json", "lockfiles", "project instructions"],
        "actions": ["Use pnpm for package operations.", "Do not run npm install in this repository."],
        "verification": ["pnpm-lock.yaml or project instructions confirm pnpm usage."],
        "stop_conditions": ["The project explicitly changes package managers."],
        "requires_approval_for": ["package manager migration"],
        "artifacts": ["AGENTS.md rule draft"],
        "downgrade_notes": "This is a stable rule, not a loop.",
    },
    "deploy-approval-gate": {
        "summary": "Deployment and migration checks recur, but release and production actions require human approval.",
        "mechanisms": ["checklist", "approval-gate"],
        "decision": "needs-human",
        "confidence": "high",
        "trigger": ["Before production deploys, release notes approval, or database migrations."],
        "inputs": ["deployment status", "release notes", "migration plan", "rollback path"],
        "actions": ["Check deploy status.", "Prepare release and migration checklist.", "Ask for explicit approval before acting."],
        "verification": ["Human approval is recorded.", "Deployment status is observed without triggering a deploy."],
        "stop_conditions": ["Approval is missing.", "Rollback path is unclear.", "Production action would be triggered."],
        "requires_approval_for": ["production deploy", "database migration", "release approval"],
        "artifacts": ["approval checklist"],
        "downgrade_notes": "Hard downgrade from automation because production deploys and migrations are high-impact actions.",
    },
    "provider-acceptance-soak": {
        "summary": "Provider or channel changes need a bounded relay acceptance loop that separates transport success from schema, semantic assertion, and latency quality.",
        "mechanisms": ["loop", "skill"],
        "decision": "draft",
        "confidence": "medium",
        "trigger": ["Before adding or releasing a provider, channel, model alias, or relay behavior change."],
        "inputs": ["provider configuration", "relay request matrix", "HTTP status", "schema checks", "semantic assertions", "latency samples"],
        "actions": [
            "Run a small repeated relay suite against the changed provider path.",
            "Classify each result as transport, schema, model echo, semantic assertion, evaluator normalization, or latency.",
            "Pick at most 1-3 failures by release impact and reproducibility.",
            "Attempt only local, reversible fixes or record a provider limitation.",
        ],
        "verification": [
            "All required assertions pass or remaining failures are explicitly classified.",
            "Latency stays within the project threshold or is recorded as a release risk.",
        ],
        "stop_conditions": [
            "Acceptance suite passes.",
            "A provider limitation needs human product judgment.",
            "The same failure repeats after one focused fix attempt.",
            "Release or production routing approval is required.",
        ],
        "managed_loop": {
            "objective": "Keep provider acceptance work moving from raw request results to a verified release decision.",
            "cadence_or_trigger": ["Before provider, channel, model alias, or relay release candidates."],
            "state_file": ".session-to-loop/state/provider-acceptance-soak.json",
            "cycle_steps": [
                "Read the previous provider acceptance state file if it exists.",
                "Run or inspect the bounded relay acceptance result set.",
                "Bucket failures into transport, schema, model echo, semantic assertion, evaluator normalization, and latency.",
                "Pick at most 1-3 high-impact reproducible failures.",
                "Apply only low-risk local fixes, then rerun the focused acceptance check and record state.",
            ],
            "selection_policy": [
                "Prefer failures that block release or affect multiple model aliases.",
                "Do not spend cycles on provider behavior that needs product judgment.",
            ],
            "max_items_per_cycle": 3,
            "max_iterations_per_run": 8,
            "change_policy": "Local code or config fixes are allowed when reversible and directly evidenced. Do not change production routing, keys, billing, or provider contracts without approval.",
            "deliverables": ["Acceptance summary", "Classified failure list", "Patch or PR draft when verification passes", "Updated state file"],
            "resume_policy": "On the next run, continue unresolved provider failures from the state file before adding new checks.",
            "failure_policy": "Record the blocker and stop when failures need product judgment, provider escalation, or production approval.",
        },
        "requires_approval_for": ["production routing", "provider credential changes", "billing-impacting model changes"],
        "artifacts": ["loop-card", "draft-skill"],
        "downgrade_notes": "Draft because project auxiliary evidence is weaker than repeated user transcript evidence.",
    },
    "browser-audit-loop": {
        "summary": "Frontend route, copy, and i18n changes need a browser audit loop that verifies the real UI with scripted navigation and screenshots.",
        "mechanisms": ["loop", "skill"],
        "decision": "draft",
        "confidence": "medium",
        "trigger": ["After frontend route, UI copy, auth flow, or i18n changes."],
        "inputs": ["changed frontend files", "route list", "browser audit script", "screenshots or snapshots", "i18n check output"],
        "actions": [
            "Run the relevant i18n or static frontend check.",
            "Open the changed routes with a browser audit script.",
            "Capture screenshots or snapshots for the main states.",
            "Pick at most 1-3 visible regressions by user impact.",
        ],
        "verification": [
            "Target routes render without blocking errors.",
            "Screenshots or snapshots confirm the main user path.",
            "i18n checks pass or missing copy is explicitly listed.",
        ],
        "stop_conditions": [
            "Changed routes pass the audit.",
            "Authentication, data, or product judgment blocks verification.",
            "A visual fix requires design approval.",
        ],
        "managed_loop": {
            "objective": "Catch frontend route, copy, and i18n regressions before handoff.",
            "cadence_or_trigger": ["After frontend, routing, copy, auth UI, or i18n changes."],
            "state_file": ".session-to-loop/state/browser-audit-loop.json",
            "cycle_steps": [
                "Read the previous browser audit state file if it exists.",
                "Identify changed routes and the smallest meaningful route set.",
                "Run i18n/static checks, then navigate target routes in a browser.",
                "Capture screenshots or snapshots and select at most 1-3 visible regressions.",
                "Apply low-risk local fixes, rerun the focused audit, and record state.",
            ],
            "selection_policy": [
                "Prefer broken primary flows over cosmetic issues.",
                "Prefer regressions confirmed by screenshot, snapshot, or console output.",
            ],
            "max_items_per_cycle": 3,
            "max_iterations_per_run": 8,
            "change_policy": "Only make local UI fixes that are reversible and verified. Ask before changing product copy, navigation structure, or visual direction.",
            "deliverables": ["Audit summary", "Screenshots or snapshot pointers", "Patch or PR draft when verification passes", "Updated state file"],
            "resume_policy": "On the next run, continue unresolved route failures from the state file before expanding coverage.",
            "failure_policy": "Record the blocker and stop when auth, data, or design judgment is required.",
        },
        "requires_approval_for": ["visual direction changes", "product copy decisions", "auth or data fixture changes"],
        "artifacts": ["loop-card", "draft-skill"],
        "downgrade_notes": "Draft because project auxiliary evidence is weaker than repeated user transcript evidence.",
    },
    "transcript-redaction-boundary": {
        "summary": "Transcript evidence included secret-like material and must stay redacted in shareable outputs.",
        "mechanisms": ["checklist"],
        "decision": "checklist-only",
        "confidence": "medium",
        "trigger": ["Before quoting transcript evidence in any shareable artifact."],
        "inputs": ["redacted transcript snippets", "redaction summary"],
        "actions": ["Cite short redacted snippets only.", "Keep raw transcripts under private ignored paths."],
        "verification": ["Shareable outputs contain redaction markers instead of secret values."],
        "stop_conditions": ["Evidence cannot be safely redacted.", "A secret appears in rendered output."],
        "requires_approval_for": ["sharing raw transcript evidence"],
        "artifacts": ["privacy checklist"],
        "downgrade_notes": "Use as a safety checklist; do not infer a broader workflow from one secret-bearing session.",
    },
    "one-off-bugfix": {
        "summary": "Single small bugfix with no durable repeated intervention, verification loop, or automation trigger.",
        "mechanisms": [],
        "decision": "reject",
        "confidence": "high",
        "trigger": ["No reusable trigger detected."],
        "inputs": ["single task request"],
        "actions": ["Do not automate."],
        "verification": ["Pattern appears once."],
        "stop_conditions": ["A repeated pattern appears in future sessions."],
        "requires_approval_for": [],
        "artifacts": [],
        "downgrade_notes": "Rejected by one-off hard downgrade.",
    },
}


SCORE_VALUES = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.25,
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def level_frequency(session_count: int) -> str:
    if session_count >= 3:
        return "high"
    if session_count == 2:
        return "medium"
    return "low"


def dimension_levels(signal: dict, profile: dict) -> dict:
    signal_id = signal["id"]
    if signal_id == "one-off-bugfix":
        return {
            "frequency": "low",
            "pain": "low",
            "verifiability": "low",
            "safety_reversibility": "high",
            "artifactability": "low",
            "project_person_fit": "low",
        }
    if signal_id == "deploy-approval-gate":
        return {
            "frequency": level_frequency(signal["session_count"]),
            "pain": "high",
            "verifiability": "medium",
            "safety_reversibility": "low",
            "artifactability": "medium",
            "project_person_fit": "high",
        }
    if signal_id == "package-manager-rule":
        return {
            "frequency": level_frequency(signal["session_count"]),
            "pain": "medium",
            "verifiability": "high",
            "safety_reversibility": "high",
            "artifactability": "high",
            "project_person_fit": "high",
        }
    if signal_id == "transcript-redaction-boundary":
        return {
            "frequency": level_frequency(signal["session_count"]),
            "pain": "high",
            "verifiability": "medium",
            "safety_reversibility": "high",
            "artifactability": "medium",
            "project_person_fit": "high",
        }
    return {
        "frequency": level_frequency(signal["session_count"]),
        "pain": "high",
        "verifiability": "high",
        "safety_reversibility": "medium",
        "artifactability": "high",
        "project_person_fit": "high",
    }


def weighted_score(levels: dict) -> int:
    weights = {
        "frequency": 0.25,
        "pain": 0.20,
        "verifiability": 0.20,
        "safety_reversibility": 0.15,
        "artifactability": 0.10,
        "project_person_fit": 0.10,
    }
    score = 0.0
    for key, weight in weights.items():
        score += SCORE_VALUES[levels[key]] * weight
    return round(score * 100)


def loop_eligibility(signal: dict, mechanisms: list[str], profile: dict) -> dict:
    terms = set(signal.get("terms", []))
    role_counts = signal.get("role_counts", {})
    provider_counts = signal.get("provider_counts", {})
    candidate_id = signal["id"]
    managed_loop = profile.get("managed_loop", {})
    has_project_context_evidence = provider_counts.get("auxiliary", 0) > 0
    criteria = {
        "requested_loop_mechanism": "loop" in mechanisms,
        "recurs_across_sessions": signal.get("session_count", 0) >= 2
        or (has_project_context_evidence and signal.get("event_count", 0) >= 2),
        "has_user_primary_evidence": role_counts.get("user", 0) > 0,
        "has_project_context_evidence": has_project_context_evidence,
        "has_primary_or_project_evidence": role_counts.get("user", 0) > 0 or has_project_context_evidence,
        "has_observable_state": bool(
            role_counts.get("tool", 0) > 0
            or terms.intersection({"ci", "failed job", "failed log", "verify locally", "local test"})
        ),
        "has_repeatable_action": bool(profile.get("actions")),
        "has_verification_signal": bool(profile.get("verification")),
        "has_stop_conditions": bool(profile.get("stop_conditions")),
        "has_safety_gate": bool(profile.get("requires_approval_for")) or candidate_id not in {"deploy-approval-gate"},
        "has_state_file": bool(managed_loop.get("state_file")),
        "has_cycle_steps": len(managed_loop.get("cycle_steps", [])) >= 3,
        "has_selection_policy": bool(managed_loop.get("selection_policy")),
        "has_iteration_cap": bool(managed_loop.get("max_iterations_per_run")),
        "has_change_policy": bool(managed_loop.get("change_policy")),
        "has_resume_policy": bool(managed_loop.get("resume_policy")),
        "has_failure_policy": bool(managed_loop.get("failure_policy")),
    }
    required_keys = [
        "requested_loop_mechanism",
        "recurs_across_sessions",
        "has_primary_or_project_evidence",
        "has_observable_state",
        "has_repeatable_action",
        "has_verification_signal",
        "has_stop_conditions",
        "has_safety_gate",
        "has_state_file",
        "has_cycle_steps",
        "has_selection_policy",
        "has_iteration_cap",
        "has_change_policy",
        "has_resume_policy",
        "has_failure_policy",
    ]
    missing = [key for key in required_keys if not criteria[key]]
    return {
        "eligible": not missing,
        "criteria": criteria,
        "missing": missing,
    }


def apply_hard_downgrades(signal: dict, profile: dict, mechanisms: list[str], loop_gate: dict) -> tuple[str, str, list[str], list[str], list[str]]:
    decision = profile["decision"]
    confidence = profile["confidence"]
    artifacts = list(profile["artifacts"])
    downgrades: list[str] = []
    auxiliary_context = signal.get("provider_counts", {}).get("auxiliary", 0) > 0

    if "loop" in mechanisms and not loop_gate["eligible"]:
        mechanisms = [mechanism for mechanism in mechanisms if mechanism != "loop"]
        downgrades.append("Removed loop mechanism because managed goal loop eligibility criteria were not met.")

    if signal.get("session_count", 0) < 2 and signal["id"] != "transcript-redaction-boundary":
        if auxiliary_context and signal["id"] in {"provider-acceptance-soak", "browser-audit-loop"} and signal.get("event_count", 0) >= 2:
            decision = "draft"
            confidence = "medium"
            downgrades.append(
                "Kept as draft because repeated project auxiliary evidence can justify a loop proposal, but it is weaker than repeated user transcript evidence."
            )
        else:
            mechanisms = []
            decision = "reject"
            confidence = "low"
            artifacts = []
            downgrades.append("Rejected because the pattern appears in fewer than two user-centered sessions.")

    if signal["id"] == "deploy-approval-gate" and "loop" in mechanisms:
        mechanisms = [mechanism for mechanism in mechanisms if mechanism != "loop"]
        decision = "needs-human"
        downgrades.append("Removed loop mechanism because production deployment and migration decisions require human approval.")

    return decision, confidence, mechanisms, artifacts, downgrades


def decision_trace(signal: dict, mechanisms: list[str], downgrades: list[str]) -> dict:
    role_counts = signal.get("role_counts", {})
    primary_role = signal.get("primary_role", "unknown")
    return {
        "analysis_basis": "user messages are primary evidence; tool events are supporting evidence; assistant messages are not used as primary recommendation evidence.",
        "primary_role": primary_role,
        "role_counts": role_counts,
        "user_session_count": len(signal.get("user_sessions", [])),
        "tool_session_count": len(signal.get("tool_sessions", [])),
        "event_count": signal.get("event_count", 0),
        "intents": signal.get("intents", []),
        "provider_counts": signal.get("provider_counts", {}),
        "source_type_counts": signal.get("source_type_counts", {}),
        "selected_mechanisms": mechanisms,
        "downgrades": downgrades,
    }


def score_signal(signal: dict) -> dict:
    profile = PROFILES.get(signal["id"], PROFILES["one-off-bugfix"])
    levels = dimension_levels(signal, profile)
    pre_gate_score = weighted_score(levels)
    mechanisms = list(profile["mechanisms"])
    loop_gate = loop_eligibility(signal, mechanisms, profile)
    decision, confidence, mechanisms, artifacts, downgrades = apply_hard_downgrades(
        signal, profile, mechanisms, loop_gate
    )
    score = min(pre_gate_score, 49) if decision == "reject" else pre_gate_score
    evidence = signal.get("evidence", [])
    downgrade_notes = profile["downgrade_notes"]
    if downgrades:
        downgrade_notes = f"{downgrade_notes} {' '.join(downgrades)}"
    return {
        "id": signal["id"],
        "name": signal.get("name", profile.get("name", signal["id"])),
        "decision": decision,
        "confidence": confidence,
        "mechanism": mechanisms[0] if mechanisms else "none",
        "mechanisms": mechanisms,
        "score": score,
        "pre_gate_score": pre_gate_score,
        "score_dimensions": levels,
        "summary": profile["summary"],
        "evidence": [
            {
                "source": item["source"],
                "kind": item.get("kind", signal["signal_kind"]),
                "role": item.get("role", "unknown"),
                "provider": item.get("provider", "unknown"),
                "event_kind": item.get("event_kind", "unknown"),
                "source_type": item.get("source_type", "unknown"),
                "intent": item.get("intent", "unknown"),
                "snippet": item["snippet"],
            }
            for item in evidence
        ],
        "trigger": profile["trigger"],
        "inputs": profile["inputs"],
        "actions": profile["actions"],
        "verification": profile["verification"],
        "stop_conditions": profile["stop_conditions"],
        "managed_loop": profile.get("managed_loop", {}),
        "safety": {
            "autonomy_level": "draft-only" if decision != "reject" else "none",
            "requires_approval_for": profile["requires_approval_for"],
        },
        "artifacts": artifacts,
        "loop_eligibility": loop_gate,
        "decision_trace": decision_trace(signal, mechanisms, downgrades),
        "downgrade_notes": downgrade_notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score loop-engineering candidates from extracted signals.")
    parser.add_argument("--signals", default=str(DEFAULT_SIGNALS), help=f"Signals JSON path. Default: {DEFAULT_SIGNALS}")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"Candidates output path. Default: {DEFAULT_OUT}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    signals = json.loads(Path(args.signals).read_text(encoding="utf-8"))
    candidates = [score_signal(signal) for signal in signals.get("signals", [])]
    candidates.sort(key=lambda item: (-item["score"], item["id"]))
    output = {
        "version": 1,
        "created_at": now_iso(),
        "analysis_model": signals.get("analysis_model"),
        "scope_policy": signals.get("scope_policy"),
        "source": signals.get("source", {}),
        "redaction": signals.get("redaction", {}),
        "candidates": candidates,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Scored {len(candidates)} candidate(s): {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"score_candidates.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
