#!/usr/bin/env python3
"""Apply deterministic hard gates to AI-generated semantic candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SEMANTIC = Path(".session-to-loop/private/semantic-candidates.json")
DEFAULT_PACKET_INDEX = Path(".session-to-loop/private/analysis-packets-index.json")
DEFAULT_OUT = Path(".session-to-loop/private/candidates.json")
VALID_DECISIONS = {"commit", "draft", "checklist-only", "rule-only", "needs-human", "reject"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    return text or "candidate"


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def strings(value: Any) -> list[str]:
    return [str(item) for item in as_list(value) if str(item)]


def positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def normalize_managed_loop(
    raw: dict,
    candidate_id: str,
    summary: str,
    trigger: list[str],
    inputs: list[str],
    actions: list[str],
    verification: list[str],
    stop_conditions: list[str],
) -> dict:
    source = raw.get("managed_loop") if isinstance(raw.get("managed_loop"), dict) else {}
    default_cycle = [
        "Read the previous state file if it exists.",
        "Inspect current inputs and observable status.",
        "Pick at most 1-3 high-value items by impact, confidence, and reversibility.",
        "Run only bounded actions supported by the evidence.",
        "Verify the result and record state for the next run.",
    ]
    objective = str(source.get("objective") or summary)
    state_file = str(source.get("state_file") or f".session-to-loop/state/{candidate_id}.json")
    return {
        "objective": objective,
        "cadence_or_trigger": strings(source.get("cadence_or_trigger")) or trigger,
        "state_file": state_file,
        "cycle_steps": strings(source.get("cycle_steps")) or default_cycle,
        "selection_policy": strings(source.get("selection_policy"))
        or ["Select at most 1-3 items that are high impact, evidenced, and reversible."],
        "max_items_per_cycle": positive_int(source.get("max_items_per_cycle"), 3),
        "change_policy": str(
            source.get("change_policy")
            or "Only make low-risk changes with direct evidence. Use an isolated branch or worktree when modifying files. Do not push, merge, deploy, or mutate production without approval."
        ),
        "deliverables": strings(source.get("deliverables"))
        or ["Status summary", "Patch, branch, or PR draft when verification passes", "Updated state file"],
        "resume_policy": str(
            source.get("resume_policy")
            or f"Read {state_file} first and continue unresolved items before starting new work."
        ),
        "failure_policy": str(
            source.get("failure_policy")
            or "Record the blocker and stop when verification fails, evidence is inconclusive, or human judgment is required."
        ),
    }


def source_session(source: str) -> str:
    return source.split("#", 1)[0].removeprefix("session:")


def normalize_evidence(candidate: dict) -> list[dict]:
    evidence = []
    for item in as_list(candidate.get("evidence")):
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "source": str(item.get("source", "unknown")),
                "kind": str(item.get("kind", "semantic-observation")),
                "role": str(item.get("role", "unknown")),
                "intent": str(item.get("intent", "semantic_inference")),
                "snippet": str(item.get("snippet", item.get("text", "No quote needed."))),
            }
        )
    return evidence


def session_count(evidence: list[dict]) -> int:
    sessions = {source_session(item["source"]) for item in evidence if item.get("source")}
    return len(sessions)


def user_session_count(evidence: list[dict]) -> int:
    sessions = {source_session(item["source"]) for item in evidence if item.get("role") == "user"}
    return len(sessions)


def role_counts(evidence: list[dict]) -> dict:
    counts = {"user": 0, "tool": 0, "assistant": 0, "unknown": 0}
    for item in evidence:
        role = item.get("role", "unknown")
        counts[role if role in counts else "unknown"] += 1
    return counts


def normalize_candidate(raw: dict) -> dict:
    name = str(raw.get("name") or raw.get("id") or "Candidate")
    mechanisms = [str(item) for item in as_list(raw.get("mechanisms") or raw.get("mechanism")) if str(item)]
    evidence = normalize_evidence(raw)
    decision = str(raw.get("decision", "draft"))
    if decision not in VALID_DECISIONS:
        decision = "draft"
    candidate_id = slug(str(raw.get("id") or name))
    summary = str(raw.get("summary", ""))
    trigger = strings(raw.get("trigger"))
    inputs = strings(raw.get("inputs"))
    actions = strings(raw.get("actions"))
    verification = strings(raw.get("verification"))
    stop_conditions = strings(raw.get("stop_conditions"))
    return {
        "id": candidate_id,
        "name": name,
        "decision": decision,
        "confidence": str(raw.get("confidence", "medium")),
        "mechanism": mechanisms[0] if mechanisms else "none",
        "mechanisms": mechanisms,
        "score": int(raw.get("score", 70)),
        "pre_gate_score": int(raw.get("score", 70)),
        "summary": summary,
        "evidence": evidence,
        "trigger": trigger,
        "inputs": inputs,
        "actions": actions,
        "verification": verification,
        "stop_conditions": stop_conditions,
        "managed_loop": normalize_managed_loop(raw, candidate_id, summary, trigger, inputs, actions, verification, stop_conditions),
        "safety": {
            "autonomy_level": str(raw.get("safety", {}).get("autonomy_level", "draft-only"))
            if isinstance(raw.get("safety"), dict)
            else "draft-only",
            "requires_approval_for": [
                str(item)
                for item in as_list(raw.get("safety", {}).get("requires_approval_for") if isinstance(raw.get("safety"), dict) else [])
            ],
        },
        "artifacts": [str(item) for item in as_list(raw.get("artifacts"))],
        "downgrade_notes": str(raw.get("downgrade_notes", "")),
    }


def loop_eligibility(candidate: dict) -> dict:
    mechanisms = candidate.get("mechanisms", [])
    evidence = candidate.get("evidence", [])
    counts = role_counts(evidence)
    managed_loop = candidate.get("managed_loop", {})
    risky = any(
        word in " ".join(candidate.get("mechanisms", []) + candidate.get("trigger", []) + candidate.get("actions", [])).lower()
        for word in ("deploy", "production", "migration", "delete", "permission", "payment")
    )
    criteria = {
        "requested_loop_mechanism": "loop" in mechanisms,
        "recurs_across_sessions": user_session_count(evidence) >= 2 or session_count(evidence) >= 2,
        "has_user_primary_evidence": counts.get("user", 0) > 0,
        "has_observable_state": bool(candidate.get("inputs") or counts.get("tool", 0) > 0),
        "has_repeatable_action": bool(candidate.get("actions")),
        "has_verification_signal": bool(candidate.get("verification")),
        "has_stop_conditions": bool(candidate.get("stop_conditions")),
        "has_safety_gate": bool(candidate.get("safety", {}).get("requires_approval_for")) or not risky,
        "has_state_file": bool(managed_loop.get("state_file")),
        "has_cycle_steps": len(managed_loop.get("cycle_steps", [])) >= 3,
        "has_selection_policy": bool(managed_loop.get("selection_policy")),
        "has_change_policy": bool(managed_loop.get("change_policy")),
        "has_resume_policy": bool(managed_loop.get("resume_policy")),
        "has_failure_policy": bool(managed_loop.get("failure_policy")),
    }
    missing = [key for key, value in criteria.items() if not value]
    return {"eligible": not missing, "criteria": criteria, "missing": missing}


def apply_gates(candidate: dict) -> dict:
    downgrades = []
    loop_gate = loop_eligibility(candidate)
    mechanisms = list(candidate.get("mechanisms", []))

    if "loop" in mechanisms and not loop_gate["eligible"]:
        mechanisms = [item for item in mechanisms if item != "loop"]
        downgrades.append("Removed loop mechanism because managed goal loop eligibility criteria were not met.")

    if session_count(candidate.get("evidence", [])) < 2 and not {"checklist", "approval-gate"}.intersection(mechanisms):
        mechanisms = []
        candidate["decision"] = "reject"
        candidate["confidence"] = "low"
        candidate["score"] = min(candidate.get("score", 70), 49)
        candidate["artifacts"] = []
        downgrades.append("Rejected because evidence appears in fewer than two sessions.")

    if {"approval-gate"}.intersection(mechanisms) and candidate["decision"] == "commit":
        candidate["decision"] = "needs-human"
        downgrades.append("Changed commit to needs-human because an approval gate is required.")

    candidate["mechanisms"] = mechanisms
    candidate["mechanism"] = mechanisms[0] if mechanisms else "none"
    candidate["loop_eligibility"] = loop_gate
    candidate["decision_trace"] = {
        "analysis_basis": "AI semantic candidate with deterministic scope, recurrence, loop, and safety gates applied.",
        "primary_role": "user" if role_counts(candidate.get("evidence", [])).get("user", 0) else "unknown",
        "role_counts": role_counts(candidate.get("evidence", [])),
        "user_session_count": user_session_count(candidate.get("evidence", [])),
        "tool_session_count": len({source_session(item["source"]) for item in candidate.get("evidence", []) if item.get("role") == "tool"}),
        "event_count": len(candidate.get("evidence", [])),
        "intents": sorted({item.get("intent", "semantic_inference") for item in candidate.get("evidence", [])}),
        "selected_mechanisms": mechanisms,
        "downgrades": downgrades,
    }
    if downgrades:
        candidate["downgrade_notes"] = (candidate.get("downgrade_notes", "") + " " + " ".join(downgrades)).strip()
    return candidate


def semantic_candidates(data: dict) -> list[dict]:
    if isinstance(data.get("candidates"), list):
        return data["candidates"]
    if isinstance(data.get("top_findings"), list):
        return data["top_findings"]
    raise ValueError("Semantic candidates JSON must contain a candidates array.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply deterministic hard gates to AI semantic candidates.")
    parser.add_argument("--semantic-candidates", default=str(DEFAULT_SEMANTIC), help=f"AI candidates JSON. Default: {DEFAULT_SEMANTIC}")
    parser.add_argument("--packet-index", default=str(DEFAULT_PACKET_INDEX), help=f"Packet index JSON. Default: {DEFAULT_PACKET_INDEX}")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"Guarded candidates output. Default: {DEFAULT_OUT}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    semantic = load_json(Path(args.semantic_candidates))
    packet_index = load_json(Path(args.packet_index))
    candidates = [apply_gates(normalize_candidate(item)) for item in semantic_candidates(semantic)]
    output = {
        "version": 1,
        "created_at": now_iso(),
        "analysis_model": "ai-semantic-with-deterministic-guardrails-v1",
        "scope_policy": packet_index.get("scope_policy", {}),
        "source": packet_index.get("source", {}),
        "redaction": packet_index.get("redaction", {}),
        "candidates": candidates,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Applied guardrails to {len(candidates)} semantic candidate(s): {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"apply_guardrails.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
