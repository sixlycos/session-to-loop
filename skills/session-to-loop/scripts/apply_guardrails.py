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

from loop_contract import normalize_exit_contract, validate_exit_contract


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


def integer(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_state_schema(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    return {
        "items": "Tracked work items with status: inbox, active, blocked, done.",
        "attempts": "Attempt log with action, verification result, and timestamp.",
        "failures": "Failure signatures, repeat count, and blocker reason.",
        "next_cursor": "Where the next run should resume.",
        "human_decisions": "Approvals, rejections, or decisions that changed the loop boundary.",
    }


def reject_conditions_from(stop_conditions: list[str]) -> list[str]:
    success_terms = ("green", "pass", "passes", "passed", "done", "complete", "completed", "succeed", "success")
    rejected = [item for item in stop_conditions if not any(term in item.lower() for term in success_terms)]
    return rejected or stop_conditions


def normalize_completion_contract(source: dict, verification: list[str], stop_conditions: list[str]) -> dict:
    raw = source.get("completion_contract") if isinstance(source.get("completion_contract"), dict) else {}
    return {
        "success_criteria": strings(raw.get("success_criteria")) or verification,
        "verifier_commands": strings(raw.get("verifier_commands"))
        or ["Run the focused project checks listed in the verification section."],
        "evaluator_agent": str(
            raw.get("evaluator_agent")
            or "Use deterministic checks first; use a read-only checker when commands cannot decide."
        ),
        "pass_evidence_required": strings(raw.get("pass_evidence_required"))
        or ["Command output, status check, screenshot, schema result, or explicit verifier note."],
        "reject_conditions": strings(raw.get("reject_conditions")) or reject_conditions_from(stop_conditions),
        "no_progress_policy": str(
            raw.get("no_progress_policy")
            or "Stop when the same failure repeats twice, no files or evidence change across two iterations, or the iteration cap is reached."
        ),
    }


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
        "Decide at most 1-3 high-value items by impact, confidence, reversibility, and verifier availability.",
        "Run only bounded actions supported by the evidence.",
        "Verify the result and record state for the next run.",
    ]
    objective = str(source.get("objective") or summary)
    state_file = str(source.get("state_file") or f".session-to-loop/state/{candidate_id}.json")
    completion_contract = normalize_completion_contract(source, verification, stop_conditions)
    max_items = positive_int(source.get("max_items_per_cycle"), 3)
    max_iterations = positive_int(source.get("max_iterations_per_run"), 8)
    safety = raw.get("safety") if isinstance(raw.get("safety"), dict) else {}
    approval_boundary = strings(safety.get("requires_approval_for")) or strings(safety.get("human_checkpoint"))
    return {
        "objective": objective,
        "heartbeat": str(source.get("heartbeat") or raw.get("heartbeat") or "goal"),
        "recommended_maturity": str(
            source.get("recommended_maturity")
            or raw.get("recommended_maturity")
            or "goal-loop"
        ),
        "cadence_or_trigger": strings(source.get("cadence_or_trigger")) or trigger,
        "discovery_sources": strings(source.get("discovery_sources")) or inputs or trigger,
        "state_file": state_file,
        "state_schema": normalize_state_schema(source.get("state_schema")),
        "cycle_steps": strings(source.get("cycle_steps")) or default_cycle,
        "selection_policy": strings(source.get("selection_policy"))
        or ["Select at most 1-3 items that are high impact, evidenced, and reversible."],
        "max_items_per_cycle": max_items,
        "max_iterations_per_run": max_iterations,
        "completion_contract": completion_contract,
        "loop_exit_contract": normalize_exit_contract(
            source.get("loop_exit_contract"),
            success_criteria=completion_contract.get("success_criteria"),
            reject_conditions=completion_contract.get("reject_conditions") or stop_conditions,
            approval_boundary=approval_boundary,
            max_items=max_items,
            max_iterations=max_iterations,
        ),
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
        "promotion_criteria": strings(source.get("promotion_criteria"))
        or ["Promote only after repeated runs pass verification and human review accepts the output."],
        "demotion_criteria": strings(source.get("demotion_criteria"))
        or ["Demote when outputs are rejected, verification is inconclusive, cost grows, or human judgment is repeatedly required."],
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
                "provider": str(item.get("provider", "unknown")),
                "event_kind": str(item.get("event_kind", "unknown")),
                "source_type": str(item.get("source_type", "unknown")),
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


def is_project_context_evidence(item: dict) -> bool:
    return (
        item.get("provider") == "auxiliary"
        or item.get("source_type") == "auxiliary-evidence"
        or item.get("kind") == "project-auxiliary-evidence"
        or item.get("event_kind") == "auxiliary_evidence"
    )


def project_context_event_count(evidence: list[dict]) -> int:
    return sum(1 for item in evidence if is_project_context_evidence(item))


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
        "score": integer(raw.get("score"), 70),
        "pre_gate_score": integer(raw.get("score"), 70),
        "work_shape": str(raw.get("work_shape") or ("goal-driven" if "loop" in mechanisms else "tool-assisted")),
        "loop_archetype": str(raw.get("loop_archetype") or ("engineering-maintenance" if "loop" in mechanisms else "none")),
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
            "human_checkpoint": [
                str(item)
                for item in as_list(raw.get("safety", {}).get("human_checkpoint") if isinstance(raw.get("safety"), dict) else [])
            ],
            "budget_caps": [
                str(item)
                for item in as_list(raw.get("safety", {}).get("budget_caps") if isinstance(raw.get("safety"), dict) else [])
            ],
        },
        "artifacts": [str(item) for item in as_list(raw.get("artifacts"))],
        "downgrade_notes": str(raw.get("downgrade_notes", "")),
    }


def loop_eligibility(candidate: dict) -> dict:
    mechanisms = candidate.get("mechanisms", [])
    evidence = candidate.get("evidence", [])
    counts = role_counts(evidence)
    project_context_count = project_context_event_count(evidence)
    managed_loop = candidate.get("managed_loop", {})
    completion_contract = managed_loop.get("completion_contract", {})
    safety = candidate.get("safety", {})
    exit_contract = managed_loop.get("loop_exit_contract", {})
    exit_validation = validate_exit_contract(exit_contract)
    risky = any(
        word in " ".join(candidate.get("mechanisms", []) + candidate.get("trigger", []) + candidate.get("actions", [])).lower()
        for word in ("deploy", "production", "migration", "delete", "permission", "payment")
    )
    criteria = {
        "requested_loop_mechanism": "loop" in mechanisms,
        "recurs_across_sessions": user_session_count(evidence) >= 2 or session_count(evidence) >= 2 or project_context_count >= 2,
        "has_user_primary_evidence": counts.get("user", 0) > 0,
        "has_project_context_evidence": project_context_count > 0,
        "has_primary_or_project_evidence": counts.get("user", 0) > 0 or project_context_count > 0,
        "has_observable_state": bool(candidate.get("inputs") or counts.get("tool", 0) > 0),
        "has_repeatable_action": bool(candidate.get("actions")),
        "has_verification_signal": bool(candidate.get("verification")),
        "has_stop_conditions": bool(candidate.get("stop_conditions")),
        "has_safety_gate": bool(candidate.get("safety", {}).get("requires_approval_for")) or not risky,
        "has_state_file": bool(managed_loop.get("state_file")),
        "has_state_schema": bool(managed_loop.get("state_schema")),
        "has_discovery_sources": bool(managed_loop.get("discovery_sources") or managed_loop.get("cadence_or_trigger")),
        "has_cycle_steps": len(managed_loop.get("cycle_steps", [])) >= 3,
        "has_selection_policy": bool(managed_loop.get("selection_policy")),
        "has_iteration_cap": positive_int(managed_loop.get("max_iterations_per_run"), 0) > 0,
        "has_completion_contract": bool(
            completion_contract.get("success_criteria")
            and completion_contract.get("reject_conditions")
            and completion_contract.get("evaluator_agent")
            and completion_contract.get("no_progress_policy")
        ),
        "has_change_policy": bool(managed_loop.get("change_policy")),
        "has_resume_policy": bool(managed_loop.get("resume_policy")),
        "has_failure_policy": bool(managed_loop.get("failure_policy")),
        "has_human_checkpoint": bool(safety.get("human_checkpoint") or safety.get("requires_approval_for")),
        "has_budget_cap": bool(safety.get("budget_caps") or managed_loop.get("max_iterations_per_run")),
        "has_loop_exit_contract": exit_validation["valid"],
        "has_all_exit_statuses": not exit_validation["missing_statuses"],
        "has_continue_gate": bool(exit_contract.get("continue_only_if")),
        "has_budget_stop": bool(exit_contract.get("budget_stopped_when")),
        "exit_contract_bound_to_verifier": bool(
            completion_contract.get("success_criteria") and exit_contract.get("done_when")
        ),
        "exit_contract_bound_to_human_gate": bool(
            (safety.get("human_checkpoint") or safety.get("requires_approval_for"))
            and exit_contract.get("needs_human_when")
        ),
    }
    missing = [
        key
        for key, value in criteria.items()
        if not value and key not in {"has_user_primary_evidence", "has_project_context_evidence"}
    ]
    return {"eligible": not missing, "criteria": criteria, "missing": missing}


def decision_card(candidate: dict, mechanisms: list[str], loop_gate: dict) -> dict:
    decision = candidate.get("decision", "draft")
    verification = candidate.get("verification", [])
    if decision == "reject":
        can_use_now = "no"
        next_action = "reject"
    elif decision in {"rule-only", "checklist-only", "needs-human"}:
        can_use_now = "limited"
        next_action = "shrink"
    else:
        can_use_now = "limited" if decision == "draft" else "yes"
        next_action = "adopt"
    return {
        "can_use_now": can_use_now,
        "can_confirm": "yes" if verification else "no",
        "can_delegate": "yes" if "loop" in mechanisms and loop_gate.get("eligible") else "no",
        "missing_before_delegate": loop_gate.get("missing", []),
        "next_action": next_action,
    }


def apply_gates(candidate: dict) -> dict:
    downgrades = []
    loop_gate = loop_eligibility(candidate)
    mechanisms = list(candidate.get("mechanisms", []))
    project_context_count = project_context_event_count(candidate.get("evidence", []))

    if "loop" in mechanisms and candidate.get("work_shape") == "process-shaped":
        mechanisms = [item for item in mechanisms if item != "loop"]
        downgrades.append("Removed loop mechanism because process-shaped work should use a script or hook before a managed loop.")

    if "loop" in mechanisms and not loop_gate["eligible"]:
        mechanisms = [item for item in mechanisms if item != "loop"]
        downgrades.append("Removed loop mechanism because the managed loop acceptance contract was incomplete.")

    if (
        session_count(candidate.get("evidence", [])) < 2
        and project_context_count < 2
        and not {"checklist", "approval-gate"}.intersection(mechanisms)
    ):
        mechanisms = []
        candidate["decision"] = "reject"
        candidate["confidence"] = "low"
        candidate["score"] = min(candidate.get("score", 70), 49)
        candidate["artifacts"] = []
        downgrades.append("Rejected because evidence appears in fewer than two sessions.")
    elif project_context_count >= 2 and user_session_count(candidate.get("evidence", [])) == 0:
        candidate["decision"] = "draft" if candidate["decision"] == "commit" else candidate["decision"]
        candidate["confidence"] = "medium" if candidate.get("confidence") == "high" else candidate.get("confidence", "medium")
        downgrades.append(
            "Kept as draft because repeated project auxiliary evidence can justify a loop proposal, but it is weaker than repeated user transcript evidence."
        )

    if {"approval-gate"}.intersection(mechanisms) and candidate["decision"] == "commit":
        candidate["decision"] = "needs-human"
        downgrades.append("Changed commit to needs-human because an approval gate is required.")

    candidate["mechanisms"] = mechanisms
    candidate["mechanism"] = mechanisms[0] if mechanisms else "none"
    candidate["loop_eligibility"] = loop_gate
    candidate["decision_card"] = decision_card(candidate, mechanisms, loop_gate)
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
