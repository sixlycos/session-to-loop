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

from sixloops.core.loop_contract import normalize_exit_contract
from sixloops.core.mode_policy import INTERNAL_TO_MODE, level_to_mode, mode_to_level


DEFAULT_CANDIDATES = Path(".sixloops/private/candidates.json")
DEFAULT_OUT_DIR = Path(".sixloops/adopted")
ALLOWED_LEVELS = set(INTERNAL_TO_MODE)


LEVEL_POLICIES = {
    "read-only": "Read evidence and produce recommendations only. Do not edit project files.",
    "goal-loop": "Run as a delegated goal loop. Ask before edits unless the user explicitly grants edit scope.",
    "isolated-draft": "Use an isolated branch or worktree for reversible draft changes. Do not push or merge.",
    "verified-pr-draft": "Prepare a verified patch or PR draft when checks pass. Do not push, merge, or deploy without approval.",
    "scheduled-readonly": "Use only as a scheduled read-only report until separate automation setup is approved.",
    "scheduled-draft": "Use only after separate scheduling, isolation, notification, and rollback boundaries are approved.",
}
ZH_LEVEL_POLICIES = {
    "read-only": "只读证据并给出建议，不改项目文件。",
    "goal-loop": "按已委托目标循环运行；除非用户明确授权改动，否则修改前先询问。",
    "isolated-draft": "使用隔离分支或 worktree 进行可回退草稿改动；不 push、不 merge。",
    "verified-pr-draft": "检查通过后准备补丁或 PR 草稿；未获批准前不 push、不 merge、不部署。",
    "scheduled-readonly": "只作为定时只读报告使用；自动化设置需要另行批准。",
    "scheduled-draft": "只有在定时、隔离、通知和回滚边界都获批后才能使用。",
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


def language_for_candidate(candidate: dict) -> str:
    return "zh" if re.search(r"[\u3400-\u9fff]", json.dumps(candidate, ensure_ascii=False)) else "en"


def join_items(items: list[str], language: str) -> str:
    return ("、" if language == "zh" else ", ").join(items)


ZH_TEXT = {
    "A smaller rule or checklist would not preserve state, verifier evidence, failure signatures, and the next cursor across runs.": "规则或清单无法在多轮运行之间保留状态、验收证据、失败签名和下一步位置。",
    "Objective is unchanged.": "目标没有变化。",
    "Next action stays inside approved scope.": "下一步仍在已批准范围内。",
    "A verifier can reject bad output.": "验收器能够拒绝错误产出。",
    "The Change Map can be updated or the next action can produce evidence for it.": "Change Map 可以被更新，或下一步能为它产生证据。",
    "New evidence changed or is likely from the next verifier.": "已有新证据变化，或下一轮验收可能产生新证据。",
    "Risk stays below the approved mode and explicit return points.": "风险仍低于当前批准模式和明确返回点。",
    "The last cycle changed evidence, narrowed scope, reduced failures, or clarified the blocker.": "上一轮改变了证据、收窄了范围、减少了失败，或明确了阻塞点。",
    "Token, time, cost, or tool budget is reached.": "token、时间、成本或工具预算达到上限。",
}


def zh_text(value: str) -> str:
    if value in ZH_TEXT:
        return ZH_TEXT[value]
    if value.startswith("Start as "):
        return "先从当前批准模式启动；只有在验收证据和明确批准点稳定后，才升级到更高自动化。"
    match = re.fullmatch(r"Approval required for (.+) after options, impact, and regression evidence are recorded\.", value)
    if match:
        return f"需要批准：{match.group(1)}。批准前必须已记录选项、影响和回归证据。"
    match = re.fullmatch(r"Fewer than (\d+) item\(s\) are active in this cycle\.", value)
    if match:
        return f"本轮活跃事项少于 {match.group(1)} 个。"
    match = re.fullmatch(r"Fewer than (\d+) iteration\(s\) have run\.", value)
    if match:
        return f"已运行轮数少于 {match.group(1)} 轮。"
    match = re.fullmatch(r"Review required for (.+)\.", value)
    if match:
        return f"需要审查：{match.group(1)}。"
    match = re.fullmatch(r"More than (\d+) item\(s\) would be required in one cycle\.", value)
    if match:
        return f"单轮需要超过 {match.group(1)} 个事项。"
    match = re.fullmatch(r"(\d+) iteration\(s\) are reached\.", value)
    if match:
        return f"达到 {match.group(1)} 轮上限。"
    return value


def zh_items(items: list[str]) -> list[str]:
    return [zh_text(item) for item in items]


def bullet(items: list[str], language: str = "en") -> str:
    if not items:
        return "- 无。" if language == "zh" else "- None."
    return "\n".join(f"- {item}" for item in items)


def numbered(items: list[str], language: str = "en") -> str:
    if not items:
        return "1. 未记录可重复步骤。" if language == "zh" else "1. No repeatable steps recorded."
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


def change_map_for_candidate(candidate: dict, managed_loop: dict, contract: dict) -> dict:
    raw = candidate.get("change_map") if isinstance(candidate.get("change_map"), dict) else {}
    raw = raw or managed_loop.get("change_map") if isinstance(managed_loop.get("change_map"), dict) else raw
    verifiers = strings(contract.get("verifier_commands") or candidate.get("verification"))
    return {
        "current_x": raw.get("current_x") or candidate.get("summary") or managed_loop.get("objective") or "Current state is not mapped yet.",
        "target_b": raw.get("target_b") or managed_loop.get("objective") or candidate.get("summary") or "Target outcome is not mapped yet.",
        "user_perception": raw.get("user_perception") or candidate.get("user_value") or "The user should see a concrete change with verifier evidence.",
        "transformation_thesis": raw.get("transformation_thesis") or candidate.get("why_this_loop") or "Turn observed evidence into verified progress.",
        "affected_surfaces": strings(raw.get("affected_surfaces") or candidate.get("inputs") or managed_loop.get("discovery_sources")),
        "regression_plan": strings(raw.get("regression_plan") or verifiers),
        "rollback_or_compatibility": strings(raw.get("rollback_or_compatibility") or managed_loop.get("change_policy")),
        "research_questions": strings(raw.get("research_questions") or ["What evidence proves current X?", "Which surfaces must change for target B?", "Which verifier rejects a bad result?"]),
        "waves": strings(raw.get("waves") or managed_loop.get("cycle_steps")),
        "decision_packet_required_when": strings(raw.get("decision_packet_required_when") or candidate.get("approval_boundaries") or (candidate.get("safety") or {}).get("requires_approval_for")),
    }


def render_change_map(change_map: dict, language: str) -> str:
    if language == "zh":
        return f"""- 当前 X：{change_map["current_x"]}
- 目标 B：{change_map["target_b"]}
- 用户感知：{change_map["user_perception"]}
- 转换假设：{change_map["transformation_thesis"]}

波及面：

{bullet(change_map["affected_surfaces"], language)}

回归 / 兼容：

{bullet(change_map["regression_plan"] + change_map["rollback_or_compatibility"], language)}

推进波次：

{numbered(change_map["waves"], language)}

决策包触发：

{bullet(change_map["decision_packet_required_when"], language)}
"""
    return f"""- Current X: {change_map["current_x"]}
- Target B: {change_map["target_b"]}
- User perception: {change_map["user_perception"]}
- Transformation thesis: {change_map["transformation_thesis"]}

Affected surfaces:

{bullet(change_map["affected_surfaces"], language)}

Regression / compatibility:

{bullet(change_map["regression_plan"] + change_map["rollback_or_compatibility"], language)}

Rollout waves:

{numbered(change_map["waves"], language)}

Decision packet triggers:

{bullet(change_map["decision_packet_required_when"], language)}
"""


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


def first_text(*values: object) -> str:
    for value in values:
        items = strings(value)
        if items:
            return items[0]
    return ""


def rationale(candidate: dict, managed_loop: dict, level: str) -> dict:
    safety = candidate.get("safety") if isinstance(candidate.get("safety"), dict) else {}
    mode = level_to_mode(level)
    return {
        "why_this_loop": first_text(
            candidate.get("why_this_loop"),
            candidate.get("why_this_mechanism"),
            candidate.get("summary"),
            managed_loop.get("objective"),
            "This candidate needs bounded cycles with verifier evidence and state.",
        ),
        "why_not_smaller": first_text(
            candidate.get("why_not_smaller"),
            "A smaller rule or checklist would not preserve state, verifier evidence, failure signatures, and the next cursor across runs.",
        ),
        "why_not_more_autonomous": first_text(
            candidate.get("why_not_more_autonomous"),
            f"Start as {mode}; stronger autonomy needs accepted verifier evidence and the recorded approval points.",
        ),
        "human_gates": strings(safety.get("requires_approval_for")),
    }


def build_state(candidate: dict, level: str, artifact_dir: Path) -> dict:
    managed_loop, contract = candidate_contract(candidate)
    safety = candidate.get("safety") if isinstance(candidate.get("safety"), dict) else {}
    change_map = change_map_for_candidate(candidate, managed_loop, contract)
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
        "change_map": change_map,
        "success_criteria": strings(contract.get("success_criteria") or candidate.get("verification")),
        "reject_conditions": strings(contract.get("reject_conditions") or candidate.get("stop_conditions")),
        "loop_exit_contract": exit_contract(candidate),
        "approval_boundary": strings(safety.get("requires_approval_for")),
        "budget_caps": strings(safety.get("budget_caps")),
        "items": [],
        "attempts": [],
        "active_wave": None,
        "decision_packets": [],
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
    change_map = change_map_for_candidate(candidate, managed_loop, contract)
    candidate_id = str(candidate.get("id"))
    state_file = "STATE.json"
    suggested_state = managed_loop.get("state_file", f".sixloops/state/{candidate_id}.json")
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
    reasons = rationale(candidate, managed_loop, level)
    language = language_for_candidate(candidate)
    if language == "zh":
        return f"""# {candidate.get("name", candidate_id)} 执行包

用于用户确认 `{candidate_id}` 以 `{mode}` 启动之后。

## 执行摘要

- 模式：`{mode}`（内部级别 `{level}`）：{ZH_LEVEL_POLICIES[level]}
- 状态文件：`{state_file}`；建议项目状态路径：`{suggested_state}`
- 每轮最多处理 {max_items} 个事项；单次最多 {max_iterations} 轮。
- 需要先问用户：{join_items(approval_boundary, language) or "扩大范围、不可逆动作、发布、数据或产品边界变更"}。

## 目标

{managed_loop.get("objective") or candidate.get("summary", "运行这个 loop。")}

## 改造图景

{render_change_map(change_map, language)}

## 为什么是这个 loop

- 为什么值得跑：{zh_text(reasons["why_this_loop"])}
- 为什么不只是更小机制：{zh_text(reasons["why_not_smaller"])}
- 为什么不更自动化：{zh_text(reasons["why_not_more_autonomous"])}

## 验收标准

{bullet(success, language)}

## 循环步骤

{numbered(cycle_steps, language)}

## 选择规则

{bullet(selection_policy or [f"每轮最多选择 {max_items} 个高价值事项。"], language)}

## 验证方式

{bullet(verifiers or strings(candidate.get("verification")) or ["运行项目里最贴近目标的聚焦验证。"], language)}

## 停止条件

{bullet(reject_conditions, language)}

还要在以下情况停止：达到 `{max_iterations}` 轮、连续两轮没有进展，或触达返回点。

## 退出协议

仅在以下条件成立时继续：

{bullet(zh_items(exits["continue_only_if"]), language)}

返回 `DONE` 的条件：

{bullet(zh_items(exits["done_when"]), language)}

交还给用户的条件：

{bullet(zh_items(exits["needs_human_when"]), language)}

返回 `BLOCKED` 的条件：

{bullet(zh_items(exits["blocked_when"]), language)}

返回 `BUDGET_STOPPED` 的条件：

{bullet(zh_items(exits["budget_stopped_when"]), language)}

## 交付物

{bullet(deliverables or ["状态摘要", "更新后的 STATE.json", "验证证据或阻塞原因"], language)}

## 状态记录

结束前只能返回一个状态：`DONE`、`CONTINUE`、`BLOCKED`、`NEEDS_HUMAN` 或 `BUDGET_STOPPED`。
面向用户说明时，把 `NEEDS_HUMAN` 写成“交还给用户判断”。

下一次运行前，在 `STATE.json` 记录：是否减少了人工纠正、是否产生误报、是否过度依赖人工判断、是否应该改成 skill/checklist，或是否已有足够被接受的产出。
"""
    return f"""# {candidate.get("name", candidate_id)} Run Packet

Use this after the user starts `{candidate_id}` as `{mode}`.

## Objective

{managed_loop.get("objective") or candidate.get("summary", "Run the loop.")}

## Change Map

{render_change_map(change_map, language)}

## Why This Loop

- Why this loop: {reasons["why_this_loop"]}
- Why not smaller: {reasons["why_not_smaller"]}
- Why not more autonomous: {reasons["why_not_more_autonomous"]}

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

Also stop after `{max_iterations}` iteration(s), no progress across two iterations, or any return point.

## Exit Contract

Continue only if:

{bullet(exits["continue_only_if"])}

Return `DONE` when:

{bullet(exits["done_when"])}

Return to user when:

{bullet(exits["needs_human_when"])}

Return `BLOCKED` when:

{bullet(exits["blocked_when"])}

Return `BUDGET_STOPPED` when:

{bullet(exits["budget_stopped_when"])}

## Explicit Approval Points

{bullet(approval_boundary or ["Ask before expanding scope, making irreversible changes, or changing product/release/data boundaries."])}

## Deliverables

{bullet(deliverables or ["Status summary", "Updated STATE.json", "Verifier evidence or blocker reason"])}

## Status Protocol

Return one status at the end:

- `DONE`: all success criteria passed with verifier evidence.
- `CONTINUE`: progress changed and budget remains.
- `BLOCKED`: repeated failure, no progress, missing input, or uncertain verifier.
- `NEEDS_HUMAN`: return for review after a decision packet is ready or explicit approval is required.
- `BUDGET_STOPPED`: item, iteration, time, or token cap was reached.

## First Run Retro

Before the next run, update `STATE.json` with whether this loop reduced repeated human correction,
created false positives, required too much human judgment, should become a skill/checklist,
or has enough accepted output to keep its current autonomy level.
"""


def render_handoff(candidate: dict, level: str, artifact_dir: Path) -> str:
    managed_loop, contract = candidate_contract(candidate)
    exits = exit_contract(candidate)
    change_map = change_map_for_candidate(candidate, managed_loop, contract)
    candidate_id = str(candidate.get("id"))
    mode = level_to_mode(level)
    reasons = rationale(candidate, managed_loop, level)
    language = language_for_candidate(candidate)
    if language == "zh":
        return f"""# {candidate.get("name", candidate_id)} 交接说明

这份执行包是在 `{candidate_id}` 以 `{mode}` 启动后生成的。

## 从哪里开始

把 `GOAL.md` 作为已委托目标；先更新改造图景，`STATE.json` 放在旁边，停止前必须更新。

## 改造图景

{render_change_map(change_map, language)}

## 为什么存在

- 为什么值得跑：{zh_text(reasons["why_this_loop"])}
- 为什么不只是更小机制：{zh_text(reasons["why_not_smaller"])}
- 为什么不更自动化：{zh_text(reasons["why_not_more_autonomous"])}

## 触发时机

{bullet(strings(managed_loop.get("cadence_or_trigger") or candidate.get("trigger")), language)}

## 退出协议

仅在以下条件成立时继续：

{bullet(zh_items(exits["continue_only_if"]), language)}

返回 `DONE` 的条件：

{bullet(zh_items(exits["done_when"]), language)}

交还给用户的条件：

{bullet(zh_items(exits["needs_human_when"]), language)}

返回 `BLOCKED` 的条件：

{bullet(zh_items(exits["blocked_when"]), language)}

返回 `BUDGET_STOPPED` 的条件：

{bullet(zh_items(exits["budget_stopped_when"]), language)}

## 复盘记录

第一轮结束后，在 `STATE.json` 记录节省的人工纠正、误报、人工接受度、下一步调整和是否建议改成更小机制。

## 文件

- `{artifact_dir / "GOAL.md"}`
- `{artifact_dir / "STATE.json"}`
- `{artifact_dir / "AGENTS-snippet.md"}`
- `{artifact_dir / "manifest.json"}`
"""
    return f"""# {candidate.get("name", candidate_id)} Run Handoff

This packet was generated after starting `{candidate_id}` as `{mode}`.

## What To Run

Paste or attach `GOAL.md` as the delegated goal. Refresh the Change Map first. Keep `STATE.json` beside it and update it before stopping.

## Change Map

{render_change_map(change_map, language)}

## Why This Exists

- Why this loop: {reasons["why_this_loop"]}
- Why not smaller: {reasons["why_not_smaller"]}
- Why not more autonomous: {reasons["why_not_more_autonomous"]}

## Trigger

{bullet(strings(managed_loop.get("cadence_or_trigger") or candidate.get("trigger")))}

## Exit Contract

Continue only if:

{bullet(exits["continue_only_if"])}

Return `DONE` when:

{bullet(exits["done_when"])}

Return to user when:

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
    language = language_for_candidate(candidate)
    if language == "zh":
        return f"""# AGENTS.md 草稿片段：{candidate.get("name", candidate_id)}

这是待审查的 loop 指令草稿。不要自动安装；复制进项目规则前先人工确认。

当 `{candidate_id}` 被触发时：

- 运行模式：`{mode}`（内部级别 `{level}`）。
- 目标：{managed_loop.get("objective") or candidate.get("summary", "未记录目标。")}
- 每轮先更新改造图景：当前 X、目标 B、波及面、回归 / 兼容路径和推进波次。
- 停止前必须读取并更新 Change Map 与 loop 状态。
- 每轮最多处理 {managed_loop.get("max_items_per_cycle", 3)} 个事项。
- 达到 {managed_loop.get("max_iterations_per_run", 8)} 轮、重复失败、没有进展或触达返回点时停止。
- 验证方式：{join_items(verifier, language) if verifier else "运行聚焦项目验证"}。
- 需要先询问：{join_items(strings(safety.get("requires_approval_for")), language) or "不可逆、发布、数据或产品边界变更"}。
"""
    return f"""# Draft AGENTS.md Snippet: {candidate.get("name", candidate_id)}

This is a draft rule. Do not install it automatically; review it before copying into project instructions.

When `{candidate_id}` is triggered:

- Run mode: `{mode}` (`{level}` internally).
- Objective: {managed_loop.get("objective") or candidate.get("summary", "No objective recorded.")}
- Refresh the Change Map first each cycle: current X, target B, affected surfaces, regression / compatibility path, and rollout waves.
- Read and update the Change Map and loop state before stopping.
- Handle at most {managed_loop.get("max_items_per_cycle", 3)} item(s) per cycle.
- Stop after {managed_loop.get("max_iterations_per_run", 8)} iteration(s), repeated failure, no progress, or a return point.
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
