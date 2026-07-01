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

from sixloops.core.autonomy_contract import build_autonomy_contract
from sixloops.core.host_packets import build_host_manifest, render_host_packet, render_host_start
from sixloops.core.loop_contract import build_exit_contract
from sixloops.core.mode_policy import level_to_mode
from sixloops.core.progression_contract import build_progression_contract


DEFAULT_OUT_DIR = Path(".sixloops/goal-design")
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
    "auto",
    "read-only",
    "goal-loop",
    "isolated-draft",
    "verified-pr-draft",
    "scheduled-readonly",
    "scheduled-draft",
}
TEAM_MODES = {"auto", "none", "phased", "subagent-team"}


BASE_STATE_SCHEMA = {
    "status": "pending, discovering, active, verifying, done, blocked, needs_human, budget_stopped",
    "objective_hash": "Stable hash of objective and success criteria.",
    "change_map": "Durable X-to-B map: current state, target outcome, user perception, affected surfaces, regression plan, rollout waves, and decision packets.",
    "items": "Tracked work items with id, status, evidence, owner_role, verifier, and risk.",
    "attempts": "Attempt log with role, action, changed evidence, verification result, and timestamp.",
    "evidence_delta": "What changed since the previous cycle; CONTINUE requires changed or likely new verifier evidence.",
    "failure_signatures": "Repeated failure signatures and repeat counts.",
    "progress_metrics": "Evidence that changed, passed, failed, or stayed unchanged.",
    "human_queue": "Decisions, approvals, or missing context that require a human.",
    "budgets": "Item, iteration, time, token, or cost caps for the current run.",
    "progression_contract": "How each cycle records progress and proves that another cycle is justified.",
    "autonomy_contract": "How the model chooses the next bounded shot, controls roles, and avoids unnecessary human prompts.",
    "progression_log": "Per-cycle deltas: what changed, what evidence was gained, what remains, and why continue or stop.",
    "next_trigger": "The next condition, event, or user reply that should resume this loop.",
    "next_expected_evidence": "The new evidence the next cycle is expected to produce.",
    "next_verifier": "The verifier that can reject the next cycle's output.",
    "candidate_next_items": "Non-selected possible next steps; these are not the active cursor.",
    "blocking_human_queue": "Human decisions or approvals that block the selected next cursor.",
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


def first(items: list[str], default: str) -> str:
    return items[0] if items else default


def bullet(items: list[str]) -> str:
    if not items:
        return "- None."
    return "\n".join(f"- {item}" for item in items)


def numbered(items: list[str]) -> str:
    if not items:
        return "1. No repeatable steps recorded."
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def contains_cjk_text(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def design_language(design: dict) -> str:
    return "zh" if contains_cjk_text(str(design.get("goal", ""))) else "en"


ZH_START_CARD_TEXT = {
    "read-only": "只读",
    "low-risk edit": "低风险本地修改",
    "worktree draft": "隔离草稿",
    "PR draft": "PR 草稿",
    "phased": "分阶段执行",
    "subagent-team": "子代理团队",
    "none": "单代理执行",
    "Run the focused project verifier identified during the Decide step.": "运行决策阶段确定的聚焦项目验证。",
    "The requested outcome is produced with required verifier evidence.": "产出符合目标，并留下可复核的验收证据。",
    "Acceptance checks pass with required evidence.": "验收标准通过，并留下必要证据。",
    "Same failure repeats twice.": "同一失败重复两次。",
    "No evidence changes across two iterations.": "连续两轮证据没有变化。",
    "A return point is reached.": "触达需要交还用户的返回点。",
    "The verifier is unavailable or ambiguous.": "验收信号不可用或结论不清。",
    "Verifier is unavailable or ambiguous.": "验收信号不可用或结论不清。",
    "Objective is unchanged.": "目标没有变化。",
    "Next action stays inside approved scope.": "下一步仍在已批准范围内。",
    "A verifier can reject bad output.": "验收器能够拒绝错误产出。",
    "The Change Map can be updated or the next action can produce evidence for it.": "Change Map 可以被更新，或下一步能为它产生证据。",
    "New evidence changed or is likely from the next verifier.": "已有新证据变化，或下一轮验收可能产生新证据。",
    "next_cursor, next_expected_evidence, and next_verifier are concrete.": "`next_cursor`、`next_expected_evidence` 和 `next_verifier` 都是具体的。",
    "No blocking human_queue item prevents the selected next_cursor.": "没有阻塞型 `human_queue` 事项阻止已选择的 `next_cursor`。",
    "Risk stays below the approved mode and explicit return points.": "风险仍低于当前批准模式和明确返回点。",
    "The last cycle changed evidence, narrowed scope, reduced failures, or clarified the blocker.": "上一轮改变了证据、收窄了范围、减少了失败，或明确了阻塞点。",
    "Token, time, cost, or tool budget is reached.": "token、时间、成本或工具预算达到上限。",
    "Review required for human judgment or approval.": "需要人工判断或批准。",
    "Human decision required after the decision packet includes options, impact, regression path, and recommendation.": "决策包已经包含选项、影响、回归路径和推荐后，需要人工决定。",
    "Target routes render without blocking errors.": "目标路由能渲染，且没有阻塞性错误。",
    "Desktop/mobile screenshots or snapshots confirm the main path.": "桌面端和移动端截图或快照能确认主路径正常。",
    "Console and network checks show no blocking errors.": "控制台和网络检查没有阻塞性错误。",
    "i18n/copy output shows no missing key, raw key, or unintended fallback locale.": "i18n/文案没有缺失 key、裸 key 或非预期 fallback 语言。",
    "Read prior state, current goal, changed UI files, and project instructions.": "读取既有状态、当前目标、变更的 UI 文件和项目规则。",
    "Identify the smallest route/state/locale set that proves the change, including default locale and one non-default locale when relevant.": "找出能证明变更的最小路由、状态和语言集合；相关时覆盖默认语言和一个非默认语言。",
    "Choose at most 1-3 visible or user-path regressions by impact, risk, and verifier availability.": "按影响、风险和验收可用性，最多选择 1-3 个可见或用户路径回归。",
    "Apply only obvious, reversible UI fixes such as missing keys, broken routes, console errors, or text overflow inside the approved scope.": "只在已批准范围内修复明显、可回退的 UI 问题，例如缺失 key、路由损坏、控制台错误或文本溢出。",
    "Run focused static checks and browser verification, capture desktop/mobile screenshots when useful, inspect console/network/i18n fallback, and update state.": "运行聚焦静态检查和浏览器验证；必要时截取桌面/移动端截图，检查控制台、网络和 i18n fallback，并更新状态。",
    "Route URL list.": "路由 URL 列表。",
    "Locale list.": "语言列表。",
    "Screenshot paths or snapshot summaries.": "截图路径或快照摘要。",
    "Console/network result.": "控制台/网络检查结果。",
    "i18n/copy finding summary.": "i18n/文案发现摘要。",
    "Choose at most 3 item(s) per cycle.": "每轮最多选择 3 个事项。",
    "Prefer high-impact work with clear verifier evidence.": "优先处理影响高且验证证据清楚的事项。",
    "Defer work that needs product, release, data, or architecture judgment.": "需要产品、发布、数据或架构判断的事项先打包决策信息再交还用户。",
    "A checklist can remind an agent what to do, but it cannot preserve item state, verifier evidence, failure signatures, and the next cursor across repeated runs.": "清单只能提醒要做什么，不能在多轮运行之间保留事项状态、验收证据、失败签名和下一步位置。",
    "Execute roles sequentially in the current agent.": "在当前智能体内按顺序执行这些角色。",
    "Planner defines at most 1-3 items and verifier paths.": "规划者最多定义 1-3 个事项和对应验收路径。",
    "Maker roles act only inside approved scope.": "执行角色只能在已批准范围内行动。",
    "Reviewer/checker/verifier roles must be independent from maker output when possible.": "条件允许时，审查、检查和验收角色应独立于执行产出。",
    "Integrator updates state and returns DONE, CONTINUE, BLOCKED, NEEDS_HUMAN, or BUDGET_STOPPED.": "整合者更新状态，并返回 `DONE`、`CONTINUE`、`BLOCKED`、`NEEDS_HUMAN` 或 `BUDGET_STOPPED`。",
    "Planner": "规划者",
    "Architect": "架构师",
    "Frontend Maker": "前端执行者",
    "Backend Maker": "后端执行者",
    "Browser Verifier": "浏览器验收者",
    "Contract Verifier": "契约验收者",
    "Integration Verifier": "集成验收者",
    "Implementation Planner": "实现规划者",
    "Risk Reviewer": "风险审查者",
    "Maker Summarizer": "执行摘要者",
    "Checker": "检查者",
    "Verifier": "验收者",
    "Reviewer": "审查者",
    "Release Planner": "发布规划者",
    "CI Fixer": "CI 修复者",
    "Handoff Writer": "交接撰写者",
    "Triage Planner": "分诊规划者",
    "Issue Investigator": "问题调查者",
    "Fixer": "修复者",
    "Maker": "执行者",
    "Integrator": "整合者",
    "Updated STATE.json": "更新后的 `STATE.json`",
    "final status": "最终状态",
    "handoff summary": "交接摘要",
    "commands or checks run": "已运行命令或检查",
    "pass/fail evidence": "通过/失败证据",
    "untested risks": "未测试风险",
    "route list": "路由列表",
    "screenshot or snapshot evidence": "截图或快照证据",
    "console/network findings": "控制台/网络发现",
    "diff risks": "diff 风险",
    "missing verifier": "缺失的验收器",
    "approval gate": "审批门禁",
    "finding summary": "发现摘要",
    "recommended next action": "建议下一步",
    "evidence or blocker": "证据或阻塞点",
    "Merge role outputs into one state update and final status. Do not hide blockers.": "把各角色输出合并成一次状态更新和最终状态。不要隐藏阻塞点。",
    "Verify the real UI path with browser evidence, not visual guesses.": "用浏览器证据验证真实 UI 路径，不靠视觉猜测。",
    "Review the diff and plan against objective, project rules, and likely regressions.": "按目标、项目规则和可能回归审查 diff 与计划。",
    "Design has a bounded implementation path.": "设计具备范围清楚的实现路径。",
    "Each slice has a verifier.": "每个切片都有对应验收器。",
    "Ambiguities and human decisions are explicit.": "不确定点和人工决策点已明确。",
    "Prefer work that clarifies the X-to-B map, reduces blast radius, or produces verifier evidence.": "优先处理能澄清 X→B 图景、降低波及风险或产生验收证据的事项。",
    "When product, release, data, or architecture judgment appears, first produce a decision packet with options, impact, regression plan, and recommendation.": "遇到产品、发布、数据或架构判断时，先产出包含选项、影响、回归计划和推荐的决策包。",
    "Build or refresh the Change Map: current X, target B, user perception, affected surfaces, regression plan, and rollout waves.": "建立或刷新 Change Map：当前 X、目标 B、用户感知、波及面、回归计划和推进波次。",
    "Scan project evidence that can confirm or falsify the map; record file paths, commands, logs, and unknowns.": "扫描能确认或推翻图景的项目证据；记录文件路径、命令、日志和未知点。",
    "When judgment is needed, produce a decision packet with options, impact, regression path, and recommendation before returning for review.": "需要判断时，先产出包含选项、影响、回归路径和推荐的决策包，再交还用户。",
    "Update Change Map and STATE.json before choosing CONTINUE, DONE, NEEDS_HUMAN, BLOCKED, or BUDGET_STOPPED.": "选择 `CONTINUE`、`DONE`、`NEEDS_HUMAN`、`BLOCKED` 或 `BUDGET_STOPPED` 前，先更新 Change Map 和 `STATE.json`。",
    "End by writing the state delta and the next cursor before returning or continuing.": "返回或继续前，先写入状态变化和下一步位置。",
    "Act only on the selected item(s), then verify before choosing the next status.": "只处理已选事项，并在选择下一状态前完成验证。",
    "Turn prior blockers, repeated human corrections, or unfinished waves into candidate work before adding new work.": "新增事项前，先把上轮阻塞、重复人工纠正或未完成波次转成候选事项。",
    "change_map_delta": "`change_map_delta`",
    "evidence_delta": "`evidence_delta`",
    "selected_items": "`selected_items`",
    "completed_items": "`completed_items`",
    "blocked_items": "`blocked_items`",
    "next_cursor": "`next_cursor`",
    "next_trigger": "`next_trigger`",
    "next_expected_evidence": "`next_expected_evidence`",
    "next_verifier": "`next_verifier`",
    "candidate_next_items": "`candidate_next_items`",
    "blocking_human_queue": "`blocking_human_queue`",
    "human_friction_delta": "`human_friction_delta`",
    "next_cursor names the exact unfinished wave, item, file, route, log, check, or decision packet.": "`next_cursor` 必须指出具体未完成波次、事项、文件、路由、日志、检查或决策包。",
    "next_cursor names one selected path, not mutually exclusive alternatives.": "`next_cursor` 必须是一个已选择路径，不能是互斥备选项列表。",
    "next_expected_evidence states what new verifier evidence the next cycle should produce.": "`next_expected_evidence` 必须说明下一轮应产生什么新的验收证据。",
    "next_verifier can reject bad output for the next action.": "`next_verifier` 必须能拒绝下一步的错误产出。",
    "blocking_human_queue is empty, or the selected next_cursor is explicitly non-blocking.": "`blocking_human_queue` 必须为空，或已选择的 `next_cursor` 明确不受其阻塞。",
    "human_friction_delta records whether this cycle removed or added repeated user work.": "`human_friction_delta` 必须记录本轮减少还是增加了重复人工解释。",
    "The next action would repeat the same observation without new evidence.": "下一步只是重复观察，不能产生新证据。",
    "The next cursor is vague, such as 'continue later' or 'keep working'.": "下一步位置含糊，例如“稍后继续”或“继续做”。",
    "The next cursor contains unresolved alternatives instead of one selected path.": "下一步位置包含未解决的备选分支，而不是一个已选择路径。",
    "No verifier can reject the next action.": "没有验收器能拒绝下一步动作。",
    "Human judgment or a stronger approval mode blocks the selected next action.": "人工判断或更高批准模式正在阻塞已选择的下一步。",
    "Finish every cycle with: what changed, what evidence was gained, what remains, the exact next cursor, the next expected evidence, and whether another cycle is justified.": "每轮结束时写清：发生了什么变化、得到什么证据、还剩什么、精确下一步位置、下一轮预期证据，以及下一轮是否值得继续。",
    "When multiple next actions are plausible, rank them by user value, verifier availability, reversibility, risk, and progress toward the Change Map.": "存在多个可行下一步时，按用户价值、验收可用性、可回退性、风险和对 Change Map 的推进程度排序。",
    "Choose the highest-ranked action that is inside the approved mode and has a verifier; do not ask the user to choose ordinary engineering next steps.": "选择已批准模式内、且有验收器的最高排序动作；不要让用户替模型选择普通工程下一步。",
    "If the highest-value action is blocked by human approval or product judgment, select the best non-blocking evidence or cleanup action instead.": "如果最高价值动作被人工批准或产品判断阻塞，就改选最佳的非阻塞证据扫描或清理动作。",
    "Return to the user only when all useful non-blocking actions are exhausted or the selected action requires human judgment or stronger approval.": "只有所有有用的非阻塞动作都耗尽，或已选择动作需要人工判断/更高授权时，才交还用户。",
    "Prefer a coherent sequence of bounded shots over a single oversized one-shot.": "优先用连贯的多个有边界步骤，而不是一个过大的 one-shot。",
    "After each shot, use verifier evidence to update candidate_next_items, choose the next shot, and continue while risk and budget remain in scope.": "每一步后，用验收证据更新 `candidate_next_items`，选择下一步；只要风险和预算仍在范围内就继续。",
    "Do not repeat a shot unless the next attempt uses new evidence, a narrower hypothesis, or a different verifier.": "不要重复同一步，除非下一次使用了新证据、更窄假设或不同验收器。",
    "Treat model judgment as the selector for the next bounded shot; treat deterministic checks as rejection gates.": "把模型判断作为下一步有边界动作的选择器，把确定性检查作为拒绝门。",
    "Start planner/checker/verifier roles when they can reduce uncertainty or reject output independently.": "当规划者、检查者或验收者能降低不确定性或独立拒绝产出时启动它们。",
    "Start maker roles only inside explicit edit scope and stop them after the selected shot is verified or blocked.": "执行角色只在明确编辑范围内启动，并在已选步骤被验证或阻塞后停止。",
    "Do not keep subagents running after their evidence, patch, review, or verifier output has been integrated into state.": "子角色的证据、补丁、审查或验收输出整合进状态后，不要继续保留其运行。",
    "Ask the user only for product, architecture, release, security, data, billing, permission, production, irreversible, or scope-expanding decisions.": "只在产品、架构、发布、安全、数据、计费、权限、生产、不可逆或扩范围决策时询问用户。",
    "Before asking, package options, impact, regression path, recommendation, and the best non-blocking action already attempted or rejected.": "询问前，先打包选项、影响、回归路径、推荐，以及已尝试或已拒绝的最佳非阻塞动作。",
    "Do not ask for ordinary prioritization when the model can choose using evidence, verifier availability, risk, and approved mode.": "当模型能根据证据、验收可用性、风险和批准模式选择时，不要把普通优先级问题交给用户。",
    "Read prior state, goal, constraints, and relevant project instructions.": "读取既有状态、目标、约束和相关项目规则。",
    "Map affected modules, contracts, risks, and dependency order.": "映射受影响模块、契约、风险和依赖顺序。",
    "Choose at most 1-3 design decisions or implementation slices with verifiers.": "最多选择 1-3 个带验收器的设计决策或实现切片。",
    "Draft the smallest reversible plan or local proof before broad refactors.": "在大范围重构前，先草拟最小可回退方案或本地证明。",
    "Review the plan against risks and update state with next action or return point.": "按风险审查方案，并用下一步动作或返回点更新状态。",
    "Same visible failure repeats twice.": "同一可见问题重复出现两次。",
    "No new screenshot, console, network, or i18n evidence appears across two iterations.": "连续两轮没有新的截图、控制台、网络或 i18n 证据。",
    "The browser verifier or dev server is unavailable.": "浏览器验证器或开发服务器不可用。",
    "A product copy, translation tone, visual direction, route behavior, or scope-expansion decision is required.": "需要产品文案、翻译语气、视觉方向、路由行为或范围扩张判断。",
    "visual direction changes": "视觉方向变更",
    "product copy decisions": "产品文案决策",
    "translation tone or terminology decisions": "翻译语气或术语决策",
    "route behavior changes": "路由行为变更",
    "auth or data fixture changes": "认证或数据夹具变更",
    "production action": "生产环境操作",
    "destructive changes": "破坏性变更",
    "large refactor": "大范围重构",
    "schema migration": "schema 迁移",
    "public API change": "公开 API 变更",
    "product tradeoff": "产品取舍",
    "scope expansion": "范围扩张",
    "irreversible changes": "不可逆变更",
}


def start_card_text(value: str, language: str) -> str:
    if language != "zh":
        return value
    if value in ZH_START_CARD_TEXT:
        return ZH_START_CARD_TEXT[value]
    review_match = re.fullmatch(r"Review required for (.+)\.", value)
    if review_match:
        return f"需要审查：{start_card_text(review_match.group(1), language)}。"
    approval_match = re.fullmatch(r"Approval required for (.+) after options, impact, and regression evidence are recorded\.", value)
    if approval_match:
        return f"需要批准：{start_card_text(approval_match.group(1), language)}。批准前必须已记录选项、影响和回归证据。"
    fewer_items = re.fullmatch(r"Fewer than (\d+) item\(s\) are active in this cycle\.", value)
    if fewer_items:
        return f"本轮活跃事项少于 {fewer_items.group(1)} 个。"
    fewer_iterations = re.fullmatch(r"Fewer than (\d+) iteration\(s\) have run\.", value)
    if fewer_iterations:
        return f"已运行轮数少于 {fewer_iterations.group(1)} 轮。"
    more_items = re.fullmatch(r"More than (\d+) item\(s\) would be required in one cycle\.", value)
    if more_items:
        return f"单轮需要超过 {more_items.group(1)} 个事项。"
    iterations_reached = re.fullmatch(r"(\d+) iteration\(s\) are reached\.", value)
    if iterations_reached:
        return f"达到 {iterations_reached.group(1)} 轮上限。"
    if value.startswith("This goal is loop-shaped because"):
        return "这个目标适合做成 loop，因为每轮都需要发现输入、选择少量高价值事项、验证结果、更新状态，并在明确返回点交还。"
    coordination_match = re.fullmatch(r"Use `(.+)` coordination by default; spawn or emulate only the roles needed for the selected shot\.", value)
    if coordination_match:
        return f"默认使用 `{coordination_match.group(1)}` 协作；只启动或模拟已选择步骤所需的角色。"
    read_state_match = re.fullmatch(r"Read `(.+)`, the goal, the Change Map, and the verifier before choosing work\.", value)
    if read_state_match:
        return f"选择事项前，读取 `{read_state_match.group(1)}`、目标、Change Map 和验收器。"
    choose_match = re.fullmatch(r"Choose at most (\d+) item\(s\) that can change evidence, narrow risk, or clarify a blocker\.", value)
    if choose_match:
        return f"最多选择 {choose_match.group(1)} 个能改变证据、收窄风险或澄清阻塞的事项。"
    if value.startswith("Start as "):
        return "先从当前批准模式启动；只有在验收证据和人工接受度稳定后，才升级到更高自动化。"
    if value.startswith("Domain `"):
        return "当前领域、协作方式和内部级别适合先试运行；多轮产出被接受后再考虑升级。"
    handle_role = re.fullmatch(r"Handle the (.+) role for this (.+) goal\.", value)
    if handle_role:
        domain = {"frontend": "前端", "backend": "后端", "fullstack": "全栈", "architecture": "架构", "review": "审查", "delivery": "交付", "maintenance": "维护"}.get(handle_role.group(2), handle_role.group(2))
        return f"负责这个{domain}目标中的{start_card_text(handle_role.group(1), language)}角色。"
    return value


def start_card_items(items: list[str], language: str) -> list[str]:
    return [start_card_text(item, language) for item in items]


def first_cycle_card(design: dict) -> str:
    language = design_language(design)
    managed_loop = design["managed_loop"]
    contract = managed_loop["completion_contract"]
    max_items = managed_loop["max_items_per_cycle"]
    max_iterations = managed_loop["max_iterations_per_run"]
    verifier = start_card_text(first(contract["verifier_commands"], "Run the focused verifier."), language).rstrip("。.;；")
    mode = start_card_text(level_to_mode(design["adoption_level"]), language)
    approval_separator = "、" if language == "zh" else ", "
    approvals = approval_separator.join(start_card_items(design["safety"]["requires_approval_for"], language))

    if language == "zh":
        return "\n".join(
            [
                f"1. 建图：读取 `STATE.json`、Change Map、当前目标、项目规则和输入；先更新 X→B、波及面和回归路径。",
                f"2. 选择：本轮最多选择 {max_items} 个能推进图景、降低风险或产生验收证据的事项。",
                f"3. 执行：只按“{mode}”允许的动作处理有直接证据支撑的事项；遇到判断题先产出决策包。",
                f"4. 验收 / 交还：{verifier}；更新 Change Map、`STATE.json`、下一步位置和下一轮预期证据；达到 {max_iterations} 轮、无可推进证据、触达返回点，或需要{approvals}时返回。",
            ]
        )

    return "\n".join(
        [
            "1. Map: read `STATE.json`, the Change Map, the current goal, project rules, and inputs; refresh X-to-B, affected surfaces, and regression path.",
            f"2. Select: choose at most {max_items} item(s) that advance the map, reduce risk, or produce verifier evidence.",
            f"3. Act: work only inside `{level_to_mode(design['adoption_level'])}` with directly evidenced items; turn judgment into a decision packet first.",
            f"4. Verify / Deliver: {verifier}; update Change Map, `STATE.json`, next cursor, and next expected evidence; return after {max_iterations} iterations, no bounded evidence step remains, a return point is reached, or approval is needed for: {approvals}.",
        ]
    )


def read_goal(args: argparse.Namespace) -> str:
    if args.goal and args.goal_file:
        raise ValueError("Pass either --goal or --goal-file, not both.")
    if args.goal_file:
        return Path(args.goal_file).read_text(encoding="utf-8").strip()
    if args.goal:
        return args.goal.strip()
    raise ValueError("Pass --goal or --goal-file.")


def read_model_design(path: str | None) -> dict:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("--model-design-file must be a JSON object.")
    return data


def model_choice(model_design: dict, key: str, allowed: set[str]) -> str:
    value = str(model_design.get(key, "")).strip()
    return value if value in allowed and value != "auto" else ""


def infer_domain(goal: str, requested: str) -> str:
    if requested != "auto":
        return requested
    return "general"


def resolve_level(goal: str, requested: str) -> str:
    if requested != "auto":
        return requested
    return "read-only"


def resolve_team_mode(domain: str, requested: str, goal: str) -> str:
    if requested != "auto":
        return requested
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
                "Review the plan against risks and update state with next action or return point.",
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
            "verification": ["The requested outcome is produced with required verifier evidence."],
            "approval": ["irreversible changes", "production action", "scope expansion"],
            "team": ["planner", "maker", "verifier", "reviewer", "integrator"],
        },
    }
    return profiles.get(domain, profiles["general"])


def missing_change_map(language: str) -> dict:
    if language == "zh":
        return {
            "current_x": "缺少模型写入的 current_x。",
            "target_b": "缺少模型写入的 target_b。",
            "user_perception": "缺少模型写入的 user_perception。",
            "transformation_thesis": "缺少模型写入的 transformation_thesis。",
            "affected_surfaces": ["缺少模型写入的 affected_surfaces。"],
            "regression_plan": ["缺少模型写入的 regression_plan。"],
            "rollback_or_compatibility": ["缺少模型写入的 rollback_or_compatibility。"],
            "research_questions": ["缺少模型写入的 research_questions。"],
            "waves": ["缺少模型写入的 waves。"],
            "decision_packet_required_when": ["缺少模型写入的 decision_packet_required_when。"],
        }
    return {
        "current_x": "Model-authored current_x was not supplied.",
        "target_b": "Model-authored target_b was not supplied.",
        "user_perception": "Model-authored user_perception was not supplied.",
        "transformation_thesis": "Model-authored transformation_thesis was not supplied.",
        "affected_surfaces": ["Model-authored affected_surfaces was not supplied."],
        "regression_plan": ["Model-authored regression_plan was not supplied."],
        "rollback_or_compatibility": ["Model-authored rollback_or_compatibility was not supplied."],
        "research_questions": ["Model-authored research_questions was not supplied."],
        "waves": ["Model-authored waves was not supplied."],
        "decision_packet_required_when": ["Model-authored decision_packet_required_when was not supplied."],
    }


def normalize_change_map(raw: object, language: str) -> dict:
    fallback = missing_change_map(language)
    source = raw if isinstance(raw, dict) else {}
    return {
        "current_x": str(source.get("current_x") or fallback["current_x"]),
        "target_b": str(source.get("target_b") or fallback["target_b"]),
        "user_perception": str(source.get("user_perception") or fallback["user_perception"]),
        "transformation_thesis": str(source.get("transformation_thesis") or fallback["transformation_thesis"]),
        "affected_surfaces": strings(source.get("affected_surfaces")) or fallback["affected_surfaces"],
        "regression_plan": strings(source.get("regression_plan")) or fallback["regression_plan"],
        "rollback_or_compatibility": strings(source.get("rollback_or_compatibility")) or fallback["rollback_or_compatibility"],
        "research_questions": strings(source.get("research_questions")) or fallback["research_questions"],
        "waves": strings(source.get("waves")) or fallback["waves"],
        "decision_packet_required_when": strings(source.get("decision_packet_required_when")) or fallback["decision_packet_required_when"],
    }


def build_change_map(goal: str, model_design: dict) -> dict:
    is_zh = contains_cjk_text(goal)
    return normalize_change_map(model_design.get("change_map"), "zh" if is_zh else "en")


def change_map_cycle_steps(profile: dict) -> list[str]:
    return [
        "Build or refresh the Change Map: current X, target B, user perception, affected surfaces, regression plan, and rollout waves.",
        "Scan project evidence that can confirm or falsify the map; record file paths, commands, logs, and unknowns.",
        *profile["cycle_steps"],
        "When judgment is needed, produce a decision packet with options, impact, regression path, and recommendation before returning for review.",
        "Update Change Map and STATE.json before choosing CONTINUE, DONE, NEEDS_HUMAN, BLOCKED, or BUDGET_STOPPED.",
    ]


def render_change_map(change_map: dict, language: str) -> str:
    if language == "zh":
        return f"""- 当前 X：{change_map["current_x"]}
- 目标 B：{change_map["target_b"]}
- 用户感知：{change_map["user_perception"]}
- 转换假设：{change_map["transformation_thesis"]}

波及面：

{bullet(start_card_items(change_map["affected_surfaces"], language))}

回归 / 兼容：

{bullet(start_card_items(change_map["regression_plan"] + change_map["rollback_or_compatibility"], language))}

推进波次：

{numbered(start_card_items(change_map["waves"], language))}

需要人工决策前，先补齐这些问题：

{bullet(start_card_items(change_map["research_questions"], language))}

决策包触发：

{bullet(start_card_items(change_map["decision_packet_required_when"], language))}
"""
    return f"""- Current X: {change_map["current_x"]}
- Target B: {change_map["target_b"]}
- User perception: {change_map["user_perception"]}
- Transformation thesis: {change_map["transformation_thesis"]}

Affected surfaces:

{bullet(change_map["affected_surfaces"])}

Regression / compatibility:

{bullet(change_map["regression_plan"] + change_map["rollback_or_compatibility"])}

Rollout waves:

{numbered(change_map["waves"])}

Answer before returning for human judgment:

{bullet(change_map["research_questions"])}

Decision packet triggers:

{bullet(change_map["decision_packet_required_when"])}
"""


def render_progression_contract(contract: dict, language: str) -> str:
    if language == "zh":
        return f"""推进节奏：

{bullet(start_card_items(contract["rhythm"], language))}

每轮必须写入：

{bullet(start_card_items(contract["state_updates_required"], language))}

继续下一轮前必须具备：

{bullet(start_card_items(contract["continue_requires"], language))}

遇到这些情况不要继续，改为停止或交还：

{bullet(start_card_items(contract["stop_instead_of_continue_when"], language))}

交接规则：

- {start_card_text(contract["handoff_rule"], language)}
"""
    return f"""Rhythm:

{bullet(contract["rhythm"])}

State updates required every cycle:

{bullet(contract["state_updates_required"])}

Continue only after recording:

{bullet(contract["continue_requires"])}

Stop instead of continuing when:

{bullet(contract["stop_instead_of_continue_when"])}

Handoff rule:

- {contract["handoff_rule"]}
"""


def render_autonomy_contract(contract: dict, language: str) -> str:
    if language == "zh":
        return f"""自主决策：

{bullet(start_card_items(contract["decision_policy"], language))}

自我迭代：

{bullet(start_card_items(contract["self_iteration_policy"], language))}

子角色启停：

{bullet(start_card_items(contract["subagent_control"], language))}

交还用户：

{bullet(start_card_items(contract["human_return_policy"], language))}
"""
    return f"""Autonomous decision:

{bullet(contract["decision_policy"])}

Self-iteration:

{bullet(contract["self_iteration_policy"])}

Subagent control:

{bullet(contract["subagent_control"])}

Return to human:

{bullet(contract["human_return_policy"])}
"""


def build_rationale(goal: str, domain: str, profile: dict, level: str, team_mode: str, model_design: dict) -> dict:
    raw = model_design.get("rationale") if isinstance(model_design.get("rationale"), dict) else {}
    def supplied(key: str, fallback: str) -> str:
        return str(raw.get(key) or model_design.get(key) or fallback)

    source_summary = ", ".join(profile["discovery_sources"][:3])
    trigger_summary = "; ".join(item.rstrip(".") for item in profile["trigger"][:2])
    mode = level_to_mode(level)
    return {
        "why_this_loop": supplied("why_this_loop",
            f"This goal is loop-shaped because each cycle must discover inputs such as {source_summary}; "
            "then select only a few high-value items, verify the result, update state, and stop at explicit review boundaries."
        ),
        "why_not_smaller": supplied("why_not_smaller",
            "A checklist can remind an agent what to do, but it cannot preserve item state, verifier evidence, "
            "failure signatures, and the next cursor across repeated runs."
        ),
        "why_not_more_autonomous": supplied("why_not_more_autonomous",
            f"Start as {mode} because the trigger is {trigger_summary or 'user delegation'}; higher-impact actions "
            "still need the recorded approval points before scope expansion, irreversible changes, or production work."
        ),
        "fit_summary": supplied("fit_summary",
            f"Domain `{domain}` with `{team_mode}` team mode and `{level}` internal level; promote only after accepted "
            "runs produce reliable verifier evidence."
        ),
    }


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
        "risk-reviewer": ["risk map", "human decisions", "reversible next slice"],
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
            f"Objective: {goal} Return only your role output, evidence, blockers, and next action. "
            "Do not expand scope. Do not perform high-impact actions without explicit approval."
        ),
    }


def build_design(args: argparse.Namespace) -> dict:
    goal = read_goal(args)
    model_design = read_model_design(args.model_design_file)
    domain = args.domain if args.domain != "auto" else model_choice(model_design, "domain", DOMAINS) or infer_domain(goal, args.domain)
    profile = base_profile(domain)
    team_mode = args.team_mode if args.team_mode != "auto" else model_choice(model_design, "team_mode", TEAM_MODES) or resolve_team_mode(domain, args.team_mode, goal)
    loop_id = args.loop_id or str(model_design.get("loop_id") or "").strip() or slug(f"{domain}-{compact(goal, 40)}-{short_hash(goal)}")
    name = args.name or str(model_design.get("name") or "").strip() or f"{profile['archetype'].replace('-', ' ').title()} Loop"
    level = args.level if args.level != "auto" else model_choice(model_design, "level", LEVELS) or resolve_level(goal, args.level)
    rationale = build_rationale(goal, domain, profile, level, team_mode, model_design)
    max_items = max(1, args.max_items)
    max_iterations = max(1, args.max_iterations)
    team_roles = [role_prompt(role_id, goal, domain) for role_id in profile["team"]]
    state_file = "STATE.json"
    approval_boundary = list(dict.fromkeys(profile["approval"] + ["scope expansion", "irreversible changes"]))
    success_criteria = args.success_criteria or profile["verification"]
    verifier_commands = args.verifier or profile["verification"]
    change_map = build_change_map(goal, model_design)
    reject_conditions = profile.get(
        "reject_conditions",
        [
            "Same failure repeats twice.",
            "No evidence changes across two iterations.",
            "A return point is reached.",
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
    progression_contract = build_progression_contract(
        max_items=max_items,
        max_iterations=max_iterations,
        state_file=state_file,
    )
    autonomy_contract = build_autonomy_contract(team_mode=team_mode)

    managed_loop = {
        "objective": goal,
        "heartbeat": "goal" if not level.startswith("scheduled") else "scheduled",
        "recommended_maturity": level,
        "cadence_or_trigger": profile["trigger"],
        "discovery_sources": profile["discovery_sources"],
        "state_file": state_file,
        "state_schema": BASE_STATE_SCHEMA,
        "change_map": change_map,
        "cycle_steps": change_map_cycle_steps(profile),
        "selection_policy": [
            f"Choose at most {max_items} item(s) per cycle.",
            "Prefer work that clarifies the X-to-B map, reduces blast radius, or produces verifier evidence.",
            "When product, release, data, or architecture judgment appears, first produce a decision packet with options, impact, regression plan, and recommendation.",
        ],
        "max_items_per_cycle": max_items,
        "max_iterations_per_run": max_iterations,
        "completion_contract": {
            "success_criteria": success_criteria,
            "verifier_commands": verifier_commands,
            "evaluator_agent": "Use deterministic checks first; use a reviewer or verifier role when commands cannot decide.",
            "pass_evidence_required": pass_evidence_required,
            "reject_conditions": reject_conditions,
            "no_progress_policy": "If evidence stops changing, try to convert the unknown into a narrower scan or decision packet; stop only when no bounded next action can improve the Change Map or verifier evidence.",
        },
        "loop_exit_contract": loop_exit_contract,
        "progression_contract": progression_contract,
        "autonomy_contract": autonomy_contract,
        "change_policy": (
            "Read-only until edit scope is approved. For draft-producing levels, use a local reversible change set "
            "or isolated branch/worktree. Do not push, merge, deploy, migrate, delete data, or change credentials without approval."
        ),
        "deliverables": ["Updated Change Map", "Updated STATE.json", "status summary", "verifier evidence", "patch/PR draft or decision packet when applicable"],
        "resume_policy": "Read STATE.json and the Change Map first; continue unresolved waves, decisions, or active items before selecting new work.",
        "failure_policy": "Record repeated failures, missing inputs, and human decisions. Convert ambiguity into a bounded evidence scan or decision packet before stopping for review.",
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
        "change_map": change_map,
        **rationale,
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
        "change_map": design["change_map"],
        "success_criteria": contract["success_criteria"],
        "reject_conditions": contract["reject_conditions"],
        "loop_exit_contract": managed_loop["loop_exit_contract"],
        "progression_contract": managed_loop["progression_contract"],
        "autonomy_contract": managed_loop["autonomy_contract"],
        "approval_boundary": design["safety"]["requires_approval_for"],
        "items": [],
        "attempts": [],
        "active_wave": None,
        "decision_packets": [],
        "evidence_delta": [],
        "progression_log": [],
        "failure_signatures": [],
        "progress_metrics": [],
        "human_queue": [],
        "budgets": {
            "max_items_per_cycle": managed_loop["max_items_per_cycle"],
            "max_iterations_per_run": managed_loop["max_iterations_per_run"],
        },
        "next_trigger": None,
        "next_expected_evidence": None,
        "next_verifier": None,
        "candidate_next_items": [],
        "blocking_human_queue": [],
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
    }


def render_goal(design: dict) -> str:
    managed_loop = design["managed_loop"]
    contract = managed_loop["completion_contract"]
    exit_contract = managed_loop["loop_exit_contract"]
    progression_contract = managed_loop["progression_contract"]
    autonomy_contract = managed_loop["autonomy_contract"]
    mode = level_to_mode(design["adoption_level"])
    language = design_language(design)
    mode_display = start_card_text(mode, language)
    team_display = start_card_text(design["team_mode"], language)
    intro = (
        "先看改造图景和执行合同。确认后，智能体按 `RUN.md` 运行、按 `VERIFY.md` 验收，并在触达返回点时交还给你。"
        if language == "zh"
        else "Start with the Change Map and execution contract. After confirmation, the agent follows `RUN.md`, verifies with `VERIFY.md`, and returns at explicit return points."
    )
    contract_label = "执行合同" if language == "zh" else "Execution Contract"
    map_label = "改造图景" if language == "zh" else "Change Map"
    reply_label = "推荐回复" if language == "zh" else "Recommended reply"
    reply_text = "开始执行" if language == "zh" else "start"
    mode_label = "运行模式" if language == "zh" else "Mode"
    team_label = "协作方式" if language == "zh" else "Team mode"
    goal_label = "目标" if language == "zh" else "Goal"
    will_do_label = "我会做" if language == "zh" else "I will do"
    verify_label = "验证方式" if language == "zh" else "Verifier"
    stop_label = "停止 / 返回点" if language == "zh" else "Stop / return point"
    ask_label = "完成前需要明确批准" if language == "zh" else "Explicit approval before"
    if language == "zh":
        return f"""# {design["name"]}

{intro}

## {map_label}

{render_change_map(design["change_map"], language)}

## {contract_label}

- {reply_label}: `{reply_text}`
- {mode_label}: {mode_display}
- {team_label}: {team_display}

{goal_label}:

{design["goal"]}

{will_do_label}:

{first_cycle_card(design)}

{verify_label}:

{bullet(start_card_items(contract["verifier_commands"], language))}

{stop_label}:

{bullet(start_card_items(contract["reject_conditions"], language))}

{ask_label}:

{bullet(start_card_items(design["safety"]["requires_approval_for"], language))}

## 为什么是这个 loop

- 为什么值得跑：{start_card_text(design["why_this_loop"], language)}
- 为什么不只是更小机制：{start_card_text(design["why_not_smaller"], language)}
- 为什么不更自动化：{start_card_text(design["why_not_more_autonomous"], language)}
- 适配判断：{start_card_text(design["fit_summary"], language)}

## Loop 形态

- 领域：`{design["domain"]}`
- 类型：`{design["loop_archetype"]}`
- 启动模式：`{mode}`
- 内部级别：`{design["adoption_level"]}`
- 协作方式：`{design["team_mode"]}`

## 验收标准

{bullet(start_card_items(contract["success_criteria"], language))}

## 循环步骤

{numbered(start_card_items(managed_loop["cycle_steps"], language))}

## 推进节奏

{render_progression_contract(progression_contract, language)}

## 自主决策

{render_autonomy_contract(autonomy_contract, language)}

## 选择规则

{bullet(start_card_items(managed_loop["selection_policy"], language))}

## 验证方式

{bullet(start_card_items(contract["verifier_commands"], language))}

必须留下的通过证据：

{bullet(start_card_items(contract["pass_evidence_required"], language))}

## 停止条件

{bullet(start_card_items(contract["reject_conditions"], language))}

还要在达到 `{managed_loop["max_iterations_per_run"]}` 轮、重复无进展或触达返回点时停止。

## 退出协议

仅在以下条件成立时继续：

{bullet(start_card_items(exit_contract["continue_only_if"], language))}

返回 `DONE` 的条件：

{bullet(start_card_items(exit_contract["done_when"], language))}

交还给用户的条件：

{bullet(start_card_items(exit_contract["needs_human_when"], language))}

返回 `BLOCKED` 的条件：

{bullet(start_card_items(exit_contract["blocked_when"], language))}

返回 `BUDGET_STOPPED` 的条件：

{bullet(start_card_items(exit_contract["budget_stopped_when"], language))}

## 状态

- 状态文件：`STATE.json`
- 工作前先读状态。
- 返回任何最终状态前必须更新状态。

## 明确批准点

{bullet(start_card_items(design["safety"]["requires_approval_for"], language))}

## 最终状态

结束前只能返回一个内部状态：`DONE`、`CONTINUE`、`BLOCKED`、`NEEDS_HUMAN` 或 `BUDGET_STOPPED`。
面向用户说明时，把 `NEEDS_HUMAN` 写成“交还给用户判断”。

## 首轮复盘

下一次运行前，在 `STATE.json` 记录：这个 loop 是否减少了重复人工纠正、是否产生误报、是否过度依赖人工判断、是否应该改成 skill/checklist，或是否已有足够被接受的产出。
"""
    return f"""# {design["name"]}

{intro}

## {map_label}

{render_change_map(design["change_map"], language)}

## {contract_label}

- {reply_label}: `{reply_text}`
- {mode_label}: {mode_display}
- {team_label}: {team_display}

{goal_label}:

{design["goal"]}

{will_do_label}:

{first_cycle_card(design)}

{verify_label}:

{bullet(start_card_items(contract["verifier_commands"], language))}

{stop_label}:

{bullet(start_card_items(contract["reject_conditions"], language))}

{ask_label}:

{bullet(start_card_items(design["safety"]["requires_approval_for"], language))}

## Objective

{design["goal"]}

## Why This Loop

- Why this loop: {design["why_this_loop"]}
- Why not smaller: {design["why_not_smaller"]}
- Why not more autonomous: {design["why_not_more_autonomous"]}
- Fit summary: {design["fit_summary"]}

## Loop Shape

- Domain: `{design["domain"]}`
- Archetype: `{design["loop_archetype"]}`
- Start mode: `{mode}`
- Internal level: `{design["adoption_level"]}`
- Team mode: `{design["team_mode"]}`

## Acceptance Checks

{bullet(contract["success_criteria"])}

## Cycle

{numbered(managed_loop["cycle_steps"])}

## Progression Contract

{render_progression_contract(progression_contract, language)}

## Autonomy Contract

{render_autonomy_contract(autonomy_contract, language)}

## Selection Policy

{bullet(managed_loop["selection_policy"])}

## Verification

{bullet(contract["verifier_commands"])}

Required pass evidence:

{bullet(contract["pass_evidence_required"])}

## Stop Conditions

{bullet(contract["reject_conditions"])}

Also stop after `{managed_loop["max_iterations_per_run"]}` iteration(s), repeated no-progress, or a return point.

## Exit Contract

Continue only if:

{bullet(exit_contract["continue_only_if"])}

Return `DONE` when:

{bullet(exit_contract["done_when"])}

Return to user when:

{bullet(exit_contract["needs_human_when"])}

Return `BLOCKED` when:

{bullet(exit_contract["blocked_when"])}

Return `BUDGET_STOPPED` when:

{bullet(exit_contract["budget_stopped_when"])}

## State

- State file: `STATE.json`
- Read state before work.
- Update state before returning any final status.

## Explicit Approval Points

{bullet(design["safety"]["requires_approval_for"])}

## Final Status

Return exactly one internal status: `DONE`, `CONTINUE`, `BLOCKED`, `NEEDS_HUMAN`, or `BUDGET_STOPPED`.
In user-facing copy, treat `NEEDS_HUMAN` as return-to-user.

## First Run Retro

Before the next run, update `STATE.json` with whether this loop reduced repeated human correction,
created false positives, required too much human judgment, should become a skill/checklist,
or has enough accepted output to keep its current autonomy level.
"""


def render_team(design: dict) -> str:
    team = design["subagent_team"]
    if team["mode"] == "none":
        return "# 团队\n\n这个 loop 不启用团队模式。\n" if design_language(design) == "zh" else "# Team\n\nTeam mode is disabled for this loop.\n"
    if design_language(design) == "zh":
        blocks = [
            "# 团队",
            "",
            f"模式：`{team['mode']}`",
            "",
            start_card_text(team["activation_rule"], "zh"),
            "",
            "## 协作规则",
            "",
            bullet(start_card_items(team["coordination"], "zh")),
        ]
        domain_label = {"frontend": "前端", "backend": "后端", "fullstack": "全栈", "architecture": "架构", "review": "审查", "delivery": "交付", "maintenance": "维护"}.get(design["domain"], design["domain"])
        for role in team["roles"]:
            title = start_card_text(role["title"], "zh")
            prompt = (
                f"你是 SixLoops {domain_label}目标的{title}。目标：{design['goal']} "
                "只返回本角色输出、证据、阻塞点和下一步。不要扩大范围。没有明确批准时，不执行高影响动作。"
            )
            blocks.extend(
                [
                    "",
                    f"## {title}",
                    "",
                    f"- 角色 id：`{role['id']}`",
                    f"- 可修改文件：`{str(role['may_modify_files']).lower()}`",
                    f"- 任务：{start_card_text(role['mission'], 'zh')}",
                    "",
                    "输出：",
                    "",
                    bullet(start_card_items(role["outputs"], "zh")),
                    "",
                    "提示词：",
                    "",
                    "```text",
                    prompt,
                    "```",
                ]
            )
        return "\n".join(blocks) + "\n"
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
    exits = design["managed_loop"]["loop_exit_contract"]
    managed_loop = design["managed_loop"]
    contract = managed_loop["completion_contract"]
    progression_contract = managed_loop["progression_contract"]
    autonomy_contract = managed_loop["autonomy_contract"]
    mode = level_to_mode(design["adoption_level"])
    language = design_language(design)
    mode_display = start_card_text(mode, language)
    team_display = start_card_text(design["team_mode"], language)
    intro = (
        "这个目录是一份可执行 loop 运行包。先看 `GOAL.md` 的改造图景和执行合同，再按 `RUN.md` 运行、按 `VERIFY.md` 验收。"
        if language == "zh"
        else "This folder contains an executable loop harness. Start with the `GOAL.md` Change Map and execution contract, then run with `RUN.md` and verify with `VERIFY.md`."
    )
    contract_label = "执行合同" if language == "zh" else "Execution Contract"
    map_label = "改造图景" if language == "zh" else "Change Map"
    mode_label = "运行模式" if language == "zh" else "Mode"
    team_label = "协作方式" if language == "zh" else "Team mode"
    goal_label = "目标" if language == "zh" else "Goal"
    will_do_label = "我会做" if language == "zh" else "I will do"
    verify_label = "验证方式" if language == "zh" else "Verifier"
    stop_label = "停止 / 返回点" if language == "zh" else "Stop / return point"
    ask_label = "完成前需要明确批准" if language == "zh" else "Explicit approval before"
    if language == "zh":
        return f"""# {design["name"]} 交接说明

{intro}

## {map_label}

{render_change_map(design["change_map"], language)}

## {contract_label}

- {mode_label}: {mode_display}
- {team_label}: {team_display}

{goal_label}:

{design["goal"]}

{will_do_label}:

{first_cycle_card(design)}

{verify_label}:

{bullet(start_card_items(contract["verifier_commands"], language))}

{stop_label}:

{bullet(start_card_items(contract["reject_conditions"], language))}

{ask_label}:

{bullet(start_card_items(design["safety"]["requires_approval_for"], language))}

## 为什么是这个 loop

- 为什么值得跑：{start_card_text(design["why_this_loop"], language)}
- 为什么不只是更小机制：{start_card_text(design["why_not_smaller"], language)}
- 为什么不更自动化：{start_card_text(design["why_not_more_autonomous"], language)}
- 适配判断：{start_card_text(design["fit_summary"], language)}

## 从这里开始

1. 读 `GOAL.md`。
2. 读 `RUN.md` 和 `VERIFY.md`。
3. 如果可用团队工具且协作方式是 `subagent-team`，用 `TEAM.md` 分配规划者、执行者、检查者、验收者和整合者角色。
4. 保持 `STATE.json` 在执行包旁边，停止前更新。

## 退出协议

仅在以下条件成立时继续：

{bullet(start_card_items(exits["continue_only_if"], language))}

返回 `DONE` 的条件：

{bullet(start_card_items(exits["done_when"], language))}

交还给用户的条件：

{bullet(start_card_items(exits["needs_human_when"], language))}

返回 `BLOCKED` 的条件：

{bullet(start_card_items(exits["blocked_when"], language))}

返回 `BUDGET_STOPPED` 的条件：

{bullet(start_card_items(exits["budget_stopped_when"], language))}

## 推进节奏

{render_progression_contract(progression_contract, language)}

## 自主决策

{render_autonomy_contract(autonomy_contract, language)}

## 复盘记录

每轮结束后，在 `STATE.json` 记录基线摩擦、运行结果、节省的人工纠正、误报、人工接受度、下一步调整和是否建议改成更小机制。

## 文件

- `{artifact_dir / "GOAL.md"}`
- `{artifact_dir / "STATE.json"}`
- `{artifact_dir / "RUN.md"}`
- `{artifact_dir / "VERIFY.md"}`
- `{artifact_dir / "TEAM.md"}`
- `{artifact_dir / "goal-loop-design.json"}`
- `{artifact_dir / "AGENTS-snippet.md"}`
"""
    return f"""# {design["name"]} Handoff

{intro}

## {map_label}

{render_change_map(design["change_map"], language)}

## {contract_label}

- {mode_label}: {mode_display}
- {team_label}: {team_display}

{goal_label}:

{design["goal"]}

{will_do_label}:

{first_cycle_card(design)}

{verify_label}:

{bullet(start_card_items(contract["verifier_commands"], language))}

{stop_label}:

{bullet(start_card_items(contract["reject_conditions"], language))}

{ask_label}:

{bullet(start_card_items(design["safety"]["requires_approval_for"], language))}

## Why This Loop

- Why this loop: {design["why_this_loop"]}
- Why not smaller: {design["why_not_smaller"]}
- Why not more autonomous: {design["why_not_more_autonomous"]}
- Fit summary: {design["fit_summary"]}

## Start Here

1. Read `GOAL.md`.
2. Read `RUN.md` and `VERIFY.md`.
3. If team tools are available and team mode is `subagent-team`, use `TEAM.md` to split planner, maker, checker, verifier, and integrator roles.
4. Keep `STATE.json` beside the run and update it before stopping.

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

## Progression Contract

{render_progression_contract(progression_contract, language)}

## Autonomy Contract

{render_autonomy_contract(autonomy_contract, language)}

## Learning Check

After each run, record baseline friction, post-run result, saved corrections, false positives,
human acceptance, next adjustment, and demotion recommendation in `STATE.json`.

## Files

- `{artifact_dir / "GOAL.md"}`
- `{artifact_dir / "STATE.json"}`
- `{artifact_dir / "RUN.md"}`
- `{artifact_dir / "VERIFY.md"}`
- `{artifact_dir / "TEAM.md"}`
- `{artifact_dir / "goal-loop-design.json"}`
- `{artifact_dir / "AGENTS-snippet.md"}`
"""


def render_run(design: dict) -> str:
    managed_loop = design["managed_loop"]
    exit_contract = managed_loop["loop_exit_contract"]
    progression_contract = managed_loop["progression_contract"]
    autonomy_contract = managed_loop["autonomy_contract"]
    change_map = design["change_map"]
    language = design_language(design)
    if language == "zh":
        title = "运行协议"
        read_first = "先读"
        map_label = "先更新改造图景"
        cycle = "循环步骤"
        exit_rule = "退出规则"
        continue_only_if = "继续下一轮的条件"
        stop_conditions = "停止条件"
        state_update = "停止前更新状态"
        progression = "推进节奏"
        autonomy = "自主决策"
        status_intro = "停止前只能返回一个状态："
        state_intro = "返回前，更新 `STATE.json`："
        status_lines = [
            "`CONTINUE`：只有下一轮能产生新的验收证据时才继续。",
            "`DONE`：只有成功标准通过并留下证据时才完成。",
            "`NEEDS_HUMAN`：决策包已包含选项、影响、回归路径和推荐后，或需要明确批准时返回。",
            "`BLOCKED`：同一失败重复两次、证据不再变化或验收器不可用时阻塞。",
            "`BUDGET_STOPPED`：事项、轮次、时间、token 或成本上限到达时停止。",
        ]
        read_steps = [
            "读 `GOAL.md`。",
            "读 `STATE.json`。",
            "读并更新 Change Map：当前 X、目标 B、波及面、回归 / 兼容路径、推进波次。",
            "读 `VERIFY.md`。",
            f"本轮最多选择 `{managed_loop['max_items_per_cycle']}` 个事项。",
        ]
        state_lines = ["改造图景变化", "选中的波次 / 事项", "采取的动作", "验收证据", "证据变化", "已选择的下一步位置", "候选下一步（不能替代 next_cursor）", "下一轮预期证据", "下一轮验收器", "阻塞型人工决策队列", "决策包（如有）", "失败签名（如有）", "最终状态", "下次位置或待用户确认事项"]
    else:
        title = "Run Protocol"
        read_first = "Read First"
        map_label = "Refresh The Change Map First"
        cycle = "Cycle"
        exit_rule = "Exit Rule"
        continue_only_if = "Continue Only If"
        stop_conditions = "Stop Conditions"
        state_update = "State Update"
        progression = "Progression Contract"
        autonomy = "Autonomy Contract"
        status_intro = "Return exactly one status before stopping:"
        state_intro = "Before returning, update `STATE.json` with:"
        status_lines = [
            "`CONTINUE`: only when the next cycle can produce new verifier evidence.",
            "`DONE`: only when success criteria pass with required evidence.",
            "`NEEDS_HUMAN`: after a decision packet is ready, or explicit approval / stronger authority is required.",
            "`BLOCKED`: when the same failure repeats twice, evidence stops changing, or the verifier is unavailable.",
            "`BUDGET_STOPPED`: when an item, iteration, time, token, or cost cap is reached.",
        ]
        read_steps = [
            "Read `GOAL.md`.",
            "Read `STATE.json`.",
            "Read and update the Change Map: current X, target B, affected surfaces, regression / compatibility path, and rollout waves.",
            "Read `VERIFY.md`.",
            f"Choose at most `{managed_loop['max_items_per_cycle']}` item(s) for this cycle.",
        ]
        state_lines = [
            "Change Map delta",
            "selected wave / items",
            "action taken",
            "verifier evidence",
            "evidence_delta",
            "next_cursor",
            "candidate_next_items",
            "next_expected_evidence",
            "next_verifier",
            "blocking_human_queue",
            "decision packet when any",
            "failure signature when any",
            "final status",
            "next_cursor or human_queue",
        ]
    return f"""# {title}: {design["name"]}

## {read_first}

{numbered(read_steps)}

## {map_label}

{render_change_map(change_map, language)}

## {cycle}

{numbered(start_card_items(managed_loop["cycle_steps"], language))}

## {progression}

{render_progression_contract(progression_contract, language)}

## {autonomy}

{render_autonomy_contract(autonomy_contract, language)}

## {exit_rule}

{status_intro}

{bullet(status_lines)}

## {continue_only_if}

{bullet(start_card_items(exit_contract["continue_only_if"], language))}

## {stop_conditions}

{bullet(start_card_items(managed_loop["completion_contract"]["reject_conditions"], language))}

## {state_update}

{state_intro}

{bullet(state_lines)}
"""


def render_verify(design: dict) -> str:
    managed_loop = design["managed_loop"]
    contract = managed_loop["completion_contract"]
    progression_contract = managed_loop["progression_contract"]
    change_map = design["change_map"]
    language = design_language(design)
    if language == "zh":
        title = "验收协议"
        map_label = "图景验收"
        success = "成功标准"
        verifier = "验收方式"
        pass_evidence = "必须留下的通过证据"
        regression = "回归 / 兼容检查"
        failure = "失败分类"
        progression = "推进验收"
        review = "返回点"
        map_lines = [
            "必须能说明当前 X 如何变成目标 B。",
            "必须列出真实波及面；不知道的波及面要进入 research_questions。",
            "每个执行波次必须有回归或兼容检查。",
            "需要人工判断时，先给出选项、影响、回归路径和推荐。",
        ]
        failure_lines = [
            "验收信号缺失或不可用",
            "同一失败重复两次",
            "连续两轮没有证据变化",
            "结果需要产品、设计、发布、安全、数据、成本或架构判断",
            "动作需要比当前模式更高的批准",
        ]
        review_text = "审查可以拒绝风险、范围或判断；审查不能替代验收证据，也不能单独宣布 `DONE`。"
    else:
        title = "Verification Protocol"
        map_label = "Change Map Verification"
        success = "Success Criteria"
        verifier = "Verifier"
        pass_evidence = "Required Pass Evidence"
        regression = "Regression / Compatibility Checks"
        failure = "Failure Classes"
        progression = "Progression Verification"
        review = "Review Boundary"
        map_lines = [
            "The packet explains how current X becomes target B.",
            "Affected surfaces are listed; unknown surfaces move into research_questions.",
            "Every execution wave has a regression or compatibility check.",
            "Human judgment comes with options, impact, regression path, and recommendation.",
        ]
        failure_lines = [
            "verifier missing or unavailable",
            "same failure repeated twice",
            "no evidence_delta across two cycles",
            "output needs product, design, release, security, data, cost, or architecture judgment",
            "action needs stronger approval than the current mode allows",
        ]
        review_text = "Review can reject risk, scope, or judgment. Review cannot replace verifier evidence or mark `DONE`."
    if language == "zh":
        progression_block = f"""验收器应拒绝没有具体推进字段的 `CONTINUE`：

{bullet(start_card_items(progression_contract["continue_requires"], language))}

验收器应拒绝含糊交接，例如：

{bullet(start_card_items(progression_contract["stop_instead_of_continue_when"], language))}"""
    else:
        progression_block = f"""The verifier should reject `CONTINUE` unless these progression fields are concrete:

{bullet(progression_contract["continue_requires"])}

The verifier should reject vague handoffs such as:

{bullet(progression_contract["stop_instead_of_continue_when"])}"""
    return f"""# {title}: {design["name"]}

## {map_label}

{bullet(map_lines)}

## {success}

{bullet(start_card_items(contract["success_criteria"], language))}

## {verifier}

{bullet(start_card_items(contract["verifier_commands"], language))}

## {pass_evidence}

{bullet(start_card_items(contract["pass_evidence_required"], language))}

## {regression}

{bullet(start_card_items(change_map["regression_plan"] + change_map["rollback_or_compatibility"], language))}

## {failure}

{bullet(failure_lines)}

## {progression}

{progression_block}

## {review}

{review_text}
"""


def render_agents_snippet(design: dict) -> str:
    managed_loop = design["managed_loop"]
    mode = level_to_mode(design["adoption_level"])
    language = design_language(design)
    if language == "zh":
        return f"""# AGENTS.md 草稿片段：{design["name"]}

这是待审查的 loop 指令草稿。复制进项目规则前先人工确认。

当目标匹配 `{design["loop_id"]}` 时：

- 以 `{mode}` 运行（内部级别 `{design["adoption_level"]}`），协作方式为 `{design["team_mode"]}`。
- 目标：{design["goal"]}
- 每轮先更新 Change Map：当前 X、目标 B、波及面、回归 / 兼容路径和推进波次。
- 每轮最多选择 {managed_loop["max_items_per_cycle"]} 个事项。
- 每轮结束前必须写入 `next_cursor`、`next_expected_evidence`、`next_verifier` 和 `human_friction_delta`。
- 存在多个可行下一步时，先由模型按用户价值、验收可用性、可回退性、风险和批准模式选择一个最高价值的非阻塞步骤。
- 普通工程优先级不要询问用户；只有产品、架构、发布、安全、数据、计费、权限、生产、不可逆或扩范围决策才交还。
- 只有下一轮能产生新的验收证据时才能返回 `CONTINUE`。
- 达到 {managed_loop["max_iterations_per_run"]} 轮、重复无进展或触达返回点时停止。
- 返回前必须读取并更新 Change Map 与 `STATE.json`。
- 需要先询问：{"、".join(start_card_items(design["safety"]["requires_approval_for"], language))}。
"""
    return f"""# Draft AGENTS.md Snippet: {design["name"]}

This is a draft loop instruction. Review before copying into project instructions.

When the goal matches `{design["loop_id"]}`:

- Run as `{mode}` (`{design["adoption_level"]}` internally) with `{design["team_mode"]}` team mode.
- Objective: {design["goal"]}
- Refresh the Change Map first each cycle: current X, target B, affected surfaces, regression / compatibility path, and rollout waves.
- Select at most {managed_loop["max_items_per_cycle"]} item(s) per cycle.
- Before ending each cycle, write `next_cursor`, `next_expected_evidence`, `next_verifier`, and `human_friction_delta`.
- When multiple next actions are plausible, the model must choose the highest-value non-blocking step using user value, verifier availability, reversibility, risk, and approved mode.
- Do not ask the user for ordinary engineering prioritization; return only for product, architecture, release, security, data, billing, permission, production, irreversible, or scope-expanding decisions.
- Return `CONTINUE` only when the next cycle can produce new verifier evidence.
- Stop after {managed_loop["max_iterations_per_run"]} iteration(s), repeated no-progress, or a return point.
- Read and update the Change Map and `STATE.json` before returning.
- Ask before: {", ".join(design["safety"]["requires_approval_for"])}.
"""


def host_packet_spec(design: dict, artifact_dir: Path) -> dict:
    managed_loop = design["managed_loop"]
    contract = managed_loop["completion_contract"]
    progression = managed_loop["progression_contract"]
    language = design_language(design)
    is_zh = language == "zh"
    return {
        "source_kind": "goal-design",
        "language": language,
        "loop_id": design["loop_id"],
        "name": design["name"],
        "objective": design["goal"],
        "project_root": str(Path(design.get("project_root") or ".").resolve()),
        "mode": level_to_mode(design["adoption_level"]),
        "internal_level": design["adoption_level"],
        "team_mode": design["team_mode"],
        "state_file": str(artifact_dir / "STATE.json"),
        "max_items": managed_loop["max_items_per_cycle"],
        "max_iterations": managed_loop["max_iterations_per_run"],
        "change_map": render_change_map(design["change_map"], language),
        "first_cycle": first_cycle_card(design),
        "cycle_steps": start_card_items(managed_loop["cycle_steps"], language) if is_zh else managed_loop["cycle_steps"],
        "selection_policy": start_card_items(managed_loop["selection_policy"], language) if is_zh else managed_loop["selection_policy"],
        "verification": start_card_items(contract["verifier_commands"], language) if is_zh else contract["verifier_commands"],
        "pass_evidence": start_card_items(contract["pass_evidence_required"], language) if is_zh else contract["pass_evidence_required"],
        "approval_boundary": start_card_items(design["safety"]["requires_approval_for"], language) if is_zh else design["safety"]["requires_approval_for"],
        "rollback_policy": start_card_items(
            [
                managed_loop["change_policy"],
                "Use the generated packet as host input; SixLoops does not directly execute the loop.",
                "Keep patch or decision packet output reviewable before applying irreversible changes.",
            ],
            language,
        )
        if is_zh
        else [
            managed_loop["change_policy"],
            "Use the generated packet as host input; SixLoops does not directly execute the loop.",
            "Keep patch or decision packet output reviewable before applying irreversible changes.",
        ],
        "exit_contract": managed_loop["loop_exit_contract"],
        "progression_contract": progression,
        "autonomy_contract": managed_loop["autonomy_contract"],
        "state_updates_required": start_card_items(progression["state_updates_required"], language) if is_zh else progression["state_updates_required"],
    }


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
    host_files = {
        "host_start": artifact_dir / "HOST-START.md",
        "codex_goal": artifact_dir / "CODEX-GOAL.md",
        "claude_loop": artifact_dir / "CLAUDE-LOOP.md",
        "host_manifest": artifact_dir / "host-start-packet.json",
    }
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
            "run": str(artifact_dir / "RUN.md"),
            "verify": str(artifact_dir / "VERIFY.md"),
            "design": str(artifact_dir / "goal-loop-design.json"),
            "handoff": str(artifact_dir / "HANDOFF.md"),
            "agents_snippet": str(artifact_dir / "AGENTS-snippet.md"),
            "host_start": str(host_files["host_start"]),
            "codex_goal": str(host_files["codex_goal"]),
            "claude_loop": str(host_files["claude_loop"]),
            "host_manifest": str(host_files["host_manifest"]),
        },
    }
    spec = host_packet_spec(design, artifact_dir)
    host_manifest = build_host_manifest(spec, host_files)
    write_json(artifact_dir / "goal-loop-design.json", design, overwrite)
    write_json(artifact_dir / "STATE.json", build_state(design), overwrite)
    write_text(artifact_dir / "GOAL.md", render_goal(design), overwrite)
    write_text(artifact_dir / "RUN.md", render_run(design), overwrite)
    write_text(artifact_dir / "VERIFY.md", render_verify(design), overwrite)
    write_text(artifact_dir / "TEAM.md", render_team(design), overwrite)
    write_text(artifact_dir / "HANDOFF.md", render_handoff(design, artifact_dir), overwrite)
    write_text(artifact_dir / "AGENTS-snippet.md", render_agents_snippet(design), overwrite)
    write_text(host_files["codex_goal"], render_host_packet(spec, "codex"), overwrite)
    write_text(host_files["claude_loop"], render_host_packet(spec, "claude"), overwrite)
    write_json(host_files["host_manifest"], host_manifest, overwrite)
    write_text(host_files["host_start"], render_host_start(host_manifest, spec["language"]), overwrite)
    write_json(artifact_dir / "manifest.json", manifest, overwrite)
    return artifact_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design a goal-ready loop and optional subagent team from a user objective.")
    parser.add_argument("--goal", default=None, help="User objective to turn into a loop.")
    parser.add_argument("--goal-file", default=None, help="Path to a text file containing the user objective.")
    parser.add_argument("--name", default=None, help="Human-readable loop name.")
    parser.add_argument("--loop-id", default=None, help="Stable loop id. Defaults to a slug from domain and goal hash.")
    parser.add_argument("--domain", choices=sorted(DOMAINS), default="auto", help="Task domain. Use explicit/model-design values for real runs; auto is fallback scaffolding.")
    parser.add_argument("--level", choices=sorted(LEVELS), default="auto", help="Starting adoption level. Use explicit/model-design values for real runs; auto is fallback scaffolding.")
    parser.add_argument("--team-mode", choices=sorted(TEAM_MODES), default="auto", help="Team design mode. Use explicit/model-design values for real runs; auto is fallback scaffolding.")
    parser.add_argument("--model-design-file", default=None, help="Host-model-authored JSON with domain, level, team_mode, change_map, and rationale. Without it, auto fields are fallback scaffolding only.")
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
    print(f"- {artifact_dir / 'STATE.json'}")
    print(f"- {artifact_dir / 'RUN.md'}")
    print(f"- {artifact_dir / 'VERIFY.md'}")
    print(f"- {artifact_dir / 'TEAM.md'}")
    print(f"- {artifact_dir / 'goal-loop-design.json'}")
    print(f"- {artifact_dir / 'HOST-START.md'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"design_goal_loop.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
