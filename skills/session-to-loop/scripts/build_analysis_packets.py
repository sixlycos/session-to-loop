#!/usr/bin/env python3
"""Build redacted analysis packets for AI semantic review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from transcript_adapters import NormalizedEvent, iter_normalized_events


DEFAULT_INDEX = Path(".session-to-loop/private/redacted-index.json")
DEFAULT_OUT = Path(".session-to-loop/private/analysis-packets.jsonl")
DEFAULT_PACKET_INDEX = Path(".session-to-loop/private/analysis-packets-index.json")
DEFAULT_ROLE_QUOTAS = {"user": 0, "tool": 0}

HIGH_VALUE_TERMS = {
    "approval": ("approval", "approve", "ask", "confirm", "permission", "批准", "确认", "同意", "许可"),
    "correction": (
        "not npm",
        "pnpm",
        "wrong",
        "instead",
        "do not",
        "don't",
        "again",
        "不要",
        "别",
        "不是",
        "应该",
        "改成",
        "又",
        "重复",
    ),
    "risk": (
        "deploy",
        "production",
        "migration",
        "delete",
        "secret",
        "credential",
        "token",
        "payment",
        "上线",
        "生产",
        "迁移",
        "删除",
        "密钥",
        "凭证",
        "支付",
        "权限",
    ),
    "verification": (
        "verify",
        "test",
        "lint",
        "typecheck",
        "ci",
        "failed",
        "error",
        "screenshot",
        "browser",
        "验证",
        "测试",
        "截图",
        "浏览器",
        "报错",
        "失败",
        "检查",
        "我来测",
    ),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_index(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_index_path"] = str(path)
    return data


def compact_text(text: str, max_chars: int) -> tuple[str, bool]:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact, False
    return compact[: max_chars - 3].rstrip() + "...", True


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def allowed_roles(index: dict) -> set[str]:
    return set(index.get("scope_policy", {}).get("allowed_roles", ["user", "tool"]))


def snippets_allowed(index: dict) -> bool:
    return bool(index.get("scope_policy", {}).get("allow_redacted_snippets", True))


def packet_from_event(
    event: NormalizedEvent,
    sequence: int,
    source_file: str,
    source_type: str,
    source_confidence: str,
    max_chars: int,
    allow_text: bool,
) -> dict:
    packet_text, truncated = compact_text(event.text, max_chars)
    return {
        "packet_id": f"packet-{sequence:06d}",
        "packet_type": "transcript_event",
        "provider": event.provider,
        "event_kind": event.event_kind,
        "source_type": source_type,
        "source_confidence": source_confidence,
        "source": event.source,
        "source_file": source_file,
        "session_id": event.session_id,
        "role": event.role,
        "tool_name": event.tool_name,
        "text": packet_text if allow_text else "[SNIPPET_DISABLED_BY_SCOPE]",
        "text_hash": text_hash(event.text),
        "text_truncated": truncated,
        "redacted": True,
        "structured": event.structured if allow_text else {},
    }


def estimated_tokens(text: str) -> int:
    # Cheap local estimate. Good enough for packet selection without tokenizer dependencies.
    return max(1, (len(text) + 3) // 4)


def importance(packet: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    role = packet.get("role")
    if role == "user":
        score += 50
        reasons.append("user-primary")
    elif role == "tool":
        score += 35
        reasons.append("tool-support")
    else:
        score += 5
        reasons.append("weak-role")

    if packet.get("source_type") == "auxiliary-evidence":
        score += 20
        reasons.append("auxiliary-project-evidence")

    text = str(packet.get("text", "")).lower()
    tool_name = str(packet.get("tool_name") or "").lower()
    haystack = f"{tool_name} {text}"
    for reason, terms in HIGH_VALUE_TERMS.items():
        if any(term in haystack for term in terms):
            score += 15
            reasons.append(reason)

    if packet.get("text_truncated"):
        score -= 5
        reasons.append("truncated")

    return score, reasons


def annotate_packet(packet: dict) -> dict:
    score, reasons = importance(packet)
    packet["importance_score"] = score
    packet["importance_reasons"] = reasons
    packet["estimated_tokens"] = estimated_tokens(str(packet.get("text", "")))
    return packet


def iter_packets(index: dict, max_chars: int) -> Iterator[dict]:
    roles = allowed_roles(index)
    allow_text = snippets_allowed(index)
    sequence = 0
    for file_info in index.get("files", []):
        path = Path(file_info["path"])
        source_file = file_info.get("source_label", path.name)
        source_type = file_info.get("source_type", "generic-jsonl")
        source_confidence = file_info.get("classification_confidence", "low")
        for event in iter_normalized_events(path, source_type=source_type, provider_hint=file_info.get("provider")):
            if event.role not in roles:
                continue
            sequence += 1
            yield annotate_packet(
                packet_from_event(event, sequence, source_file, source_type, source_confidence, max_chars, allow_text)
            )


def parse_role_quota(values: list[str]) -> dict[str, int]:
    quotas = dict(DEFAULT_ROLE_QUOTAS)
    for value in values:
        if "=" not in value:
            raise ValueError(f"Invalid role quota {value!r}; expected role=count.")
        role, raw_count = value.split("=", 1)
        role = role.strip()
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise ValueError(f"Invalid role quota count in {value!r}.") from exc
        if count < 0:
            raise ValueError(f"Invalid role quota {value!r}; count must be non-negative.")
        quotas[role] = count
    return quotas


def within_limits(packet: dict, kept: list[dict], max_packets: int, target_token_budget: int) -> bool:
    if max_packets > 0 and len(kept) >= max_packets:
        return False
    if target_token_budget > 0:
        used = sum(int(item.get("estimated_tokens", 0)) for item in kept)
        return used + int(packet.get("estimated_tokens", 0)) <= target_token_budget
    return True


def select_packets(
    packets: list[dict],
    max_packets: int,
    target_token_budget: int,
    role_quotas: dict[str, int],
) -> tuple[list[dict], dict]:
    if max_packets <= 0 and target_token_budget <= 0:
        for packet in packets:
            packet["selection_reason"] = "uncapped"
        return packets, {
            "enabled": False,
            "input_count": len(packets),
            "kept_count": len(packets),
            "dropped_count": 0,
            "estimated_tokens": sum(int(item.get("estimated_tokens", 0)) for item in packets),
        }

    ranked = sorted(
        packets,
        key=lambda item: (-int(item.get("importance_score", 0)), item.get("packet_id", "")),
    )
    kept: list[dict] = []
    kept_ids: set[str] = set()

    for role, quota in role_quotas.items():
        if quota <= 0:
            continue
        role_packets = [item for item in ranked if item.get("role") == role]
        kept_for_role = 0
        for packet in role_packets:
            if kept_for_role >= quota:
                break
            if packet["packet_id"] in kept_ids or not within_limits(packet, kept, max_packets, target_token_budget):
                continue
            packet["selection_reason"] = f"role-quota:{role}"
            kept.append(packet)
            kept_ids.add(packet["packet_id"])
            kept_for_role += 1

    for packet in ranked:
        if packet["packet_id"] in kept_ids or not within_limits(packet, kept, max_packets, target_token_budget):
            continue
        packet["selection_reason"] = "importance"
        kept.append(packet)
        kept_ids.add(packet["packet_id"])

    kept.sort(key=lambda item: item.get("packet_id", ""))
    dropped = [item for item in packets if item["packet_id"] not in kept_ids]
    for packet in dropped:
        packet["selection_reason"] = "dropped-by-budget"

    kept_by_role: dict[str, int] = {}
    dropped_by_role: dict[str, int] = {}
    for packet in kept:
        role = str(packet.get("role", "unknown"))
        kept_by_role[role] = kept_by_role.get(role, 0) + 1
    for packet in dropped:
        role = str(packet.get("role", "unknown"))
        dropped_by_role[role] = dropped_by_role.get(role, 0) + 1

    return kept, {
        "enabled": True,
        "input_count": len(packets),
        "kept_count": len(kept),
        "dropped_count": len(dropped),
        "max_packets": max_packets,
        "target_token_budget": target_token_budget,
        "role_quotas": role_quotas,
        "estimated_tokens": sum(int(item.get("estimated_tokens", 0)) for item in kept),
        "dropped_estimated_tokens": sum(int(item.get("estimated_tokens", 0)) for item in dropped),
        "kept_by_role": kept_by_role,
        "dropped_by_role": dropped_by_role,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build redacted JSONL packets for AI semantic analysis.")
    parser.add_argument(
        "--redacted-index",
        default=str(DEFAULT_INDEX),
        help=f"Index from redact_transcripts.py. Default: {DEFAULT_INDEX}",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"Packet JSONL output. Default: {DEFAULT_OUT}")
    parser.add_argument(
        "--packet-index",
        default=str(DEFAULT_PACKET_INDEX),
        help=f"Packet index JSON output. Default: {DEFAULT_PACKET_INDEX}",
    )
    parser.add_argument("--max-chars", type=int, default=1200, help="Maximum text chars per event packet.")
    parser.add_argument("--max-packets", type=int, default=0, help="Maximum packets to keep after importance ranking. 0 keeps all.")
    parser.add_argument(
        "--target-token-budget",
        type=int,
        default=0,
        help="Approximate packet token budget after selection. 0 disables token-budget selection.",
    )
    parser.add_argument(
        "--role-quota",
        action="append",
        default=[],
        help="Minimum high-priority packets to reserve by role, e.g. --role-quota user=20 --role-quota tool=10.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = load_index(Path(args.redacted_index))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    role_quotas = parse_role_quota(args.role_quota)
    packets_to_consider = list(iter_packets(index, args.max_chars))
    selected_packets, selection = select_packets(
        packets_to_consider,
        max(0, args.max_packets),
        max(0, args.target_token_budget),
        role_quotas,
    )
    packet_count = 0
    provider_counts: dict[str, int] = {}
    source_type_counts: dict[str, int] = {}
    with out.open("w", encoding="utf-8") as handle:
        for packet in selected_packets:
            packet_count += 1
            provider = str(packet.get("provider", "unknown"))
            source_type = str(packet.get("source_type", "unknown"))
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
            handle.write(json.dumps(packet, ensure_ascii=False) + "\n")

    packet_index = {
        "version": 1,
        "created_at": now_iso(),
        "analysis_model": "ai-semantic-packets-v1",
        "redacted_index": str(Path(args.redacted_index)),
        "packets": str(out),
        "packet_count": packet_count,
        "provider_counts": provider_counts,
        "packet_selection": selection,
        "scope_policy": index.get("scope_policy", {}),
        "source": {
            "transcript_files": index.get("file_count", 0),
            "records": index.get("record_count", 0),
            "providers": provider_counts,
            "source_types": source_type_counts,
        },
        "redaction": {
            "enabled": bool(index.get("redaction_enabled")),
            "redactions": index.get("redactions", 0),
        },
    }
    packet_index_path = Path(args.packet_index)
    packet_index_path.parent.mkdir(parents=True, exist_ok=True)
    packet_index_path.write_text(json.dumps(packet_index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Built {packet_count} analysis packet(s): {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"build_analysis_packets.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
