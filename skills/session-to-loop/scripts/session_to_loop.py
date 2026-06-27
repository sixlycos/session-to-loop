#!/usr/bin/env python3
"""One-command local pipeline for SixLoops."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SEMANTIC_PROMPT = SKILL_DIR / "references" / "semantic-analysis-prompt.md"


def run_step(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], check=True)


def private_path(out_root: Path, name: str) -> Path:
    return out_root / "private" / name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the local guardrail pipeline. Without --approve or --scope, this stops after "
            "creating a scope proposal so the host agent can ask the user once."
        )
    )
    parser.add_argument("--input", nargs="+", required=True, help="Explicit transcript file(s) or directory path(s).")
    parser.add_argument("--out-root", default=".session-to-loop", help="Output root. Default: .session-to-loop")
    parser.add_argument("--recursive", action="store_true", help="Recursively search explicit input directories.")
    parser.add_argument("--approve", action="store_true", help="Approve generated scope. Use only after user confirmation or for evals.")
    parser.add_argument("--scope", default=None, help="Existing approved analysis-scope.json.")
    parser.add_argument("--roles", nargs="+", default=["user", "tool"], help="Roles allowed for analysis. Default: user tool")
    parser.add_argument("--source-pointers-only", action="store_true", help="Disable redacted snippets in packets and artifacts.")
    parser.add_argument("--semantic-candidates", default=None, help="AI-generated semantic candidates JSON to guard and render.")
    parser.add_argument("--rule-fallback", action="store_true", help="Run deterministic keyword fallback for offline evals.")
    parser.add_argument("--max-packet-chars", type=int, default=1200, help="Maximum chars per analysis packet.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_root = Path(args.out_root)
    private = out_root / "private"
    public = out_root / "public"
    private.mkdir(parents=True, exist_ok=True)

    manifest = private_path(out_root, "discovered-sessions.json")
    scope = Path(args.scope) if args.scope else private_path(out_root, "analysis-scope.json")
    redacted_dir = private / "redacted"
    redacted_index = private_path(out_root, "redacted-index.json")
    packets = private_path(out_root, "analysis-packets.jsonl")
    packet_index = private_path(out_root, "analysis-packets-index.json")
    signals = private_path(out_root, "signals.json")
    candidates = private_path(out_root, "candidates.json")

    discover_cmd = [str(SCRIPT_DIR / "discover_claude_sessions.py"), "--input", *args.input, "--out", str(manifest)]
    if args.recursive:
        discover_cmd.append("--recursive")
    run_step(discover_cmd)

    if not args.scope:
        scope_cmd = [str(SCRIPT_DIR / "prepare_analysis_scope.py"), "--manifest", str(manifest), "--roles", *args.roles, "--out", str(scope)]
        if args.approve:
            scope_cmd.append("--approve")
        if args.source_pointers_only:
            scope_cmd.append("--source-pointers-only")
        run_step(scope_cmd)

    scope_data = json.loads(scope.read_text(encoding="utf-8"))
    if not scope_data.get("approved"):
        print(f"Scope proposal created: {scope}")
        print("Ask the user to confirm files, roles, snippet policy, and output visibility, then rerun with --approve or --scope.")
        return 0

    run_step(
        [
            str(SCRIPT_DIR / "redact_transcripts.py"),
            "--manifest",
            str(manifest),
            "--scope",
            str(scope),
            "--out-dir",
            str(redacted_dir),
            "--index",
            str(redacted_index),
        ]
    )
    run_step(
        [
            str(SCRIPT_DIR / "build_analysis_packets.py"),
            "--redacted-index",
            str(redacted_index),
            "--out",
            str(packets),
            "--packet-index",
            str(packet_index),
            "--max-chars",
            str(args.max_packet_chars),
        ]
    )

    if args.semantic_candidates:
        run_step(
            [
                str(SCRIPT_DIR / "apply_guardrails.py"),
                "--semantic-candidates",
                args.semantic_candidates,
                "--packet-index",
                str(packet_index),
                "--out",
                str(candidates),
            ]
        )
        run_step([str(SCRIPT_DIR / "render_artifacts.py"), "--candidates", str(candidates), "--out-dir", str(public)])
        print(f"Rendered semantic analysis artifacts: {public}")
        return 0

    if args.rule_fallback:
        run_step([str(SCRIPT_DIR / "extract_signals.py"), "--redacted-index", str(redacted_index), "--out", str(signals)])
        run_step([str(SCRIPT_DIR / "score_candidates.py"), "--signals", str(signals), "--out", str(candidates)])
        run_step([str(SCRIPT_DIR / "render_artifacts.py"), "--candidates", str(candidates), "--out-dir", str(public)])
        print(f"Rendered fallback analysis artifacts: {public}")
        return 0

    print(f"Analysis packets ready: {packets}")
    print(f"Packet index: {packet_index}")
    print(f"Semantic prompt: {SEMANTIC_PROMPT}")
    print("Ask the host AI to read the prompt and packets, write semantic-candidates.json, then rerun with --semantic-candidates.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
