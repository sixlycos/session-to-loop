#!/usr/bin/env python3
"""Create a concrete adoption packet for a confirmed SixLoops candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from loop_contract import normalize_exit_contract
from mode_policy import INTERNAL_TO_MODE, level_to_mode, mode_to_level


DEFAULT_CANDIDATES = Path(".session-to-loop/private/candidates.json")
DEFAULT_OUT_DIR = Path(".session-to-loop/adopted")
ALLOWED_LEVELS = set(INTERNAL_TO_MODE)


LEVEL_POLICIES = {
    "read-only": "Read evidence and produce recommendations only. Do not edit project files.",
    "goal-loop": "Run as a delegated goal loop. Ask before edits unless the user explicitly grants edit scope.",
    "isolated-draft": "Use an isolated branch or worktree for reversible draft changes. Do not push or merge.",
    "verified-pr-draft": "Prepare a verified patch or PR draft when checks pass. Do not push, merge, or deploy without approval.",
    "scheduled-readonly": "Use only as a scheduled read-only report until separate automation setup is approved.",
    "scheduled-draft": "Use only after separate scheduling, isolation, notification, and rollback boundaries are approved.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-") or "candidate"


def strings(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def bullet(items: list[str]) -> str:
    if not items:
        return "- None."
    return "\n".join(f"- {item}" for item in items)


def numbered(items: list[str]) -> str:
    if not items:
        return "1. No repeatable steps recorded."
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def load_candidates(path: Path) -> tuple[dict, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        candidates = data
        data = {"candidates": candidates}
    else:
        candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("candidates JSON must contain a candidates list.")
    return data, candidates


def find_candidate(candidates: list[dict], candidate_id: str) -> dict:
    for candidate in candidates:
        if str(candidate.get("id")) == candidate_id:
            return candidate
    available = ", ".join(str(item.get("id")) for item in candidates)
    raise ValueError(f"Candidate {candidate_id!r} not found. Available: {available or 'none'}")


def objective_hash(candidate: dict) -> str:
    managed_loop = candidate.get("managed_loop") if isinstance(candidate.get("managed_loop"), dict) else {}
    contract = managed_loop.get("completion_contract") if isinstance(managed_loop.get("completion_contract"), dict) else {}
    payload = {
        "id": candidate.get("id"),
        "objective": managed_loop.get("objective") or candidate.get("summary"),
        "success_criteria": strings(contract.get("success_criteria") or candidate.get("verification")),
        "stop_conditions": strings(candidate.get("stop_conditions")),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def candidate_contract(candidate: dict) -> tuple[dict, dict]:
    managed_loop = candidate.get("managed_loop") if isinstance(candidate.get("managed_loop"), dict) else {}
    contract = managed_loop.get("completion_contract") if isinstance(managed_loop.get("completion_contract"), dict) else {}
    return managed_loop, contract


def exit_contract(candidate: dict) -> dict:
    managed_loop, contract = candidate_contract(candidate)
    safety = candidate.get("safety") if isinstance(candidate.get("safety"), dict) else {}
    return normalize_exit_contract(
        managed_loop.get("loop_exit_contract"),
        success_criteria=strings(contract.get("success_criteria") or candidate.get("verification")),
        reject_conditions=strings(contract.get("reject_conditions") or candidate.get("stop_conditions")),
        approval_boundary=strings(safety.get("requires_approval_for")),
        max_items=managed_loop.get("max_items_per_cycle", 3),
        max_iterations=managed_loop.get("max_iterations_per_run", 8),
    )


def build_state(candidate: dict, level: str, artifact_dir: Path) -> dict:
    managed_loop, contract = candidate_contract(candidate)
    safety = candidate.get("safety") if isinstance(candidate.get("safety"), dict) else {}
    return {
        "version": 1,
        "loop_id": candidate.get("id"),
        "name": candidate.get("name", candidate.get("id")),
        "status": "pending",
        "adoption_level": level,
        "created_at": now_iso(),
        "objective_hash": objective_hash(candidate),
        "objective": managed_loop.get("objective") or candidate.get("summary"),
        "heartbeat": managed_loop.get("heartbeat", "goal"),
        "state_schema": managed_loop.get("state_schema", {}),
        "success_criteria": strings(contract.get("success_criteria") or candidate.get("verification")),
        "reject_conditions": strings(contract.get("reject_conditions") or candidate.get("stop_conditions")),
        "loop_exit_contract": exit_contract(candidate),
        "approval_boundary": strings(safety.get("requires_approval_for")),
        "budget_caps": strings(safety.get("budget_caps")),
        "items": [],
        "attempts": [],
        "failure_signatures": [],
        "progress_metrics": [],
        "human_queue": [],
        "next_cursor": None,
        "last_status": None,
        "last_exit_status": None,
        "status_history": [],
        "baseline_friction": None,
        "post_run_result": None,
        "saved_corrections": [],
        "false_positive": [],
        "human_acceptance": None,
        "next_adjustment": None,
        "demotion_recommendation": None,
        "artifact_dir": str(artifact_dir),
    }


def render_goal(candidate: dict, level: str) -> str:
    managed_loop, contract = candidate_contract(candidate)
    exits = exit_contract(candidate)
    candidate_id = str(candidate.get("id"))
    state_file = "STATE.json"
    suggested_state = managed_loop.get("state_file", f".session-to-loop/state/{candidate_id}.json")
    success = strings(contract.get("success_criteria") or candidate.get("verification"))
    verifiers = strings(contract.get("verifier_commands"))
    reject_conditions = strings(contract.get("reject_conditions") or candidate.get("stop_conditions"))
    approval_boundary = strings((candidate.get("safety") or {}).get("requires_approval_for"))
    cycle_steps = strings(managed_loop.get("cycle_steps") or candidate.get("actions"))
    selection_policy = strings(managed_loop.get("selection_policy"))
    deliverables = strings(managed_loop.get("deliverables"))
    max_items = managed_loop.get("max_items_per_cycle", 3)
    max_iterations = managed_loop.get("max_iterations_per_run", 8)
    mode = level_to_mode(level)
    return f"""# {candidate.get("name", candidate_id)} Run Packet

Use this after the user starts `{candidate_id}` as `{mode}`.

## Objective

{managed_loop.get("objective") or candidate.get("summary", "Run the loop.")}

## Start Mode

`{mode}` (`{level}` internally): {LEVEL_POLICIES[level]}

## State

- Active state file for this adoption packet: `{state_file}`
- Suggested project state path: `{suggested_state}`
- Read state before every cycle and update it before stopping.

## Acceptance Checks

{bullet(success)}

## Observe-Decide-Act-Verify Cycle

{numbered(cycle_steps)}

## Selection Policy

{bullet(selection_policy or [f"Choose at most {max_items} high-value item(s) per cycle."])}

## Verification

{bullet(verifiers or strings(candidate.get("verification")) or ["Run the focused verifier named by the project."])}

## Stop Conditions

{bullet(reject_conditions)}

Also stop after `{max_iterations}` iteration(s), no progress across two iterations, or any review boundary.

## Exit Contract

Continue only if:

{bullet(exits["continue_only_if"])}

Return `DONE` when:

{bullet(exits["done_when"])}

Return for review when:

{bullet(exits["needs_human_when"])}

Return `BLOCKED` when:

{bullet(exits["blocked_when"])}

Return `BUDGET_STOPPED` when:

{bullet(exits["budget_stopped_when"])}

## Human Gate

{bullet(approval_boundary or ["Ask before expanding scope, making irreversible changes, or changing product/release/data boundaries."])}

## Deliverables

{bullet(deliverables or ["Status summary", "Updated STATE.json", "Verifier evidence or blocker reason"])}

## Status Protocol

Return one status at the end:

- `DONE`: all success criteria passed with verifier evidence.
- `CONTINUE`: progress changed and budget remains.
- `BLOCKED`: repeated failure, no progress, missing input, or uncertain verifier.
- `NEEDS_HUMAN`: return for review because approval or human judgment is required.
- `BUDGET_STOPPED`: item, iteration, time, or token cap was reached.

## First Run Retro

Before the next run, update `STATE.json` with whether this loop reduced repeated human correction,
created false positives, required too much human judgment, should be downgraded to a skill/checklist,
or has enough accepted output to keep its current autonomy level.
"""


def render_handoff(candidate: dict, level: str, artifact_dir: Path) -> str:
    managed_loop, _ = candidate_contract(candidate)
    exits = exit_contract(candidate)
    candidate_id = str(candidate.get("id"))
    mode = level_to_mode(level)
    return f"""# {candidate.get("name", candidate_id)} Run Handoff

This packet was generated after starting `{candidate_id}` as `{mode}`.

## What To Run

Paste or attach `GOAL.md` as the delegated goal. Keep `STATE.json` beside it and update it before stopping.

## Why This Exists

{candidate.get("summary", "No summary recorded.")}

## Trigger

{bullet(strings(managed_loop.get("cadence_or_trigger") or candidate.get("trigger")))}

## Exit Contract

Continue only if:

{bullet(exits["continue_only_if"])}

Return `DONE` when:

{bullet(exits["done_when"])}

Return for review when:

{bullet(exits["needs_human_when"])}

Return `BLOCKED` when:

{bullet(exits["blocked_when"])}

Return `BUDGET_STOPPED` when:

{bullet(exits["budget_stopped_when"])}

## Learning Check

After the first run, record saved corrections, false positives, human acceptance, next adjustment,
and any demotion recommendation in `STATE.json`.

## Files

- `{artifact_dir / "GOAL.md"}`
- `{artifact_dir / "STATE.json"}`
- `{artifact_dir / "AGENTS-snippet.md"}`
- `{artifact_dir / "manifest.json"}`
"""


def render_agents_snippet(candidate: dict, level: str) -> str:
    managed_loop, contract = candidate_contract(candidate)
    safety = candidate.get("safety") if isinstance(candidate.get("safety"), dict) else {}
    candidate_id = str(candidate.get("id"))
    verifier = strings(contract.get("verifier_commands") or candidate.get("verification"))
    mode = level_to_mode(level)
    return f"""# Draft AGENTS.md Snippet: {candidate.get("name", candidate_id)}

This is a draft rule. Do not install it automatically; review it before copying into project instructions.

When `{candidate_id}` is triggered:

- Run mode: `{mode}` (`{level}` internally).
- Objective: {managed_loop.get("objective") or candidate.get("summary", "No objective recorded.")}
- Read and update the loop state before stopping.
- Handle at most {managed_loop.get("max_items_per_cycle", 3)} item(s) per cycle.
- Stop after {managed_loop.get("max_iterations_per_run", 8)} iteration(s), repeated failure, no progress, or a review boundary.
- Verify with: {", ".join(verifier) if verifier else "the focused project verifier"}.
- Ask before: {", ".join(strings(safety.get("requires_approval_for"))) or "irreversible, release, data, or product-boundary changes"}.
"""


def write_text(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Pass --overwrite to replace it.")
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, content: dict, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Pass --overwrite to replace it.")
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create goal-ready adoption artifacts for one confirmed candidate.")
    parser.add_argument("--candidates", default=str(DEFAULT_CANDIDATES), help=f"Candidates JSON. Default: {DEFAULT_CANDIDATES}")
    parser.add_argument("--candidate-id", required=True, help="Candidate id to adopt.")
    parser.add_argument("--level", help="Internal level or user-facing start mode confirmed by the user.")
    parser.add_argument("--mode", help="User-facing start mode. Overrides --level.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help=f"Adoption output directory. Default: {DEFAULT_OUT_DIR}")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing adoption packet for the same candidate.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_mode = args.mode or args.level
    if not raw_mode:
        raise ValueError("Pass --mode <start-mode> or --level <internal-level>.")
    level = mode_to_level(raw_mode)
    data, candidates = load_candidates(Path(args.candidates))
    candidate = find_candidate(candidates, args.candidate_id)
    if candidate.get("decision") == "reject":
        raise ValueError("Rejected candidates cannot be adopted. Choose a non-rejected candidate or rerun analysis.")

    root = Path(args.out_dir)
    artifact_dir = root / slug(args.candidate_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    state_path = artifact_dir / "STATE.json"
    goal_path = artifact_dir / "GOAL.md"
    handoff_path = artifact_dir / "HANDOFF.md"
    snippet_path = artifact_dir / "AGENTS-snippet.md"
    manifest_path = artifact_dir / "manifest.json"

    state = build_state(candidate, level, artifact_dir)
    manifest = {
        "version": 1,
        "created_at": now_iso(),
        "candidate_id": args.candidate_id,
        "candidate_name": candidate.get("name", args.candidate_id),
        "decision": candidate.get("decision"),
        "mechanisms": candidate.get("mechanisms", []),
        "adoption_level": level,
        "source_candidates": str(Path(args.candidates)),
        "source_analysis_model": data.get("analysis_model"),
        "files": {
            "state": str(state_path),
            "goal": str(goal_path),
            "handoff": str(handoff_path),
            "agents_snippet": str(snippet_path),
        },
    }

    write_json(state_path, state, args.overwrite)
    write_text(goal_path, render_goal(candidate, level), args.overwrite)
    write_text(handoff_path, render_handoff(candidate, level, artifact_dir), args.overwrite)
    write_text(snippet_path, render_agents_snippet(candidate, level), args.overwrite)
    write_json(manifest_path, manifest, args.overwrite)

    print(f"Created adoption packet: {artifact_dir}")
    print(f"- {goal_path}")
    print(f"- {state_path}")
    print(f"- {handoff_path}")
    print(f"- {snippet_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"adopt_candidate.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
