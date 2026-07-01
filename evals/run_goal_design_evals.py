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
DEFAULT_OUT_ROOT = REPO_ROOT / ".sixloops" / "tmp" / "goal-design-evals"
DESIGNER = REPO_ROOT / "skills" / "sixloops" / "scripts" / "design_goal_loop.py"


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
    if expected.get("adoption_level") and design.get("adoption_level") != expected.get("adoption_level"):
        failures.append(f"expected adoption_level {expected.get('adoption_level')!r}, got {design.get('adoption_level')!r}")

    role_ids = {role.get("id") for role in design.get("subagent_team", {}).get("roles", [])}
    for role in expected.get("roles", []):
        if role not in role_ids:
            failures.append(f"expected role {role!r}, got {sorted(role_ids)}")

    approvals = set(design.get("safety", {}).get("requires_approval_for", []))
    for approval in expected.get("approval_for", []):
        if approval not in approvals:
            failures.append(f"expected approval boundary {approval!r}, got {sorted(approvals)}")

    if expected.get("require_exit_contract"):
        exit_contract = design.get("managed_loop", {}).get("loop_exit_contract", {})
        required_keys = {
            "continue_only_if",
            "done_when",
            "needs_human_when",
            "blocked_when",
            "budget_stopped_when",
            "status_protocol",
        }
        missing = sorted(required_keys - set(exit_contract))
        if missing:
            failures.append(f"missing loop_exit_contract keys: {missing}")
        statuses = set(exit_contract.get("status_protocol", {}))
        required_statuses = {"CONTINUE", "DONE", "NEEDS_HUMAN", "BLOCKED", "BUDGET_STOPPED"}
        missing_statuses = sorted(required_statuses - statuses)
        if missing_statuses:
            failures.append(f"missing exit statuses: {missing_statuses}")
        for list_key in required_keys - {"status_protocol"}:
            if not exit_contract.get(list_key):
                failures.append(f"empty exit contract list: {list_key}")

    if expected.get("require_learning_fields"):
        state_path = design_dir / "STATE.json"
        if not state_path.exists():
            failures.append("missing STATE.json for learning-field check")
        else:
            state = load_json(state_path)
            required_learning = {
                "baseline_friction",
                "post_run_result",
                "saved_corrections",
                "false_positive",
                "human_acceptance",
                "next_adjustment",
                "demotion_recommendation",
            }
            missing_learning = sorted(required_learning - set(state))
            if missing_learning:
                failures.append(f"missing post-adoption learning fields: {missing_learning}")

    if expected.get("require_change_map", True):
        change_map = design.get("change_map")
        if not isinstance(change_map, dict):
            failures.append("missing top-level change_map")
        else:
            required_change_map = {
                "current_x",
                "target_b",
                "user_perception",
                "transformation_thesis",
                "affected_surfaces",
                "regression_plan",
                "rollback_or_compatibility",
                "research_questions",
                "waves",
                "decision_packet_required_when",
            }
            missing_change_map = sorted(required_change_map - set(change_map))
            if missing_change_map:
                failures.append(f"missing change_map keys: {missing_change_map}")
            for list_key in (
                "affected_surfaces",
                "regression_plan",
                "rollback_or_compatibility",
                "research_questions",
                "waves",
                "decision_packet_required_when",
            ):
                if not isinstance(change_map.get(list_key), list) or not change_map.get(list_key):
                    failures.append(f"empty change_map list: {list_key}")
            for key, markers in expected.get("change_map_contains", {}).items():
                marker_list = markers if isinstance(markers, list) else [markers]
                rendered_value = json.dumps(change_map.get(key), ensure_ascii=False)
                for marker in marker_list:
                    if str(marker) not in rendered_value:
                        failures.append(f"change_map.{key} missing model-authored marker {marker!r}")

        managed_change_map = design.get("managed_loop", {}).get("change_map")
        if not isinstance(managed_change_map, dict):
            failures.append("missing managed_loop.change_map")

        state_path = design_dir / "STATE.json"
        if state_path.exists():
            state = load_json(state_path)
            if not isinstance(state.get("change_map"), dict):
                failures.append("missing STATE.json change_map")
            for key in ("active_wave", "decision_packets"):
                if key not in state:
                    failures.append(f"missing STATE.json field {key}")

        rendered_markers = {
            "GOAL.md": ("## Change Map", "## 改造图景"),
            "HANDOFF.md": ("## Change Map", "## 改造图景"),
            "RUN.md": ("Change Map", "改造图景"),
            "VERIFY.md": ("Change Map Verification", "图景验收"),
        }
        for filename, markers in rendered_markers.items():
            path = design_dir / filename
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="ignore")
                if not any(marker in text for marker in markers):
                    failures.append(f"{filename} missing Change Map marker")
                if filename in {"GOAL.md", "HANDOFF.md", "RUN.md"} and not any(
                    marker in text for marker in ("Decision packet triggers", "决策包触发")
                ):
                    failures.append(f"{filename} missing decision packet trigger marker")

    for filename in expected.get("must_include", []):
        if not (design_dir / filename).exists():
            failures.append(f"missing artifact {filename}")

    host_files = ["HOST-START.md", "CODEX-GOAL.md", "CLAUDE-LOOP.md", "host-start-packet.json"]
    for filename in host_files:
        if not (design_dir / filename).exists():
            failures.append(f"missing host packet artifact {filename}")
    host_manifest_path = design_dir / "host-start-packet.json"
    if host_manifest_path.exists():
        host_manifest = load_json(host_manifest_path)
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
    if (design_dir / "HOST-START.md").exists():
        host_start = (design_dir / "HOST-START.md").read_text(encoding="utf-8", errors="ignore")
        for marker in ("/goal", "/loop", "CODEX-GOAL.md", "CLAUDE-LOOP.md"):
            if marker not in host_start:
                failures.append(f"HOST-START.md missing {marker!r}")
    if (design_dir / "CODEX-GOAL.md").exists():
        codex_goal = (design_dir / "CODEX-GOAL.md").read_text(encoding="utf-8", errors="ignore")
        for marker in ("/goal", "CONTINUE", "DONE", "BLOCKED"):
            if marker not in codex_goal:
                failures.append(f"CODEX-GOAL.md missing {marker!r}")
        if "Autocorrection Strategy" not in codex_goal and "自动纠正策略" not in codex_goal:
            failures.append("CODEX-GOAL.md missing autocorrection strategy")
    if (design_dir / "CLAUDE-LOOP.md").exists():
        claude_loop = (design_dir / "CLAUDE-LOOP.md").read_text(encoding="utf-8", errors="ignore")
        for marker in ("/loop", "CONTINUE", "DONE", "BLOCKED"):
            if marker not in claude_loop:
                failures.append(f"CLAUDE-LOOP.md missing {marker!r}")

    if expected.get("require_handoff_exit_contract"):
        handoff = (design_dir / "HANDOFF.md").read_text(encoding="utf-8", errors="ignore")
        goal = (design_dir / "GOAL.md").read_text(encoding="utf-8", errors="ignore")
        for label, text in (("HANDOFF.md", handoff), ("GOAL.md", goal)):
            if "## Exit Contract" not in text and "## 退出协议" not in text:
                failures.append(f"{label} missing ## Exit Contract")
            if not any(marker in text for marker in ("Learning Check", "First Run Retro", "复盘记录", "首轮复盘")):
                failures.append(f"{label} missing learning check or first run retro")

    if expected.get("require_rationale"):
        for key in ("why_this_loop", "why_not_smaller", "why_not_more_autonomous", "fit_summary"):
            if not design.get(key):
                failures.append(f"missing rationale field {key}")
        goal = (design_dir / "GOAL.md").read_text(encoding="utf-8", errors="ignore")
        markers = [
            ("## Why This Loop", "## 为什么是这个 loop"),
            ("Why this loop:", "为什么值得跑："),
            ("Why not smaller:", "为什么不只是更小机制："),
            ("Why not more autonomous:", "为什么不更自动化："),
        ]
        for marker_options in markers:
            if not any(marker in goal for marker in marker_options):
                failures.append(f"GOAL.md missing rationale marker {marker_options[0]!r}")

    if expected.get("forbid_done_blocker"):
        done_text = " ".join(design.get("managed_loop", {}).get("loop_exit_contract", {}).get("done_when", [])).lower()
        if "or a blocker" in done_text or "blocker is recorded" in done_text:
            failures.append("DONE contract treats blocker recording as success")

    rendered = all_text(design_dir)
    if "{{" in rendered or "}}" in rendered:
        failures.append("unrendered template placeholder found in goal-design artifacts")
    if "subagent" not in rendered.lower() and expected.get("team_mode") == "subagent-team":
        failures.append("expected subagent-team artifacts to mention subagent behavior")
    for status in ("CONTINUE", "DONE", "NEEDS_HUMAN", "BLOCKED", "BUDGET_STOPPED"):
        if status not in rendered:
            failures.append(f"expected rendered artifacts to include status {status}")

    return failures


def run_case(case: dict, out_root: Path, keep_going: bool) -> tuple[bool, list[str]]:
    case_dir = out_root / str(case["id"])
    clean_case_dir(case_dir, out_root)
    expected = case.get("expected", {})
    model_design = {
        key: value
        for key, value in {
            "domain": expected.get("domain"),
            "team_mode": expected.get("team_mode"),
            "level": expected.get("adoption_level"),
        }.items()
        if value
    }
    if isinstance(case.get("model_design"), dict):
        model_design.update(case["model_design"])
    model_design_path = case_dir / "model-design.json"
    model_design_path.write_text(json.dumps(model_design, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        "auto",
        "--model-design-file",
        str(model_design_path),
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
