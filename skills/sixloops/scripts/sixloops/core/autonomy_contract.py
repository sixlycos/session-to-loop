"""Shared autonomous decision contract helpers."""

from __future__ import annotations

from typing import Any


REQUIRED_AUTONOMY_KEYS = {
    "decision_policy",
    "self_iteration_policy",
    "subagent_control",
    "human_return_policy",
}


def as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def strings(value: Any) -> list[str]:
    return [str(item) for item in as_list(value) if str(item).strip()]


def merge_missing(primary: list[str], required: list[str]) -> list[str]:
    result = list(primary)
    seen = set(primary)
    result.extend(item for item in required if item not in seen)
    return result


def build_autonomy_contract(team_mode: str = "phased") -> dict:
    return {
        "decision_policy": [
            "When multiple next actions are plausible, rank them by user value, verifier availability, reversibility, risk, and progress toward the Change Map.",
            "Choose the highest-ranked action that is inside the approved mode and has a verifier; do not ask the user to choose ordinary engineering next steps.",
            "If the highest-value action is blocked by human approval or product judgment, select the best non-blocking evidence or cleanup action instead.",
            "Return to the user only when all useful non-blocking actions are exhausted or the selected action requires human judgment or stronger approval.",
        ],
        "self_iteration_policy": [
            "Prefer a coherent sequence of bounded shots over a single oversized one-shot.",
            "After each shot, use verifier evidence to update candidate_next_items, choose the next shot, and continue while risk and budget remain in scope.",
            "Do not repeat a shot unless the next attempt uses new evidence, a narrower hypothesis, or a different verifier.",
            "Treat model judgment as the selector for the next bounded shot; treat deterministic checks as rejection gates.",
        ],
        "subagent_control": [
            f"Use `{team_mode}` coordination by default; spawn or emulate only the roles needed for the selected shot.",
            "Start planner/checker/verifier roles when they can reduce uncertainty or reject output independently.",
            "Start maker roles only inside explicit edit scope and stop them after the selected shot is verified or blocked.",
            "Do not keep subagents running after their evidence, patch, review, or verifier output has been integrated into state.",
        ],
        "human_return_policy": [
            "Ask the user only for product, architecture, release, security, data, billing, permission, production, irreversible, or scope-expanding decisions.",
            "Before asking, package options, impact, regression path, recommendation, and the best non-blocking action already attempted or rejected.",
            "Do not ask for ordinary prioritization when the model can choose using evidence, verifier availability, risk, and approved mode.",
        ],
    }


def normalize_autonomy_contract(raw: Any, team_mode: str = "phased") -> dict:
    fallback = build_autonomy_contract(team_mode=team_mode)
    if not isinstance(raw, dict):
        return fallback

    normalized = dict(fallback)
    for key in REQUIRED_AUTONOMY_KEYS:
        values = strings(raw.get(key))
        if values:
            normalized[key] = merge_missing(values, fallback[key])
    return normalized


def validate_autonomy_contract(contract: Any) -> dict:
    if not isinstance(contract, dict):
        return {"valid": False, "missing": sorted(REQUIRED_AUTONOMY_KEYS)}

    missing = [key for key in REQUIRED_AUTONOMY_KEYS if not strings(contract.get(key))]
    return {"valid": not missing, "missing": missing}
