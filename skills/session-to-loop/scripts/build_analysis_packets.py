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
from typing import Any, Iterator


DEFAULT_INDEX = Path(".session-to-loop/private/redacted-index.json")
DEFAULT_OUT = Path(".session-to-loop/private/analysis-packets.jsonl")
DEFAULT_PACKET_INDEX = Path(".session-to-loop/private/analysis-packets-index.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_index(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_index_path"] = str(path)
    return data


def iter_jsonl(path: Path) -> Iterator[tuple[int, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                yield line_number, json.loads(line)


def lower_str(value: Any) -> str:
    return value.lower() if isinstance(value, str) else ""


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)
    if isinstance(value, dict):
        preferred = []
        for key in (
            "text",
            "content",
            "message",
            "name",
            "command",
            "arguments",
            "output",
            "result",
            "stdout",
            "stderr",
            "summary",
            "msg",
        ):
            if key in value:
                preferred.append(flatten_text(value[key]))
        if preferred:
            return " ".join(part for part in preferred if part)
        return " ".join(flatten_text(item) for item in value.values())
    return ""


def codex_session_meta_id(record: dict) -> str | None:
    meta = record.get("session_meta")
    if not isinstance(meta, dict):
        return None
    payload = meta.get("payload")
    if isinstance(payload, dict):
        for key in ("id", "session_id", "conversation_id"):
            if payload.get(key):
                return str(payload[key])
    for key in ("id", "session_id", "conversation_id"):
        if meta.get(key):
            return str(meta[key])
    return None


def role_of(record: Any) -> str:
    if not isinstance(record, dict):
        return "unknown"

    item = record.get("response_item")
    if isinstance(item, dict):
        item_type = lower_str(item.get("type"))
        role = lower_str(item.get("role"))
        if role in {"user", "assistant"}:
            return role
        if item_type in {"function_call", "function_call_output", "tool_call", "tool_result"}:
            return "tool"
        if item_type in {"reasoning", "message"}:
            return "assistant"

    if isinstance(record.get("event_msg"), dict):
        return "tool"

    role = record.get("type") or record.get("role")
    if isinstance(role, str):
        lowered = role.lower()
        if lowered in {"user", "assistant", "tool"}:
            return lowered
    message = record.get("message")
    if isinstance(message, dict) and isinstance(message.get("role"), str):
        return message["role"].lower()
    return "unknown"


def packet_payload(record: Any) -> Any:
    if isinstance(record, dict):
        if isinstance(record.get("response_item"), dict):
            return record["response_item"]
        if isinstance(record.get("event_msg"), dict):
            return record["event_msg"]
    return record


def compact_text(text: str, max_chars: int) -> tuple[str, bool]:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact, False
    return compact[: max_chars - 3].rstrip() + "...", True


def session_id_of(record: Any) -> str:
    if isinstance(record, dict):
        meta_id = codex_session_meta_id(record)
        if meta_id:
            return meta_id
        item = record.get("response_item")
        if isinstance(item, dict):
            for key in ("session_id", "conversation_id"):
                if item.get(key):
                    return str(item[key])
        return str(record.get("session_id") or record.get("conversation_id") or "unknown-session")
    return "unknown-session"


def tool_name_of(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    item = record.get("response_item")
    if isinstance(item, dict) and isinstance(item.get("name"), str):
        return item["name"]
    event = record.get("event_msg")
    if isinstance(event, dict):
        if isinstance(event.get("name"), str):
            return event["name"]
        if isinstance(event.get("tool_name"), str):
            return event["tool_name"]
    if isinstance(record.get("name"), str):
        return record["name"]
    return None


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def allowed_roles(index: dict) -> set[str]:
    return set(index.get("scope_policy", {}).get("allowed_roles", ["user", "tool"]))


def snippets_allowed(index: dict) -> bool:
    return bool(index.get("scope_policy", {}).get("allow_redacted_snippets", True))


def iter_packets(index: dict, max_chars: int) -> Iterator[dict]:
    roles = allowed_roles(index)
    allow_text = snippets_allowed(index)
    sequence = 0
    for file_info in index.get("files", []):
        path = Path(file_info["path"])
        source_file = file_info.get("source_label", path.name)
        current_session_id = "unknown-session"
        for event_index, record in iter_jsonl(path):
            if isinstance(record, dict):
                current_session_id = codex_session_meta_id(record) or current_session_id
                if "session_meta" in record and len(record) == 1:
                    continue
            role = role_of(record)
            if role not in roles:
                continue
            payload = packet_payload(record)
            text = flatten_text(payload)
            packet_text, truncated = compact_text(text, max_chars)
            session_id = session_id_of(record)
            if session_id == "unknown-session":
                session_id = current_session_id
            sequence += 1
            yield {
                "packet_id": f"packet-{sequence:06d}",
                "packet_type": "transcript_event",
                "source": f"session:{session_id}#event-{event_index}",
                "source_file": source_file,
                "session_id": session_id,
                "role": role,
                "tool_name": tool_name_of(record),
                "text": packet_text if allow_text else "[SNIPPET_DISABLED_BY_SCOPE]",
                "text_hash": text_hash(text),
                "text_truncated": truncated,
                "redacted": True,
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index = load_index(Path(args.redacted_index))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    packet_count = 0
    with out.open("w", encoding="utf-8") as handle:
        for packet in iter_packets(index, args.max_chars):
            packet_count += 1
            handle.write(json.dumps(packet, ensure_ascii=False) + "\n")

    packet_index = {
        "version": 1,
        "created_at": now_iso(),
        "analysis_model": "ai-semantic-packets-v1",
        "redacted_index": str(Path(args.redacted_index)),
        "packets": str(out),
        "packet_count": packet_count,
        "scope_policy": index.get("scope_policy", {}),
        "source": {
            "transcript_files": index.get("file_count", 0),
            "records": index.get("record_count", 0),
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
