#!/usr/bin/env python3
"""Design a goal-ready SixLoops loop from a user objective."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from loop_contract import build_exit_contract


DEFAULT_OUT_DIR = Path(".session-to-loop/goal-design")
DOMAINS = {
    "auto",
    "general",
    "frontend",
    "backend",
    "fullstack",
    "architecture",
    "review",
    "delivery",
    "maintenance",
}
LEVELS = {
    "read-only",
    "goal-loop",
    "isolated-draft",
    "verified-pr-draft",
    "scheduled-readonly",
    "scheduled-draft",
}
TEAM_MODES = {"auto", "none", "phased", "subagent-team"}


DOMAIN_KEYWORDS = {
    "frontend": (
        "frontend",
        "ui",
        "ux",
        "route",
        "component",
        "browser",
        "screenshot",
        "responsive",
        "i18n",
        "copy",
        "页面",
        "前端",
        "组件",
        "浏览器",
        "截图",
        "文案",
    ),
    "backend": (
        "backend",
        "api",
        "database",
        "db",
        "migration",
        "provider",
        "queue",
        "auth",
        "schema",
        "relay",
        "后端",
        "接口",
        "数据库",
        "迁移",
        "供应商",
    ),
    "fullstack": (
        "fullstack",
        "full-stack",
        "end-to-end",
        "integration",
        "contract",
        "frontend and backend",
        "前后端",
        "全栈",
        "联调",
        "集成",
        "契约",
    ),
    "architecture": (
        "architecture",
        "design",
        "plan",
        "split",
        "roadmap",
        "refactor",
        "架构",
        "方案",
        "拆分",
        "重构",
    ),
    "review": ("review", "audit", "self-review", "regression", "风险", "审查", "评审", "复查"),
    "delivery": ("deploy", "release", "pr", "merge", "ci", "handoff", "交付", "发布", "上线", "合并"),
    "maintenance": ("daily", "morning", "monitor", "todo", "logs", "triage", "每天", "早上", "巡检", "日志"),
}


BASE_STATE_SCHEMA = {
    "status": "pending, discovering, active, verifying, done, blocked, needs_human, budget_stopped",
    "objective_hash": "Stable hash of objective and success criteria.",
    "items": "Tracked work items with id, status, evidence, owner_role, verifier, and risk.",
    "attempts": "Attempt log with role, action, changed evidence, verification result, and timestamp.",
    "failure_signatures": "Repeated failure signatures and repeat counts.",
    "progress_metrics": "Evidence that changed, passed, failed, or stayed unchanged.",
    "human_queue": "Decisions, approvals, or missing context that require a human.",
    "next_cursor": "Where the next run should resume.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]+", "-", value.lower())).strip("-") or "goal-loop"


def compact(value: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


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


def read_goal(args: argparse.Namespace) -> str:
    if args.goal and args.goal_file:
        raise ValueError("Pass either --goal or --goal-file, not both.")
    if args.goal_file:
        return Path(args.goal_file).read_text(encoding="utf-8").strip()
    if args.goal:
        return args.goal.strip()
    raise ValueError("Pass --goal or --goal-file.")


def infer_domain(goal: str, requested: str) -> str:
    if requested != "auto":
        return requested
    lowered = goal.lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in lowered)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best_domain, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
    return best_domain if best_score > 0 else "general"


def resolve_team_mode(domain: str, requested: str) -> str:
    if requested != "auto":
        return requested
    if domain in {"frontend", "backend", "fullstack", "architecture", "review", "delivery", "maintenance"}:
        return "subagent-team"
    return "phased"


def base_profile(domain: str) -> dict:
    profiles = {
        "frontend": {
            "archetype": "frontend-verification",
            "trigger": ["After route, layout, component, auth UI, i18n, or copy changes."],
            "discovery_sources": [
                "changed frontend files",
                "route list",
                "default and non-default locales",
                "browser console",
                "network failures",
                "desktop/mobile screenshots",
                "i18n/static check output",
            ],
            "cycle_steps": [
                "Read prior state, current goal, changed UI files, and project instructions.",
                "Identify the smallest route/state/locale set that proves the change, including default locale and one non-default locale when relevant.",
                "Choose at most 1-3 visible or user-path regressions by impact, risk, and verifier availability.",
                "Apply only obvious, reversible UI fixes such as missing keys, broken routes, console errors, or text overflow inside the approved scope.",
                "Run focused static checks and browser verification, capture desktop/mobile screenshots when useful, inspect console/network/i18n fallback, and update state.",
            ],
            "verification": [
                "Target routes render without blocking errors.",
                "Desktop/mobile screenshots or snapshots confirm the main path.",
                "Console and network checks show no blocking errors.",
                "i18n/copy output shows no missing key, raw key, or unintended fallback locale.",
            ],
            "approval": [
                "visual direction changes",
                "product copy decisions",
                "translation tone or terminology decisions",
                "route behavior changes",
                "auth or data fixture changes",
            ],
            "reject_conditions": [
                "Same visible failure repeats twice.",
                "No new screenshot, console, network, or i18n evidence appears across two iterations.",
                "The browser verifier or dev server is unavailable.",
                "A product copy, translation tone, visual direction, route behavior, or scope-expansion decision is required.",
            ],
            "pass_evidence_required": [
                "Route URL list.",
                "Locale list.",
                "Screenshot paths or snapshot summaries.",
                "Console/network result.",
                "i18n/copy finding summary.",
            ],
            "team": ["planner", "frontend-maker", "browser-verifier", "reviewer", "integrator"],
        },
        "backend": {
            "archetype": "backend-contract-triage",
            "trigger": ["When API, provider, relay, queue, auth, database, CI, or migration work is requested."],
            "discovery_sources": ["changed backend files", "API or schema contracts", "focused tests", "logs", "CI output"],
            "cycle_steps": [
                "Read prior state, goal, changed backend surfaces, and project rules.",
                "Classify risk as contract, data, auth, migration, provider, latency, or release.",
                "Choose at most 1-3 high-impact failures or tasks with clear verifier evidence.",
                "Apply only low-risk local fixes with direct evidence.",
                "Run focused tests or acceptance checks and update state with pass/fail evidence.",
            ],
            "verification": ["Focused unit, integration, or acceptance checks pass.", "Remaining failures are classified with blocker reason."],
            "approval": ["production deploy", "database migration", "credential changes", "billing-impacting provider changes"],
            "team": ["planner", "backend-maker", "contract-verifier", "reviewer", "integrator"],
        },
        "fullstack": {
            "archetype": "fullstack-integration",
            "trigger": ["When a goal spans UI, API, auth/session, data model, or release behavior."],
            "discovery_sources": ["affected frontend files", "affected backend files", "interface contracts", "integration checks", "browser evidence"],
            "cycle_steps": [
                "Read prior state, goal, project rules, and affected surfaces.",
                "Map frontend, backend, integration, verification, and delivery work.",
                "Choose at most 1-3 dependency-ordered items with explicit verifier paths.",
                "Implement in small reversible slices and keep interface contracts explicit.",
                "Verify per layer, then verify the integrated user path and update state.",
            ],
            "verification": ["Contract-level checks pass.", "Frontend and backend focused checks pass.", "Integrated user path is verified or blocker is recorded."],
            "approval": ["schema migration", "release decision", "product behavior ambiguity", "auth or permission boundary changes"],
            "team": ["architect", "frontend-maker", "backend-maker", "integration-verifier", "integrator"],
        },
        "architecture": {
            "archetype": "architecture-task-split",
            "trigger": ["When the goal requires design, decomposition, migration planning, or cross-module refactoring."],
            "discovery_sources": ["project rules", "current architecture", "dependency graph", "risk areas", "verification commands"],
            "cycle_steps": [
                "Read prior state, goal, constraints, and relevant project instructions.",
                "Map affected modules, contracts, risks, and dependency order.",
                "Choose at most 1-3 design decisions or implementation slices with verifiers.",
                "Draft the smallest reversible plan or local proof before broad refactors.",
                "Review the plan against risks and update state with next action or human gate.",
            ],
            "verification": ["Design has a bounded implementation path.", "Each slice has a verifier.", "Ambiguities and human decisions are explicit."],
            "approval": ["large refactor", "schema migration", "public API change", "product tradeoff"],
            "team": ["architect", "risk-reviewer", "implementation-planner", "verifier", "integrator"],
        },
        "review": {
            "archetype": "maker-checker-review",
            "trigger": ["Before handoff, merge, or after meaningful implementation changes."],
            "discovery_sources": ["diff", "project rules", "tests", "build output", "risk checklist"],
            "cycle_steps": [
                "Read prior state, objective, diff, and project instructions.",
                "Summarize intended behavior and likely regression surfaces.",
                "Review at most 1-3 highest-risk findings with file/line or failure evidence.",
                "Patch only directly evidenced low-risk issues if edit scope is approved.",
                "Run focused verification and update state with unresolved risks.",
            ],
            "verification": ["No high-confidence blocker remains.", "Focused tests or checks pass, or untested risk is listed."],
            "approval": ["merge", "release", "product judgment", "large unrelated refactor"],
            "team": ["maker-summarizer", "checker", "verifier", "risk-reviewer", "integrator"],
        },
        "delivery": {
            "archetype": "delivery-readiness",
            "trigger": ["Before PR draft, release handoff, deploy readiness, or CI completion."],
            "discovery_sources": ["diff", "CI status", "test output", "build output", "release checklist"],
            "cycle_steps": [
                "Read prior state, goal, diff, CI status, and delivery rules.",
                "Choose at most 1-3 release-blocking items by impact and verifier availability.",
                "Fix only local reversible blockers with evidence.",
                "Run delivery verifiers and prepare PR or handoff draft when checks pass.",
                "Update state with pass evidence, open risks, and human approval needs.",
            ],
            "verification": ["Focused checks pass.", "CI is green or blocker is documented.", "PR/handoff includes validation evidence and remaining risk."],
            "approval": ["push", "merge", "production deploy", "release approval"],
            "team": ["release-planner", "ci-fixer", "verifier", "handoff-writer", "integrator"],
        },
        "maintenance": {
            "archetype": "maintenance-triage",
            "trigger": ["On a daily/weekly check, after new logs, CI failures, TODOs, or user feedback arrive."],
            "discovery_sources": ["recent errors", "CI failures", "TODOs", "user feedback", "state file"],
            "cycle_steps": [
                "Read prior state and the newest bounded project signals.",
                "Select only 1-3 high-value issues by impact, confidence, risk, and verifier availability.",
                "For each issue, record cause, impact, recommended action, and risk.",
                "Attempt only low-risk local fixes inside an isolated scope when approved.",
                "Run verification, update state, and stop when no high-value issue remains or human judgment is needed.",
            ],
            "verification": ["Each selected issue has cause, impact, action, risk, and verifier result.", "Low-risk fixes pass focused checks or blockers are recorded."],
            "approval": ["broad scan", "production action", "destructive changes", "large refactor"],
            "team": ["triage-planner", "issue-investigator", "fixer", "verifier", "integrator"],
        },
        "general": {
            "archetype": "goal-execution",
            "trigger": ["When the user delegates this goal."],
            "discovery_sources": ["project rules", "current diff", "relevant files", "available verifier commands"],
            "cycle_steps": [
                "Read prior state, goal, constraints, and project instructions.",
                "Identify the smallest useful task surface and verifier.",
                "Choose at most 1-3 work items by impact, confidence, risk, and verifier availability.",
                "Act only inside the approved scope.",
                "Verify, update state, and stop when done, blocked, or budget is reached.",
            ],
            "verification": ["The agreed success criteria pass or a blocker is recorded."],
            "approval": ["irreversible changes", "production action", "scope expansion"],
            "team": ["planner", "maker", "verifier", "reviewer", "integrator"],
        },
    }
    return profiles.get(domain, profiles["general"])


def role_prompt(role_id: str, goal: str, domain: str) -> dict:
    labels = {
        "planner": "Planner",
        "architect": "Architect",
        "frontend-maker": "Frontend Maker",
        "backend-maker": "Backend Maker",
        "browser-verifier": "Browser Verifier",
        "contract-verifier": "Contract Verifier",
        "integration-verifier": "Integration Verifier",
        "implementation-planner": "Implementation Planner",
        "risk-reviewer": "Risk Reviewer",
        "maker-summarizer": "Maker Summarizer",
        "checker": "Checker",
        "verifier": "Verifier",
        "reviewer": "Reviewer",
        "release-planner": "Release Planner",
        "ci-fixer": "CI Fixer",
        "handoff-writer": "Handoff Writer",
        "triage-planner": "Triage Planner",
        "issue-investigator": "Issue Investigator",
        "fixer": "Fixer",
        "maker": "Maker",
        "integrator": "Integrator",
    }
    can_modify = role_id in {"frontend-maker", "backend-maker", "ci-fixer", "fixer", "maker"}
    outputs = {
        "integrator": ["Updated STATE.json", "final status", "handoff summary"],
        "verifier": ["commands or checks run", "pass/fail evidence", "untested risks"],
        "browser-verifier": ["route list", "screenshot or snapshot evidence", "console/network findings"],
        "contract-verifier": ["contract surface", "focused verifier result", "classified blockers"],
        "integration-verifier": ["per-layer verifier result", "integrated path result", "remaining blocker"],
        "checker": ["findings ordered by severity", "file/line evidence", "regression risk"],
        "reviewer": ["diff risks", "missing verifier", "approval gate"],
        "risk-reviewer": ["risk map", "human decisions", "safe next slice"],
    }.get(role_id, ["finding summary", "recommended next action", "evidence or blocker"])
    mission = {
        "integrator": "Merge role outputs into one state update and final status. Do not hide blockers.",
        "verifier": "Run or specify the smallest verifier that can reject bad output.",
        "browser-verifier": "Verify the real UI path with browser evidence, not visual guesses.",
        "contract-verifier": "Check contract, schema, data, auth, provider, or latency behavior with focused evidence.",
        "integration-verifier": "Verify that frontend, backend, and contract changes work together.",
        "checker": "Review for bugs, regressions, missing tests, and risky assumptions.",
        "reviewer": "Review the diff and plan against objective, project rules, and likely regressions.",
        "risk-reviewer": "Identify high-impact decisions that need human judgment before more autonomy.",
    }.get(role_id, f"Handle the {labels.get(role_id, role_id)} role for this {domain} goal.")
    return {
        "id": role_id,
        "title": labels.get(role_id, role_id.replace("-", " ").title()),
        "mission": mission,
        "may_modify_files": can_modify,
        "outputs": outputs,
        "prompt": (
            f"You are the {labels.get(role_id, role_id)} for a SixLoops {domain} goal. "
            f"Goal: {goal} Return only your role output, evidence, blockers, and next action. "
            "Do not expand scope. Do not perform high-impact actions without explicit approval."
        ),
    }


def build_design(args: argparse.Namespace) -> dict:
    goal = read_goal(args)
    domain = infer_domain(goal, args.domain)
    profile = base_profile(domain)
    team_mode = resolve_team_mode(domain, args.team_mode)
    loop_id = args.loop_id or slug(f"{domain}-{compact(goal, 40)}-{short_hash(goal)}")
    name = args.name or f"{profile['archetype'].replace('-', ' ').title()} Loop"
    level = args.level
    max_items = max(1, args.max_items)
    max_iterations = max(1, args.max_iterations)
    team_roles = [role_prompt(role_id, goal, domain) for role_id in profile["team"]]
    state_file = "STATE.json"
    approval_boundary = list(dict.fromkeys(profile["approval"] + ["scope expansion", "irreversible changes"]))
    success_criteria = args.success_criteria or profile["verification"]
    verifier_commands = args.verifier or ["Run the focused project verifier identified during the Decide step."]
    reject_conditions = profile.get(
        "reject_conditions",
        [
            "Same failure repeats twice.",
            "No evidence changes across two iterations.",
            "A human approval boundary is reached.",
            "The verifier is unavailable or ambiguous.",
        ],
    )
    pass_evidence_required = profile.get(
        "pass_evidence_required",
        ["Command output, screenshot, CI status, review finding resolution, or explicit verifier note."],
    )
    loop_exit_contract = build_exit_contract(
        success_criteria,
        reject_conditions,
        approval_boundary,
        max_items,
        max_iterations,
    )

    managed_loop = {
        "objective": goal,
        "heartbeat": "goal" if not level.startswith("scheduled") else "scheduled",
        "recommended_maturity": level,
        "cadence_or_trigger": profile["trigger"],
        "discovery_sources": profile["discovery_sources"],
        "state_file": state_file,
        "state_schema": BASE_STATE_SCHEMA,
        "cycle_steps": profile["cycle_steps"],
        "selection_policy": [
            f"Choose at most {max_items} item(s) per cycle.",
            "Prefer high-impact work with clear verifier evidence.",
            "Defer work that needs product, release, data, or architecture judgment.",
        ],
        "max_items_per_cycle": max_items,
        "max_iterations_per_run": max_iterations,
        "completion_contract": {
            "success_criteria": success_criteria,
            "verifier_commands": verifier_commands,
            "evaluator_agent": "Use deterministic checks first; use a reviewer or verifier role when commands cannot decide.",
            "pass_evidence_required": pass_evidence_required,
            "reject_conditions": reject_conditions,
            "no_progress_policy": "Stop when no evidence changes across two iterations, then record the blocker and next human decision.",
        },
        "loop_exit_contract": loop_exit_contract,
        "change_policy": (
            "Read-only until edit scope is approved. For draft-producing levels, use a local reversible change set "
            "or isolated branch/worktree. Do not push, merge, deploy, migrate, delete data, or change credentials without approval."
        ),
        "deliverables": ["Updated STATE.json", "status summary", "verifier evidence", "patch/PR draft or blocker report when applicable"],
        "resume_policy": "Read STATE.json first and continue unresolved active or blocked items before selecting new work.",
        "failure_policy": "Record repeated failures, missing inputs, and human decisions; stop instead of guessing.",
        "promotion_criteria": ["Promote autonomy only after repeated accepted runs with reliable verifier evidence."],
        "demotion_criteria": ["Demote when human review rejects outputs, verifier evidence is weak, or cost exceeds value."],
    }

    return {
        "version": 1,
        "created_at": now_iso(),
        "design_model": "goal-to-loop-v1",
        "loop_id": loop_id,
        "name": name,
        "goal": goal,
        "domain": domain,
        "work_shape": "goal-driven",
        "loop_archetype": profile["archetype"],
        "adoption_level": level,
        "team_mode": team_mode,
        "project_root": str(Path(args.project_root)),
        "managed_loop": managed_loop,
        "subagent_team": {
            "mode": team_mode,
            "activation_rule": (
                "If the host runtime exposes subagent or multi-agent tools, use these roles as separate agents for "
                "planner/reviewer/verifier work. If unavailable, execute the same roles sequentially in one agent."
            )
            if team_mode == "subagent-team"
            else "Execute roles sequentially in the current agent.",
            "roles": [] if team_mode == "none" else team_roles,
            "coordination": [
                "Planner defines at most 1-3 items and verifier paths.",
                "Maker roles act only inside approved scope.",
                "Reviewer/checker/verifier roles must be independent from maker output when possible.",
                "Integrator updates state and returns DONE, CONTINUE, BLOCKED, NEEDS_HUMAN, or BUDGET_STOPPED.",
            ],
        },
        "safety": {
            "autonomy_level": level,
            "requires_approval_for": approval_boundary,
            "budget_caps": [
                f"Handle at most {max_items} item(s) per cycle.",
                f"Stop after {max_iterations} iteration(s) per run.",
            ],
            "isolation": "Use read-only mode unless edit scope is approved; use isolated branch/worktree for draft-producing levels.",
        },
    }


def build_state(design: dict) -> dict:
    managed_loop = design["managed_loop"]
    contract = managed_loop["completion_contract"]
    return {
        "version": 1,
        "loop_id": design["loop_id"],
        "name": design["name"],
        "status": "pending",
        "adoption_level": design["adoption_level"],
        "created_at": now_iso(),
        "objective_hash": short_hash(json.dumps(contract["success_criteria"], ensure_ascii=False) + design["goal"]),
        "objective": design["goal"],
        "domain": design["domain"],
        "team_mode": design["team_mode"],
        "state_schema": managed_loop["state_schema"],
        "success_criteria": contract["success_criteria"],
        "reject_conditions": contract["reject_conditions"],
        "loop_exit_contract": managed_loop["loop_exit_contract"],
        "approval_boundary": design["safety"]["requires_approval_for"],
        "items": [],
        "attempts": [],
        "failure_signatures": [],
        "progress_metrics": [],
        "human_queue": [],
        "next_cursor": None,
        "last_status": None,
        "last_exit_status": None,
        "status_history": [],
    }


def render_goal(design: dict) -> str:
    managed_loop = design["managed_loop"]
    contract = managed_loop["completion_contract"]
    exit_contract = managed_loop["loop_exit_contract"]
    return f"""# {design["name"]}

Use this as a delegated SixLoops goal loop.

## Goal

{design["goal"]}

## Loop Shape

- Domain: `{design["domain"]}`
- Archetype: `{design["loop_archetype"]}`
- Adoption level: `{design["adoption_level"]}`
- Team mode: `{design["team_mode"]}`

## Success Criteria

{bullet(contract["success_criteria"])}

## Cycle

{numbered(managed_loop["cycle_steps"])}

## Selection Policy

{bullet(managed_loop["selection_policy"])}

## Verification

{bullet(contract["verifier_commands"])}

Required pass evidence:

{bullet(contract["pass_evidence_required"])}

## Stop Conditions

{bullet(contract["reject_conditions"])}

Also stop after `{managed_loop["max_iterations_per_run"]}` iteration(s), repeated no-progress, or a human gate.

## Exit Contract

Continue only if:

{bullet(exit_contract["continue_only_if"])}

Return `DONE` when:

{bullet(exit_contract["done_when"])}

Return `NEEDS_HUMAN` when:

{bullet(exit_contract["needs_human_when"])}

Return `BLOCKED` when:

{bullet(exit_contract["blocked_when"])}

Return `BUDGET_STOPPED` when:

{bullet(exit_contract["budget_stopped_when"])}

## State

- State file: `STATE.json`
- Read state before work.
- Update state before returning any final status.

## Human Gate

{bullet(design["safety"]["requires_approval_for"])}

## Final Status

Return exactly one: `DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.
"""


def render_team(design: dict) -> str:
    team = design["subagent_team"]
    if team["mode"] == "none":
        return "# Team\n\nTeam mode is disabled for this loop.\n"
    blocks = [
        "# Team",
        "",
        f"Mode: `{team['mode']}`",
        "",
        team["activation_rule"],
        "",
        "## Coordination",
        "",
        bullet(team["coordination"]),
    ]
    for role in team["roles"]:
        blocks.extend(
            [
                "",
                f"## {role['title']}",
                "",
                f"- Role id: `{role['id']}`",
                f"- May modify files: `{str(role['may_modify_files']).lower()}`",
                f"- Mission: {role['mission']}",
                "",
                "Outputs:",
                "",
                bullet(role["outputs"]),
                "",
                "Prompt:",
                "",
                "```text",
                role["prompt"],
                "```",
            ]
        )
    return "\n".join(blocks) + "\n"


def render_handoff(design: dict, artifact_dir: Path) -> str:
    return f"""# {design["name"]} Handoff

This folder contains a goal-ready SixLoops design generated from a user objective.

## Start Here

1. Read `GOAL.md`.
2. If team tools are available and team mode is `subagent-team`, use `TEAM.md` to split planner, maker, checker, verifier, and integrator roles.
3. Keep `STATE.json` beside the run and update it before stopping.

## Files

- `{artifact_dir / "GOAL.md"}`
- `{artifact_dir / "TEAM.md"}`
- `{artifact_dir / "STATE.json"}`
- `{artifact_dir / "goal-loop-design.json"}`
- `{artifact_dir / "AGENTS-snippet.md"}`
"""


def render_agents_snippet(design: dict) -> str:
    managed_loop = design["managed_loop"]
    return f"""# Draft AGENTS.md Snippet: {design["name"]}

This is a draft loop instruction. Review before copying into project instructions.

When the goal matches `{design["loop_id"]}`:

- Run as `{design["adoption_level"]}` with `{design["team_mode"]}` team mode.
- Objective: {design["goal"]}
- Select at most {managed_loop["max_items_per_cycle"]} item(s) per cycle.
- Stop after {managed_loop["max_iterations_per_run"]} iteration(s), repeated no-progress, or a human gate.
- Read and update `STATE.json` before returning.
- Ask before: {", ".join(design["safety"]["requires_approval_for"])}.
"""


def write_text(path: Path, content: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Pass --overwrite to replace it.")
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, content: dict, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists. Pass --overwrite to replace it.")
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_artifacts(design: dict, out_root: Path, overwrite: bool) -> Path:
    artifact_dir = out_root / design["loop_id"]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 1,
        "created_at": now_iso(),
        "loop_id": design["loop_id"],
        "name": design["name"],
        "domain": design["domain"],
        "adoption_level": design["adoption_level"],
        "team_mode": design["team_mode"],
        "files": {
            "goal": str(artifact_dir / "GOAL.md"),
            "team": str(artifact_dir / "TEAM.md"),
            "state": str(artifact_dir / "STATE.json"),
            "design": str(artifact_dir / "goal-loop-design.json"),
            "handoff": str(artifact_dir / "HANDOFF.md"),
            "agents_snippet": str(artifact_dir / "AGENTS-snippet.md"),
        },
    }
    write_json(artifact_dir / "goal-loop-design.json", design, overwrite)
    write_json(artifact_dir / "STATE.json", build_state(design), overwrite)
    write_text(artifact_dir / "GOAL.md", render_goal(design), overwrite)
    write_text(artifact_dir / "TEAM.md", render_team(design), overwrite)
    write_text(artifact_dir / "HANDOFF.md", render_handoff(design, artifact_dir), overwrite)
    write_text(artifact_dir / "AGENTS-snippet.md", render_agents_snippet(design), overwrite)
    write_json(artifact_dir / "manifest.json", manifest, overwrite)
    return artifact_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design a goal-ready loop and optional subagent team from a user objective.")
    parser.add_argument("--goal", default=None, help="User objective to turn into a loop.")
    parser.add_argument("--goal-file", default=None, help="Path to a text file containing the user objective.")
    parser.add_argument("--name", default=None, help="Human-readable loop name.")
    parser.add_argument("--loop-id", default=None, help="Stable loop id. Defaults to a slug from domain and goal hash.")
    parser.add_argument("--domain", choices=sorted(DOMAINS), default="auto", help="Task domain. Default: auto.")
    parser.add_argument("--level", choices=sorted(LEVELS), default="goal-loop", help="Starting adoption level. Default: goal-loop.")
    parser.add_argument("--team-mode", choices=sorted(TEAM_MODES), default="auto", help="Team design mode. Default: auto.")
    parser.add_argument("--project-root", default=".", help="Project root for metadata only. Default: current directory.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help=f"Output root. Default: {DEFAULT_OUT_DIR}")
    parser.add_argument("--max-items", type=int, default=3, help="Maximum items per cycle. Default: 3.")
    parser.add_argument("--max-iterations", type=int, default=8, help="Maximum iterations per run. Default: 8.")
    parser.add_argument("--success-criteria", action="append", default=[], help="Override/add success criterion. Can repeat.")
    parser.add_argument("--verifier", action="append", default=[], help="Override/add verifier command or check. Can repeat.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing artifacts for the same loop id.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    design = build_design(args)
    artifact_dir = write_artifacts(design, Path(args.out_dir), args.overwrite)
    print(f"Created goal loop design: {artifact_dir}")
    print(f"- {artifact_dir / 'GOAL.md'}")
    print(f"- {artifact_dir / 'TEAM.md'}")
    print(f"- {artifact_dir / 'STATE.json'}")
    print(f"- {artifact_dir / 'goal-loop-design.json'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"design_goal_loop.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
