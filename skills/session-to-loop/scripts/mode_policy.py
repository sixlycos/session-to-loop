"""Shared SixLoops start-mode mapping."""

from __future__ import annotations


INTERNAL_TO_MODE = {
    "read-only": "read-only",
    "goal-loop": "low-risk edit",
    "isolated-draft": "worktree draft",
    "verified-pr-draft": "PR draft",
    "scheduled-readonly": "scheduled read-only",
    "scheduled-draft": "scheduled draft",
}

MODE_TO_INTERNAL = {mode: level for level, mode in INTERNAL_TO_MODE.items()}

RUN_MODES = ["read-only", "low-risk edit", "worktree draft", "PR draft"]
SCHEDULED_MODES = ["scheduled read-only", "scheduled draft"]

MODE_ALIASES = {
    "read only": "read-only",
    "readonly": "read-only",
    "low risk edit": "low-risk edit",
    "goal loop": "low-risk edit",
    "worktree draft": "worktree draft",
    "isolated draft": "worktree draft",
    "pr draft": "PR draft",
    "verified pr draft": "PR draft",
    "scheduled read only": "scheduled read-only",
    "scheduled readonly": "scheduled read-only",
    "scheduled draft": "scheduled draft",
}


def level_to_mode(level: str, default: str = "worktree draft") -> str:
    return INTERNAL_TO_MODE.get(str(level), default)


def _alias_key(value: str) -> str:
    return " ".join(value.strip().replace("_", " ").replace("-", " ").lower().split())


def normalize_mode(value: str) -> str:
    text = str(value).strip()
    if text in MODE_TO_INTERNAL:
        return text
    if text in INTERNAL_TO_MODE:
        return INTERNAL_TO_MODE[text]
    key = _alias_key(text)
    if key in MODE_ALIASES:
        return MODE_ALIASES[key]
    allowed = ", ".join(RUN_MODES + SCHEDULED_MODES)
    raise ValueError(f"Unknown start mode {value!r}. Expected one of: {allowed}.")


def mode_to_level(value: str) -> str:
    return MODE_TO_INTERNAL[normalize_mode(value)]
