#!/usr/bin/env python3
"""Redact transcript JSONL records before downstream analysis."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path(".session-to-loop/private/discovered-sessions.json")
DEFAULT_SCOPE = Path(".session-to-loop/private/analysis-scope.json")
DEFAULT_OUT_DIR = Path(".session-to-loop/private/redacted")
DEFAULT_INDEX = Path(".session-to-loop/private/redacted-index.json")

REDACTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b((?:[A-Z][A-Z0-9_]{2,}|api[_-]?key|token|secret|password|passwd|pwd)\s*=\s*)"
            r"([^\s'\"`]+)",
            re.IGNORECASE,
        ),
        r"\1[REDACTED_SECRET]",
    ),
    (re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE), "Bearer [REDACTED_SECRET]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"https?://[^\s)>\"]+"), "[REDACTED_URL]"),
    (re.compile(r"\b[A-Za-z]:\\[^\s'\"`<>|]+(?:\\[^\s'\"`<>|]+)*"), "[REDACTED_PATH]"),
    (re.compile(r"(?<!\w)/(?:Users|home)/[^\s'\"`<>|]+(?:/[^\s'\"`<>|]+)*"), "[REDACTED_PATH]"),
    (re.compile(r"(?<!\w)/mnt/[a-z]/[^\s'\"`<>|]+(?:/[^\s'\"`<>|]+)*", re.IGNORECASE), "[REDACTED_PATH]"),
    (re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_+/=-]{32,}(?![A-Za-z0-9])"), "[REDACTED_SECRET]"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_string(value: str) -> tuple[str, int]:
    redactions = 0
    redacted = value
    for pattern, replacement in REDACTION_PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        redactions += count
    return redacted, redactions


def redact_value(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, list):
        redacted_items = []
        total = 0
        for item in value:
            redacted, count = redact_value(item)
            redacted_items.append(redacted)
            total += count
        return redacted_items, total
    if isinstance(value, dict):
        redacted_dict = {}
        total = 0
        for key, item in value.items():
            redacted, count = redact_value(item)
            redacted_dict[key] = redacted
            total += count
        return redacted_dict, total
    return value, 0


def load_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("files", [])


def load_scope(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("approved"):
        raise PermissionError(f"Analysis scope is not approved: {path}")
    return data


def scoped_files(manifest_files: list[dict], scope: dict | None) -> list[dict]:
    if scope is None:
        return manifest_files
    allowed = {str(Path(item["path"]).resolve()) for item in scope.get("allowed_files", [])}
    return [item for item in manifest_files if str(Path(item["path"]).resolve()) in allowed]


def parse_jsonl_line(line: str) -> Any:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"type": "raw", "text": line.rstrip("\n")}


def redact_file(source: Path, label: str, out_path: Path) -> dict:
    record_count = 0
    redaction_count = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with source.open("r", encoding="utf-8") as src, out_path.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            record = parse_jsonl_line(line)
            redacted, count = redact_value(record)
            redaction_count += count
            record_count += 1
            dst.write(json.dumps(redacted, ensure_ascii=False) + "\n")
    return {
        "source_path": str(source),
        "source_label": label,
        "path": str(out_path),
        "record_count": record_count,
        "redactions": redaction_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Redact discovered transcript files.")
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help=f"Manifest from discover_claude_sessions.py. Default: {DEFAULT_MANIFEST}",
    )
    parser.add_argument(
        "--scope",
        default=None,
        help=f"Approved scope from prepare_analysis_scope.py. Recommended default: {DEFAULT_SCOPE}",
    )
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help=f"Directory for redacted JSONL files. Default: {DEFAULT_OUT_DIR}",
    )
    parser.add_argument(
        "--index",
        default=str(DEFAULT_INDEX),
        help=f"Redaction index output path. Default: {DEFAULT_INDEX}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    scope = load_scope(Path(args.scope)) if args.scope else None
    files = scoped_files(load_manifest(manifest_path), scope)
    out_dir = Path(args.out_dir)
    results = []
    for idx, file_info in enumerate(files, start=1):
        source = Path(file_info["path"])
        safe_name = f"{idx:03d}-{source.name}"
        results.append(redact_file(source, file_info.get("label", source.name), out_dir / safe_name))

    index = {
        "version": 1,
        "created_at": now_iso(),
        "redaction_enabled": True,
        "manifest": str(manifest_path),
        "scope": str(Path(args.scope)) if args.scope else None,
        "scope_policy": {
            "approved": bool(scope.get("approved")) if scope else False,
            "allowed_roles": scope.get("allowed_roles", ["user", "tool"]) if scope else ["user", "tool"],
            "allow_redacted_snippets": scope.get("allow_redacted_snippets", True) if scope else True,
            "output_visibility": scope.get("output_visibility", "private") if scope else "private",
        },
        "files": results,
        "file_count": len(results),
        "record_count": sum(item["record_count"] for item in results),
        "redactions": sum(item["redactions"] for item in results),
    }
    index_path = Path(args.index)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Redacted {index['record_count']} record(s), {index['redactions']} replacement(s): {index_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"redact_transcripts.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
