#!/usr/bin/env python3
"""Run deterministic SixLoops goal-design evals."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALS = REPO_ROOT / "evals" / "goal_design_evals.json"
DEFAULT_OUT_ROOT = REPO_ROOT / ".session-to-loop" / "tmp" / "goal-design-evals"
DESIGNER = REPO_ROOT / "skills" / "session-to-loop" / "scripts" / "design_goal_loop.py"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_safe_child(path: Path, root: Path) -> None:
    resolved = path.resolve()
    resolved_root = root.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"Refusing to clean path outside eval root: {path}")


def clean_case_dir(path: Path, root: Path) -> None:
    ensure_safe_child(path, root)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def find_design_dir(case_dir: Path) -> Path | None:
    design_dirs = [path for path in case_dir.iterdir() if path.is_dir()]
    if len(design_dirs) != 1:
        return None
    return design_dirs[0]


def all_text(path: Path) -> str:
    chunks = []
    for item in path.rglob("*"):
        if item.is_file():
            chunks.append(item.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def assert_case(case: dict, case_dir: Path) -> list[str]:
    failures: list[str] = []
    expected = case.get("expected", {})
    design_dir = find_design_dir(case_dir)
    if design_dir is None:
        return [f"expected exactly one design directory under {case_dir}"]

    design_path = design_dir / "goal-loop-design.json"
    if not design_path.exists():
        return [f"missing goal-loop-design.json in {design_dir}"]
    design = load_json(design_path)

    if design.get("domain") != expected.get("domain"):
        failures.append(f"expected domain {expected.get('domain')!r}, got {design.get('domain')!r}")
    if design.get("team_mode") != expected.get("team_mode"):
        failures.append(f"expected team_mode {expected.get('team_mode')!r}, got {design.get('team_mode')!r}")

    role_ids = {role.get("id") for role in design.get("subagent_team", {}).get("roles", [])}
    for role in expected.get("roles", []):
        if role not in role_ids:
            failures.append(f"expected role {role!r}, got {sorted(role_ids)}")

    approvals = set(design.get("safety", {}).get("requires_approval_for", []))
    for approval in expected.get("approval_for", []):
        if approval not in approvals:
            failures.append(f"expected approval boundary {approval!r}, got {sorted(approvals)}")

    for filename in expected.get("must_include", []):
        if not (design_dir / filename).exists():
            failures.append(f"missing artifact {filename}")

    rendered = all_text(design_dir)
    if "{{" in rendered or "}}" in rendered:
        failures.append("unrendered template placeholder found in goal-design artifacts")
    if "subagent" not in rendered.lower() and expected.get("team_mode") == "subagent-team":
        failures.append("expected subagent-team artifacts to mention subagent behavior")

    return failures


def run_case(case: dict, out_root: Path, keep_going: bool) -> tuple[bool, list[str]]:
    case_dir = out_root / str(case["id"])
    clean_case_dir(case_dir, out_root)
    cmd = [
        sys.executable,
        str(DESIGNER),
        "--goal",
        str(case["goal"]),
        "--domain",
        "auto",
        "--team-mode",
        "auto",
        "--level",
        "goal-loop",
        "--out-dir",
        str(case_dir),
        "--overwrite",
    ]
    result = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        details = [f"designer exited {result.returncode}"]
        if result.stdout.strip():
            details.append(result.stdout.strip())
        if result.stderr.strip():
            details.append(result.stderr.strip())
        if not keep_going:
            return False, details
        return False, details
    failures = assert_case(case, case_dir)
    return not failures, failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SixLoops goal-design evals.")
    parser.add_argument("--evals", default=str(DEFAULT_EVALS), help=f"Eval spec JSON. Default: {DEFAULT_EVALS}")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help=f"Output root. Default: {DEFAULT_OUT_ROOT}")
    parser.add_argument("--case", action="append", default=[], help="Run only this case id. Can be repeated.")
    parser.add_argument("--keep-going", action="store_true", help="Run all selected cases even after a failure.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evals = load_json(Path(args.evals))
    if not isinstance(evals, list):
        raise ValueError("goal-design eval spec must be a list.")
    selected = [case for case in evals if not args.case or case.get("id") in set(args.case)]
    if not selected:
        raise ValueError("No goal-design eval cases selected.")

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    failed = 0
    ran = 0
    for case in selected:
        ran += 1
        ok, details = run_case(case, out_root, args.keep_going)
        if ok:
            print(f"PASS {case['id']}")
            continue
        failed += 1
        print(f"FAIL {case['id']}")
        for detail in details:
            print(f"  - {detail}")
        if not args.keep_going:
            break

    print(f"{ran - failed}/{ran} goal-design eval(s) passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"run_goal_design_evals.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
