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
    candidate_id = signal["id"]
    criteria = {
        "requested_loop_mechanism": "loop" in mechanisms,
        "recurs_across_sessions": signal.get("session_count", 0) >= 2,
        "has_user_primary_evidence": role_counts.get("user", 0) > 0,
        "has_observable_state": bool(
            role_counts.get("tool", 0) > 0
            or terms.intersection({"ci", "failed job", "failed log", "verify locally", "local test"})
        ),
        "has_repeatable_action": bool(profile.get("actions")),
        "has_verification_signal": bool(profile.get("verification")),
        "has_stop_conditions": bool(profile.get("stop_conditions")),
        "has_safety_gate": bool(profile.get("requires_approval_for")) or candidate_id not in {"deploy-approval-gate"},
    }
    required_keys = [
        "requested_loop_mechanism",
        "recurs_across_sessions",
        "has_user_primary_evidence",
        "has_observable_state",
        "has_repeatable_action",
        "has_verification_signal",
        "has_stop_conditions",
        "has_safety_gate",
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

    if "loop" in mechanisms and not loop_gate["eligible"]:
        mechanisms = [mechanism for mechanism in mechanisms if mechanism != "loop"]
        downgrades.append("Removed loop mechanism because loop eligibility criteria were not met.")

    if signal.get("session_count", 0) < 2 and signal["id"] != "transcript-redaction-boundary":
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
