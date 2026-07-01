#!/usr/bin/env python3
"""Run minimal SixLoops adoption packet evals."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ADOPTER = REPO_ROOT / "skills" / "sixloops" / "scripts" / "adopt_candidate.py"
OUT_ROOT = REPO_ROOT / ".sixloops" / "tmp" / "adopt-candidate-evals"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    cmd = [
        sys.executable,
        str(ADOPTER),
        "--candidates",
        str(REPO_ROOT / "evals" / "semantic-candidates" / "repeated-ci-failure.json"),
        "--candidate-id",
        "ci-babysitter",
        "--mode",
        "read-only",
        "--out-dir",
        str(OUT_ROOT),
        "--overwrite",
    ]
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.returncode:
        print(result.stderr.strip() or result.stdout.strip() or "adopt_candidate.py failed")
        return 1

    packet = OUT_ROOT / "ci-babysitter"
    state = load_json(packet / "STATE.json")
    failures: list[str] = []
    if not isinstance(state.get("change_map"), dict):
        failures.append("STATE.json missing change_map")
    for key in ("active_wave", "decision_packets"):
        if key not in state:
            failures.append(f"STATE.json missing {key}")

    continue_text = "\n".join(state["loop_exit_contract"]["continue_only_if"])
    for marker in (
        "The Change Map can be updated",
        "Risk stays below the approved mode and explicit return points",
    ):
        if marker not in continue_text:
            failures.append(f"continue_only_if missing {marker!r}")

    rendered = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in packet.glob("*.md"))
    for marker in ("Change Map", "Decision packet triggers"):
        if marker not in rendered:
            failures.append(f"rendered adoption packet missing {marker!r}")
    if "{{" in rendered or "}}" in rendered:
        failures.append("unrendered template placeholder found")

    for filename in ("HOST-START.md", "CODEX-GOAL.md", "CLAUDE-LOOP.md", "host-start-packet.json"):
        if not (packet / filename).exists():
            failures.append(f"missing host packet artifact {filename}")
    if (packet / "host-start-packet.json").exists():
        host_manifest = load_json(packet / "host-start-packet.json")
        targets = host_manifest.get("targets", []) if isinstance(host_manifest, dict) else []
        host_entries = {(target.get("host"), target.get("entrypoint")) for target in targets if isinstance(target, dict)}
        if ("codex", "/goal") not in host_entries:
            failures.append("host-start-packet.json missing codex /goal target")
        if ("claude", "/loop") not in host_entries:
            failures.append("host-start-packet.json missing claude /loop target")
        governance = host_manifest.get("governance", {}) if isinstance(host_manifest, dict) else {}
        for key in ("owner", "review_cadence", "maturity_tier", "lifecycle_stage", "rollback_boundary", "output_contract"):
            if not governance.get(key):
                failures.append(f"host-start-packet.json missing governance.{key}")
    host_rendered = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in (packet / "HOST-START.md", packet / "CODEX-GOAL.md", packet / "CLAUDE-LOOP.md")
        if path.exists()
    )
    for marker in ("/goal", "/loop", "Autocorrection Strategy", "Exit Contract"):
        if marker not in host_rendered:
            failures.append(f"host packets missing {marker!r}")

    for failure in failures:
        print(f"FAIL {failure}")
    if failures:
        return 1
    print("PASS adopt-candidate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
