#!/usr/bin/env python3
"""Discover transcript files from explicit user-provided paths."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_OUT = Path(".session-to-loop/private/discovered-sessions.json")
SUPPORTED_SUFFIXES = {".jsonl"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel_label(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.name


def iter_session_files(paths: list[Path], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")
        if path.is_file():
            if path.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(path)
            continue
        pattern = "**/*.jsonl" if recursive else "*.jsonl"
        files.extend(p for p in path.glob(pattern) if p.is_file())
    return sorted({p.resolve() for p in files})


def build_manifest(paths: list[Path], recursive: bool) -> dict:
    files = []
    for path in iter_session_files(paths, recursive):
        stat = path.stat()
        files.append(
            {
                "path": str(path),
                "label": rel_label(path),
                "size_bytes": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "format": "jsonl",
            }
        )
    return {
        "version": 1,
        "created_at": now_iso(),
        "recursive": recursive,
        "inputs": [str(p) for p in paths],
        "files": files,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Discover Claude Code, Codex, or coding-agent JSONL transcripts. This script only scans "
            "paths passed with --input; it never scans the home directory by default."
        )
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="One or more transcript files or directories to inventory.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search explicit input directories for *.jsonl files.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help=f"Manifest output path. Default: {DEFAULT_OUT}",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest([Path(p) for p in args.input], args.recursive)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Discovered {len(manifest['files'])} transcript file(s): {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"discover_claude_sessions.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
