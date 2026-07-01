"""Shared Loop Exit Contract helpers."""

from __future__ import annotations

from typing import Any


ALLOWED_EXIT_STATUSES = ["CONTINUE", "DONE", "NEEDS_HUMAN", "BLOCKED", "BUDGET_STOPPED"]

STATUS_PROTOCOL = {
    "CONTINUE": "Only when another cycle can increase verified certainty.",
    "DONE": "Acceptance checks passed with required evidence; return for acceptance.",
    "NEEDS_HUMAN": "Return to the user only after evidence, options, impact, and regression path are packaged, or explicit approval is required.",
    "BLOCKED": "Reliable progress is not possible with current evidence or verifier.",
    "BUDGET_STOPPED": "Item, iteration, time, token, or cost cap was reached.",
}

REQUIRED_CONTRACT_KEYS = {
    "continue_only_if",
    "done_when",
    "needs_human_when",
    "blocked_when",
    "budget_stopped_when",
    "status_protocol",
}


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def strings(value: Any) -> list[str]:
    return [str(item) for item in as_list(value) if str(item).strip()]


def positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def merge_missing(primary: list[str], required: list[str]) -> list[str]:
    result = list(primary)
    seen = set(primary)
    result.extend(item for item in required if item not in seen)
    return result


def build_exit_contract(
    success_criteria: list[str] | None = None,
    reject_conditions: list[str] | None = None,
    approval_boundary: list[str] | None = None,
    max_items: int = 3,
    max_iterations: int = 8,
) -> dict:
    success = strings(success_criteria) or ["Acceptance checks pass with required evidence."]
    blocked = strings(reject_conditions) or [
        "Same failure repeats twice.",
        "No evidence changes across two iterations.",
        "Verifier is unavailable or ambiguous.",
    ]
    approvals = strings(approval_boundary)
    human = [
        f"Approval required for {item} after options, impact, and regression evidence are recorded."
        for item in approvals
    ] or ["Human decision required after the decision packet includes options, impact, regression path, and recommendation."]
    max_items = positive_int(max_items, 3)
    max_iterations = positive_int(max_iterations, 8)
    return {
        "continue_only_if": [
            "Objective is unchanged.",
            "Next action stays inside approved scope.",
            "A verifier can reject bad output.",
            "The Change Map can be updated or the next action can produce evidence for it.",
            "New evidence changed or is likely from the next verifier.",
            "Risk stays below the approved mode and explicit return points.",
            "The last cycle changed evidence, narrowed scope, reduced failures, or clarified the blocker.",
            f"Fewer than {max_items} item(s) are active in this cycle.",
            f"Fewer than {max_iterations} iteration(s) have run.",
        ],
        "done_when": success,
        "needs_human_when": human,
        "blocked_when": blocked,
        "budget_stopped_when": [
            f"More than {max_items} item(s) would be required in one cycle.",
            f"{max_iterations} iteration(s) are reached.",
            "Token, time, cost, or tool budget is reached.",
        ],
        "status_protocol": dict(STATUS_PROTOCOL),
    }


def normalize_exit_contract(
    raw: Any,
    success_criteria: list[str] | None = None,
    reject_conditions: list[str] | None = None,
    approval_boundary: list[str] | None = None,
    max_items: int = 3,
    max_iterations: int = 8,
) -> dict:
    fallback = build_exit_contract(
        success_criteria=success_criteria,
        reject_conditions=reject_conditions,
        approval_boundary=approval_boundary,
        max_items=max_items,
        max_iterations=max_iterations,
    )
    if not isinstance(raw, dict):
        return fallback

    normalized = dict(fallback)
    for key in REQUIRED_CONTRACT_KEYS - {"status_protocol"}:
        values = strings(raw.get(key))
        if values:
            normalized[key] = merge_missing(values, fallback[key]) if key == "continue_only_if" else values

    raw_protocol = raw.get("status_protocol") if isinstance(raw.get("status_protocol"), dict) else {}
    protocol = dict(STATUS_PROTOCOL)
    for status in ALLOWED_EXIT_STATUSES:
        if raw_protocol.get(status):
            protocol[status] = str(raw_protocol[status])
    normalized["status_protocol"] = protocol
    return normalized


def validate_exit_contract(contract: Any) -> dict:
    missing: list[str] = []
    if not isinstance(contract, dict):
        return {
            "valid": False,
            "missing": sorted(REQUIRED_CONTRACT_KEYS),
            "missing_statuses": list(ALLOWED_EXIT_STATUSES),
        }

    for key in REQUIRED_CONTRACT_KEYS:
        if key == "status_protocol":
            if not isinstance(contract.get(key), dict):
                missing.append(key)
        elif not strings(contract.get(key)):
            missing.append(key)

    statuses = set(contract.get("status_protocol", {})) if isinstance(contract.get("status_protocol"), dict) else set()
    missing_statuses = [status for status in ALLOWED_EXIT_STATUSES if status not in statuses]
    return {
        "valid": not missing and not missing_statuses,
        "missing": missing,
        "missing_statuses": missing_statuses,
    }
