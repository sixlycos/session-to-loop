#!/usr/bin/env python3
"""Prepare an explicit analysis scope from a transcript inventory."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_MANIFEST = Path(".session-to-loop/private/discovered-sessions.json")
DEFAULT_OUT = Path(".session-to-loop/private/analysis-scope.json")
DEFAULT_ROLES = ["user", "tool"]
VALID_ROLES = {"user", "tool", "assistant"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_roles(roles: list[str]) -> list[str]:
    normalized = []
    for role in roles:
        lowered = role.lower()
        if lowered not in VALID_ROLES:
            raise ValueError(f"Unsupported role: {role}")
        if lowered not in normalized:
            normalized.append(lowered)
    return normalized


def build_scope(args: argparse.Namespace) -> dict:
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    roles = normalize_roles(args.roles)
    files = [
        {
            "path": item["path"],
            "label": item.get("label", Path(item["path"]).name),
            "size_bytes": item.get("size_bytes"),
            "mtime": item.get("mtime"),
            "format": item.get("format", "jsonl"),
            "provider": item.get("provider", "generic"),
            "source_type": item.get("source_type", "generic-jsonl"),
            "classification_confidence": item.get("classification_confidence", "low"),
            "classification_reason": item.get("classification_reason", ""),
        }
        for item in manifest.get("files", [])
    ]
    return {
        "version": 1,
        "created_at": now_iso(),
        "approved": bool(args.approve),
        "approval_mode": "explicit-cli-flag" if args.approve else "pending-user-confirmation",
        "manifest": str(manifest_path),
        "allowed_files": files,
        "allowed_roles": roles,
        "allow_redacted_snippets": not args.source_pointers_only,
        "output_visibility": args.output_visibility,
        "notes": args.note or "",
        "content_policy": {
            "read_transcript_body_after_approval": bool(args.approve),
            "raw_transcripts_stay_private": True,
            "assistant_messages_are_context_only": "assistant" not in roles,
            "tool_events_are_supporting_evidence": "tool" in roles,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an analysis scope from a discovered transcript inventory. "
            "This script does not read transcript bodies."
        )
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help=f"Manifest from discover_claude_sessions.py. Default: {DEFAULT_MANIFEST}",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT), help=f"Scope output path. Default: {DEFAULT_OUT}")
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Mark this scope as approved. Downstream scripts refuse unapproved scopes.",
    )
    parser.add_argument(
        "--roles",
        nargs="+",
        default=DEFAULT_ROLES,
        help="Transcript roles allowed for analysis. Default: user tool",
    )
    parser.add_argument(
        "--source-pointers-only",
        action="store_true",
        help="Do not preserve redacted evidence snippets; keep source pointers only.",
    )
    parser.add_argument(
        "--output-visibility",
        choices=["private", "public"],
        default="private",
        help="Intended output visibility. Default: private",
    )
    parser.add_argument("--note", default="", help="Optional human-readable scope note.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scope = build_scope(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    status = "approved" if scope["approved"] else "pending approval"
    print(f"Prepared {status} scope for {len(scope['allowed_files'])} file(s): {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"prepare_analysis_scope.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
