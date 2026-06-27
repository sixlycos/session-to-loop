#!/usr/bin/env python3
"""Render redacted candidate artifacts from scored pipeline output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_CANDIDATES = Path(".session-to-loop/private/candidates.json")
DEFAULT_OUT_DIR = Path(".session-to-loop/public")
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def load_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def fill(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def bullet(items: list[str]) -> str:
    if not items:
        return "None."
    return "\n- ".join(items)


def bullet_block(items: list[str]) -> str:
    if not items:
        return "None."
    return "- " + "\n- ".join(items)


def first(items: list[str], default: str = "None.") -> str:
    return items[0] if items else default


def bool_label(value: bool) -> str:
    return "yes" if value else "no"


def render_trace(candidate: dict) -> str:
    trace = candidate.get("decision_trace", {})
    loop_gate = candidate.get("loop_eligibility", {})
    criteria = loop_gate.get("criteria", {})
    missing = loop_gate.get("missing", [])
    role_counts = trace.get("role_counts", {})
    lines = [
        "## Decision Trace",
        "",
        f"Analysis basis: {trace.get('analysis_basis', 'Not recorded.')}",
        "",
        f"Primary evidence role: `{trace.get('primary_role', 'unknown')}`",
        "",
        "Role counts:",
        "",
        f"- user: {role_counts.get('user', 0)}",
        f"- tool: {role_counts.get('tool', 0)}",
        f"- assistant: {role_counts.get('assistant', 0)}",
        f"- unknown: {role_counts.get('unknown', 0)}",
        "",
        f"Intents: {', '.join(trace.get('intents', [])) or 'None.'}",
        "",
        "Loop eligibility:",
        "",
        f"- eligible: {bool_label(loop_gate.get('eligible', False))}",
    ]
    for key, value in criteria.items():
        lines.append(f"- {key}: {bool_label(bool(value))}")
    lines.extend(["", f"Missing loop criteria: {', '.join(missing) if missing else 'None.'}"])
    downgrades = trace.get("downgrades", [])
    lines.extend(["", f"Hard downgrades: {' '.join(downgrades) if downgrades else 'None.'}", ""])
    return "\n".join(lines)


def candidate_card(candidate: dict) -> str:
    evidence = candidate.get("evidence", [{}])
    first_evidence = evidence[0] if evidence else {}
    managed_loop = candidate.get("managed_loop", {})
    values = {
        "name": candidate["name"],
        "id": candidate["id"],
        "decision": candidate["decision"],
        "confidence": candidate["confidence"],
        "mechanism": ", ".join(candidate.get("mechanisms") or [candidate.get("mechanism", "none")]),
        "summary": candidate["summary"],
        "source": first_evidence.get("source", "n/a"),
        "signal_kind": f"{first_evidence.get('kind', 'n/a')} / {first_evidence.get('role', 'unknown')} / {first_evidence.get('intent', 'unknown')}",
        "snippet": first_evidence.get("snippet", "No quote needed."),
        "trigger": bullet(candidate.get("trigger", [])),
        "artifact": bullet(candidate.get("artifacts", [])),
        "goal": candidate["summary"],
        "input": bullet(candidate.get("inputs", [])),
        "action": bullet(candidate.get("actions", [])),
        "verification": bullet(candidate.get("verification", [])),
        "stop_condition": bullet(candidate.get("stop_conditions", [])),
        "managed_objective": managed_loop.get("objective", candidate["summary"]),
        "managed_trigger": bullet_block(managed_loop.get("cadence_or_trigger", candidate.get("trigger", []))),
        "managed_state_file": managed_loop.get("state_file", f".session-to-loop/state/{candidate['id']}.json"),
        "managed_cycle_steps": bullet_block(managed_loop.get("cycle_steps", candidate.get("actions", []))),
        "managed_selection_policy": bullet_block(managed_loop.get("selection_policy", [])),
        "managed_max_items_per_cycle": str(managed_loop.get("max_items_per_cycle", 3)),
        "managed_change_policy": managed_loop.get("change_policy", "Only make low-risk changes with direct evidence. Use an isolated branch or worktree when modifying files."),
        "managed_deliverables": bullet_block(managed_loop.get("deliverables", [])),
        "managed_resume_policy": managed_loop.get("resume_policy", "Read the state file first and continue unresolved items before starting new work."),
        "managed_failure_policy": managed_loop.get("failure_policy", "Record the blocker and stop when verification fails or human judgment is required."),
        "autonomy_level": candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        "approval_required_action": bullet(candidate.get("safety", {}).get("requires_approval_for", [])),
        "downgrade_notes": candidate.get("downgrade_notes", "None."),
    }
    return fill(load_template("loop-card.md"), values) + "\n" + render_trace(candidate)


def claude_loop(candidate: dict) -> str:
    managed_loop = candidate.get("managed_loop", {})
    values = {
        "loop_name": candidate["name"],
        "goal": managed_loop.get("objective", candidate["summary"]),
        "cadence_or_trigger": bullet_block(managed_loop.get("cadence_or_trigger", candidate.get("trigger", []))),
        "context_source": bullet_block(candidate.get("inputs", [])),
        "state_file": managed_loop.get("state_file", f".session-to-loop/state/{candidate['id']}.json"),
        "cycle_steps": bullet_block(managed_loop.get("cycle_steps", candidate.get("actions", []))),
        "selection_policy": bullet_block(managed_loop.get("selection_policy", [])),
        "max_items_per_cycle": str(managed_loop.get("max_items_per_cycle", 3)),
        "change_policy": managed_loop.get("change_policy", "Only make low-risk changes with direct evidence. Use an isolated branch or worktree when modifying files."),
        "deliverables": bullet_block(managed_loop.get("deliverables", [])),
        "verification_signal": bullet_block(candidate.get("verification", [])),
        "resume_policy": managed_loop.get("resume_policy", "Read the state file first and continue unresolved items before starting new work."),
        "failure_policy": managed_loop.get("failure_policy", "Record the blocker and stop when verification fails or human judgment is required."),
        "stop_condition": bullet_block(candidate.get("stop_conditions", [])),
        "autonomy_level": candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        "approval_required_action": bullet_block(candidate.get("safety", {}).get("requires_approval_for", [])),
    }
    return fill(load_template("claude-loop.md"), values)


def generated_skill(candidate: dict) -> str:
    skill_id = slug(candidate["id"])
    values = {
        "skill_name": skill_id,
        "skill_description": candidate["summary"],
        "display_name": candidate["name"],
        "overview": candidate["summary"],
        "step_1": first(candidate.get("actions", []), "Inspect evidence."),
        "step_2": candidate.get("actions", ["", "Propose the smallest safe action."])[1]
        if len(candidate.get("actions", [])) > 1
        else "Propose the smallest safe action.",
        "step_3": candidate.get("actions", ["", "", "Verify and report."])[2]
        if len(candidate.get("actions", [])) > 2
        else "Verify and report.",
        "input": bullet(candidate.get("inputs", [])),
        "verification": bullet(candidate.get("verification", [])),
        "safety_rule": bullet(candidate.get("safety", {}).get("requires_approval_for", [])),
    }
    return fill(load_template("generated-skill.md"), values)


def playbook(data: dict, out_dir: Path, rendered_paths: list[str]) -> str:
    candidates = data.get("candidates", [])
    summary = f"Found {len(candidates)} candidate(s) from redacted local transcript evidence."
    table_rows = "\n".join(
        f"| {item['name']} | {', '.join(item.get('mechanisms') or [item.get('mechanism', 'none')])} | "
        f"{item['decision']} | {item['confidence']} |"
        for item in candidates
    )
    by_mechanism = {
        "rule": [],
        "skill": [],
        "hook": [],
        "loop": [],
        "approval": [],
        "rejected": [],
    }
    for item in candidates:
        mechanisms = item.get("mechanisms", [])
        line = f"- `{item['id']}`: {item['summary']}"
        if "rule" in mechanisms:
            by_mechanism["rule"].append(line)
        if "skill" in mechanisms:
            by_mechanism["skill"].append(line)
        if "hook" in mechanisms:
            by_mechanism["hook"].append(line)
        if "loop" in mechanisms:
            by_mechanism["loop"].append(line)
        if "checklist" in mechanisms or "approval-gate" in mechanisms:
            by_mechanism["approval"].append(line)
        if item["decision"] == "reject":
            by_mechanism["rejected"].append(f"- `{item['id']}`: {item['downgrade_notes']}")

    template = load_template("loop-playbook.md").replace(
        "| {{candidate}} | {{mechanism}} | {{decision}} | {{confidence}} |",
        table_rows or "| None | none | reject | low |",
    )
    values = {
        "project": Path.cwd().name,
        "analysis_window": "explicit local inputs",
        "transcript_source_summary": f"{data.get('source', {}).get('transcript_files', 0)} file(s), "
        f"{data.get('source', {}).get('records', 0)} record(s)",
        "redaction_status": "enabled",
        "summary": summary,
        "rules_and_memory": "\n".join(by_mechanism["rule"]) or "None.",
        "skill_candidates": "\n".join(by_mechanism["skill"]) or "None.",
        "hook_candidates": "\n".join(by_mechanism["hook"]) or "None.",
        "loop_candidates": "\n".join(by_mechanism["loop"]) or "None.",
        "approval_gates": "\n".join(by_mechanism["approval"]) or "None.",
        "rejected_candidates": "\n".join(by_mechanism["rejected"]) or "None.",
        "private_output": ".session-to-loop/private/candidates.json",
        "shareable_output": "\n- ".join(rendered_paths) if rendered_paths else str(out_dir / "loop-playbook.md"),
    }
    rendered = fill(template, values)
    scope = data.get("scope_policy") or {}
    scope_lines = [
        "",
        "## Analysis Scope",
        "",
        f"Approved: `{scope.get('approved', False)}`",
        "",
        f"Allowed roles: `{', '.join(scope.get('allowed_roles', [])) or 'not recorded'}`",
        "",
        f"Redacted snippets: `{'enabled' if scope.get('allow_redacted_snippets', True) else 'disabled'}`",
        "",
        f"Output visibility: `{scope.get('output_visibility', 'private')}`",
        "",
    ]
    return rendered + "\n" + "\n".join(scope_lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render loop cards, playbook, and draft skill/loop artifacts.")
    parser.add_argument(
        "--candidates",
        default=str(DEFAULT_CANDIDATES),
        help=f"Candidates JSON path. Default: {DEFAULT_CANDIDATES}",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help=f"Output directory. Default: {DEFAULT_OUT_DIR}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    cards_dir = out_dir / "cards"
    loops_dir = out_dir / "claude-loops"
    skills_dir = out_dir / "skills"
    for directory in (cards_dir, loops_dir, skills_dir):
        directory.mkdir(parents=True, exist_ok=True)

    rendered_paths: list[str] = []
    for candidate in data.get("candidates", []):
        card_path = cards_dir / f"{candidate['id']}.md"
        card_path.write_text(candidate_card(candidate), encoding="utf-8")
        rendered_paths.append(card_path.as_posix())
        if "loop" in candidate.get("mechanisms", []):
            loop_path = loops_dir / f"{candidate['id']}.md"
            loop_path.write_text(claude_loop(candidate), encoding="utf-8")
            rendered_paths.append(loop_path.as_posix())
        if "skill" in candidate.get("mechanisms", []):
            skill_path = skills_dir / f"{candidate['id']}.md"
            skill_path.write_text(generated_skill(candidate), encoding="utf-8")
            rendered_paths.append(skill_path.as_posix())

    summary_path = out_dir / "summary.json"
    public_summary = {
        "version": data.get("version"),
        "analysis_model": data.get("analysis_model"),
        "scope_policy": data.get("scope_policy"),
        "redaction": data.get("redaction"),
        "candidates": data.get("candidates", []),
    }
    summary_path.write_text(json.dumps(public_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rendered_paths.append(summary_path.as_posix())

    playbook_path = out_dir / "loop-playbook.md"
    playbook_path.write_text(playbook(data, out_dir, rendered_paths), encoding="utf-8")
    rendered_paths.append(playbook_path.as_posix())
    print(f"Rendered {len(rendered_paths)} artifact(s): {out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"render_artifacts.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
