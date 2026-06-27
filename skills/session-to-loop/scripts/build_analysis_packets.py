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
            yield packet_from_event(event, sequence, source_file, source_type, source_confidence, max_chars, allow_text)


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
    provider_counts: dict[str, int] = {}
    source_type_counts: dict[str, int] = {}
    with out.open("w", encoding="utf-8") as handle:
        for packet in iter_packets(index, args.max_chars):
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
