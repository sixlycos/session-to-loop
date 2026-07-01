"""Shared loop progression contract helpers."""

from __future__ import annotations

from typing import Any


REQUIRED_PROGRESSION_KEYS = {
    "rhythm",
    "state_updates_required",
    "continue_requires",
    "stop_instead_of_continue_when",
    "handoff_rule",
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


def build_progression_contract(
    max_items: int = 3,
    max_iterations: int = 8,
    state_file: str = "STATE.json",
) -> dict:
    max_items = positive_int(max_items, 3)
    max_iterations = positive_int(max_iterations, 8)
    return {
        "rhythm": [
            f"Read `{state_file}`, the goal, the Change Map, and the verifier before choosing work.",
            "Turn prior blockers, repeated human corrections, or unfinished waves into candidate work before adding new work.",
            f"Choose at most {max_items} item(s) that can change evidence, narrow risk, or clarify a blocker.",
            "Act only on the selected item(s), then verify before choosing the next status.",
            "End by writing the state delta and the next cursor before returning or continuing.",
        ],
        "state_updates_required": [
            "change_map_delta",
            "evidence_delta",
            "selected_items",
            "completed_items",
            "blocked_items",
            "next_cursor",
            "next_trigger",
            "next_expected_evidence",
            "next_verifier",
            "candidate_next_items",
            "blocking_human_queue",
            "human_friction_delta",
        ],
        "continue_requires": [
            "next_cursor names the exact unfinished wave, item, file, route, log, check, or decision packet.",
            "next_cursor names one selected path, not mutually exclusive alternatives.",
            "next_expected_evidence states what new verifier evidence the next cycle should produce.",
            "next_verifier can reject bad output for the next action.",
            "blocking_human_queue is empty, or the selected next_cursor is explicitly non-blocking.",
            "human_friction_delta records whether this cycle removed or added repeated user work.",
            f"Fewer than {max_iterations} iteration(s) have run.",
        ],
        "stop_instead_of_continue_when": [
            "The next action would repeat the same observation without new evidence.",
            "The next cursor is vague, such as 'continue later' or 'keep working'.",
            "The next cursor contains unresolved alternatives instead of one selected path.",
            "No verifier can reject the next action.",
            "Human judgment or a stronger approval mode blocks the selected next action.",
        ],
        "handoff_rule": (
            "Finish every cycle with: what changed, what evidence was gained, what remains, "
            "the exact next cursor, the next expected evidence, and whether another cycle is justified."
        ),
    }


def normalize_progression_contract(
    raw: Any,
    max_items: int = 3,
    max_iterations: int = 8,
    state_file: str = "STATE.json",
) -> dict:
    fallback = build_progression_contract(
        max_items=max_items,
        max_iterations=max_iterations,
        state_file=state_file,
    )
    if not isinstance(raw, dict):
        return fallback

    normalized = dict(fallback)
    for key in ("rhythm", "state_updates_required", "continue_requires", "stop_instead_of_continue_when"):
        values = strings(raw.get(key))
        if values:
            normalized[key] = merge_missing(values, fallback[key])
    if raw.get("handoff_rule"):
        normalized["handoff_rule"] = str(raw["handoff_rule"])
    return normalized


def validate_progression_contract(contract: Any) -> dict:
    if not isinstance(contract, dict):
        return {"valid": False, "missing": sorted(REQUIRED_PROGRESSION_KEYS)}

    missing = [
        key
        for key in REQUIRED_PROGRESSION_KEYS
        if not (contract.get(key) if key == "handoff_rule" else strings(contract.get(key)))
    ]
    return {"valid": not missing, "missing": missing}
