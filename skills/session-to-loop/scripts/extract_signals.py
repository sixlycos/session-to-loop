#!/usr/bin/env python3
"""Extract user-centered loop-engineering signals from redacted transcript JSONL."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from transcript_adapters import iter_normalized_events


DEFAULT_INDEX = Path(".session-to-loop/private/redacted-index.json")
DEFAULT_OUT = Path(".session-to-loop/private/signals.json")

USER_PATTERNS = [
    {
        "id": "ci-babysitter",
        "name": "CI Babysitter Loop",
        "signal_kind": "repeated-verification",
        "intent": "verification_request",
        "terms": ("ci", "failed job", "failed log", "verify locally", "local test", "do not push"),
    },
    {
        "id": "package-manager-rule",
        "name": "Package Manager Rule",
        "signal_kind": "repeated-context-repair",
        "intent": "human_correction",
        "terms": ("pnpm", "not npm", "npm install", "pnpm only"),
    },
    {
        "id": "deploy-approval-gate",
        "name": "Deploy Approval Gate",
        "signal_kind": "repeated-human-decision",
        "intent": "approval_required",
        "terms": ("deploy", "production", "release", "migration", "approve", "without asking"),
    },
    {
        "id": "transcript-redaction-boundary",
        "name": "Transcript Redaction Boundary",
        "signal_kind": "privacy-redaction",
        "intent": "privacy_boundary",
        "terms": ("[redacted_secret]", "[redacted_email]", "[redacted_url]", "secret", "redact", "leak"),
    },
]

TOOL_PATTERNS = [
    {
        "id": "ci-babysitter",
        "name": "CI Babysitter Loop",
        "signal_kind": "tool-status",
        "intent": "tool_status_check",
        "terms": ("ci-status", "failed: unit-tests", "unit-tests", "failed job", "test failed"),
    },
    {
        "id": "package-manager-rule",
        "name": "Package Manager Rule",
        "signal_kind": "tool-usage",
        "intent": "package_tool_usage",
        "terms": ("pnpm", "npm install", "package manager"),
    },
    {
        "id": "deploy-approval-gate",
        "name": "Deploy Approval Gate",
        "signal_kind": "tool-status",
        "intent": "deploy_status_check",
        "terms": ("deploy", "deployment", "production", "migration"),
    },
    {
        "id": "provider-acceptance-soak",
        "name": "Provider Acceptance Soak Loop",
        "signal_kind": "project-auxiliary-evidence",
        "intent": "provider_acceptance_regression",
        "terms": (
            "soak",
            "latency",
            "http 200",
            "semantic",
            "assertion",
            "model_echo",
            "schema",
            "provider",
        ),
    },
    {
        "id": "browser-audit-loop",
        "name": "Browser Audit Loop",
        "signal_kind": "project-auxiliary-evidence",
        "intent": "browser_audit_regression",
        "terms": ("browse", "browser", "screenshot", "snapshot", "goto", "click", "fill", "i18n"),
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_index(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_index_path"] = str(path)
    return data


def snippet(text: str, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def session_from_source(source: str) -> str:
    return source.split("#", 1)[0].removeprefix("session:")


def term_matches(term: str, lowered_text: str) -> bool:
    if re.fullmatch(r"[a-z0-9]+", term) and len(term) <= 3:
        return re.search(rf"\b{re.escape(term)}\b", lowered_text) is not None
    return term in lowered_text


def match_patterns(patterns: list[dict], text: str) -> list[dict]:
    lowered = text.lower()
    matches = []
    for pattern in patterns:
        hit_terms = [term for term in pattern["terms"] if term_matches(term, lowered)]
        if hit_terms:
            matches.append({**pattern, "hit_terms": hit_terms})
    return matches


def event_matches(role: str, text: str) -> list[dict]:
    if role == "user":
        return match_patterns(USER_PATTERNS, text)
    if role == "tool":
        return match_patterns(TOOL_PATTERNS, text)
    return []


def allowed_roles_from_index(index: dict) -> set[str]:
    return set(index.get("scope_policy", {}).get("allowed_roles", ["user", "tool"]))


def snippets_allowed(index: dict) -> bool:
    return bool(index.get("scope_policy", {}).get("allow_redacted_snippets", True))


def add_event(
    groups: dict[str, dict],
    match: dict,
    role: str,
    provider: str,
    event_kind: str,
    source_type: str,
    source: str,
    source_file: str,
    text: str,
    allow_snippet: bool,
) -> None:
    group = groups.setdefault(
        match["id"],
        {
            "id": match["id"],
            "name": match["name"],
            "signal_kind": match["signal_kind"],
            "sessions": set(),
            "user_sessions": set(),
            "tool_sessions": set(),
            "role_counts": {"user": 0, "tool": 0, "assistant": 0, "unknown": 0},
            "provider_counts": {},
            "source_type_counts": {},
            "events": [],
            "terms": set(),
            "intents": set(),
        },
    )
    session_id = session_from_source(source)
    group["sessions"].add(session_id)
    if role == "user":
        group["user_sessions"].add(session_id)
    elif role == "tool":
        group["tool_sessions"].add(session_id)
    group["role_counts"][role if role in group["role_counts"] else "unknown"] += 1
    group["provider_counts"][provider] = group["provider_counts"].get(provider, 0) + 1
    group["source_type_counts"][source_type] = group["source_type_counts"].get(source_type, 0) + 1
    group["terms"].update(match["hit_terms"])
    group["intents"].add(match["intent"])
    group["events"].append(
        {
            "source": source,
            "source_file": source_file,
            "role": role,
            "provider": provider,
            "event_kind": event_kind,
            "source_type": source_type,
            "intent": match["intent"],
            "kind": match["signal_kind"],
            "snippet": snippet(text) if allow_snippet else "[SNIPPET_DISABLED_BY_SCOPE]",
        }
    )


def fallback_one_off(first_event: dict | None) -> dict:
    event = first_event or {
        "source": "session:single-session#event-1",
        "source_file": "input",
        "role": "unknown",
        "intent": "one_off_task",
        "kind": "one-off-event",
        "snippet": "Single task with no repeated loop signal.",
    }
    role = event["role"] if event["role"] in {"user", "tool", "assistant"} else "unknown"
    role_counts = {"user": 0, "tool": 0, "assistant": 0, "unknown": 0}
    role_counts[role] = 1
    return {
        "id": "one-off-bugfix",
        "name": "One-off Bugfix",
        "signal_kind": "one-off-event",
        "mechanism_hints": [],
        "session_count": 1,
        "event_count": 1,
        "primary_role": role,
        "role_counts": role_counts,
        "provider_counts": {event.get("provider", "generic"): 1},
        "source_type_counts": {event.get("source_type", "generic-jsonl"): 1},
        "sessions": [session_from_source(event["source"])],
        "user_sessions": [session_from_source(event["source"])] if event["role"] == "user" else [],
        "tool_sessions": [],
        "terms": [],
        "intents": ["one_off_task"],
        "evidence": [event],
    }


def signal_from_group(group: dict) -> dict:
    user_sessions = sorted(group["user_sessions"])
    tool_sessions = sorted(group["tool_sessions"])
    sessions = sorted(group["sessions"])
    effective_sessions = user_sessions or sessions
    role_counts = group["role_counts"]
    primary_role = "user" if role_counts["user"] else "tool" if role_counts["tool"] else "unknown"
    return {
        "id": group["id"],
        "name": group["name"],
        "signal_kind": group["signal_kind"],
        "mechanism_hints": mechanism_hints_for(group["id"]),
        "session_count": len(effective_sessions),
        "event_count": len(group["events"]),
        "primary_role": primary_role,
        "role_counts": role_counts,
        "sessions": effective_sessions,
        "user_sessions": user_sessions,
        "tool_sessions": tool_sessions,
        "terms": sorted(group["terms"]),
        "intents": sorted(group["intents"]),
        "provider_counts": dict(sorted(group["provider_counts"].items())),
        "source_type_counts": dict(sorted(group["source_type_counts"].items())),
        "evidence": group["events"][:5],
    }


def mechanism_hints_for(signal_id: str) -> list[str]:
    return {
        "ci-babysitter": ["loop", "skill"],
        "package-manager-rule": ["rule"],
        "deploy-approval-gate": ["checklist", "approval-gate"],
        "transcript-redaction-boundary": ["checklist"],
    }.get(signal_id, [])


def extract(index: dict) -> dict:
    groups: dict[str, dict] = {}
    total_events = 0
    first_event: dict | None = None
    provider_counts: dict[str, int] = {}
    source_type_counts: dict[str, int] = {}
    allowed_roles = allowed_roles_from_index(index)
    allow_snippet = snippets_allowed(index)
    for file_info in index.get("files", []):
        source_file = file_info.get("source_label", Path(file_info["path"]).name)
        source_type = file_info.get("source_type", "generic-jsonl")
        for event in iter_normalized_events(
            Path(file_info["path"]), source_type=source_type, provider_hint=file_info.get("provider")
        ):
            total_events += 1
            provider_counts[event.provider] = provider_counts.get(event.provider, 0) + 1
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
            if event.role not in allowed_roles:
                continue
            if first_event is None:
                first_event = {
                    "source": event.source,
                    "source_file": source_file,
                    "role": event.role,
                    "provider": event.provider,
                    "event_kind": event.event_kind,
                    "source_type": source_type,
                    "intent": "one_off_task",
                    "kind": "one-off-event",
                    "snippet": snippet(event.text) if allow_snippet else "[SNIPPET_DISABLED_BY_SCOPE]",
                }
            for match in event_matches(event.role, event.text):
                add_event(
                    groups,
                    match,
                    event.role,
                    event.provider,
                    event.event_kind,
                    source_type,
                    event.source,
                    source_file,
                    event.text,
                    allow_snippet,
                )

    signals = [signal_from_group(group) for group in groups.values()]
    if not signals and total_events:
        signals = [fallback_one_off(first_event)]

    signals.sort(key=lambda item: (-item["session_count"], item["id"]))
    return {
        "version": 1,
        "created_at": now_iso(),
        "analysis_model": "user-message-primary-tool-usage-supporting-v1",
        "scope_policy": index.get(
            "scope_policy",
            {
                "approved": False,
                "allowed_roles": sorted(allowed_roles),
                "allow_redacted_snippets": allow_snippet,
                "output_visibility": "private",
            },
        ),
        "source": {
            "redacted_index": index.get("_index_path"),
            "transcript_files": index.get("file_count", 0),
            "records": index.get("record_count", 0),
            "providers": provider_counts,
            "source_types": source_type_counts,
        },
        "redaction": {
            "enabled": bool(index.get("redaction_enabled")),
            "redactions": index.get("redactions", 0),
        },
        "signals": signals,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract recurring workflow signals from redacted transcripts.")
    parser.add_argument(
        "--redacted-index",
        default=str(DEFAULT_INDEX),
        help=f"Index from redact_transcripts.py. Default: {DEFAULT_INDEX}",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"Signals output path. Default: {DEFAULT_OUT}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    signals = extract(load_index(Path(args.redacted_index)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(signals, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Extracted {len(signals['signals'])} signal group(s): {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"extract_signals.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
