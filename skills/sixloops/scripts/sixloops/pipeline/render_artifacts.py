#!/usr/bin/env python3
"""Render redacted candidate artifacts from scored pipeline output."""

from __future__ import annotations

import argparse
import math
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from sixloops.core.loop_contract import normalize_exit_contract
from sixloops.core.mode_policy import RUN_MODES, SCHEDULED_MODES, level_to_mode
from sixloops.paths import TEMPLATE_DIR


DEFAULT_CANDIDATES = Path(".sixloops/private/candidates.json")
DEFAULT_OUT_DIR = Path(".sixloops/public")
CJK_TEXT = re.compile(r"[\u3400-\u9fff]")
LATIN_WORD = re.compile(r"\b[A-Za-z][A-Za-z-]{2,}\b")
ENGLISH_SENTENCE_HINT = re.compile(
    r"\b(?:a|an|and|are|as|before|can|do|does|failed|failure|for|from|if|in|is|it|only|or|read|"
    r"required|return|run|scope|status|the|then|this|to|verify|when|with|without)\b",
    re.IGNORECASE,
)

UI = {
    "en": {
        "none": "None.",
        "yes": "yes",
        "no": "no",
        "limited": "limited",
        "not_recorded": "not recorded",
        "summary": "Recommended {count} startable loop plan(s). Choose a mode, shrink the idea, reject it, or rerun with narrower evidence.",
        "no_proposal": "No loop proposal is ready. The useful outcome is to keep the rejected findings as context and gather better session evidence.",
        "no_proposal_next": "Recommended next step: run a narrower transcript analysis or keep these as rejected context.",
        "overview_header": "| Priority | Candidate | Recommendation | Why worth a loop | Recommended next reply |\n| --- | --- | --- | --- | --- |",
        "overview_empty": "| - | No startable candidate | Rerun or reject | Current evidence does not justify a loop | `rerun with narrower evidence` |",
        "start_reply_note": "Reply in this chat with one of the lines below. Do not run it in a terminal or copy the whole card unless you want to hand it to another agent.",
        "choose_from": "Choose which proposal to start, shrink, or reject from {names}.",
        "chosen_mode_effect": "If the chosen mode allows edits, the agent runs the first controlled cycle in that mode; otherwise it generates the run packet and state convention.",
        "proposal_title": "### {index}. {name}",
        "recommended_start": "Recommended start",
        "decision_line": "Decision: `{decision}` | Mechanism: `{mechanisms}` | Confidence: `{confidence}`",
        "run_card_line": "Can start now: `{can_use_now}` | Can confirm: `{can_confirm}` | Can delegate: `{can_delegate}`",
        "next_action": "Next action",
        "start_with_one": "Start with one:",
        "what_it_does": "What it does",
        "work_shape_line": "Work shape: `{work_shape}` | Archetype: `{loop_archetype}`",
        "heartbeat_line": "Heartbeat: `{heartbeat}` | Mode: `{mode}` | Internal maturity: `{maturity}`",
        "first_cycle": "First cycle:",
        "observe": "Observe",
        "decide": "Decide",
        "act": "Act",
        "verify": "Verify",
        "state": "State",
        "stop_after": "Stop after",
        "trigger": "Trigger:",
        "loop_cycle": "Loop cycle:",
        "verification": "Verification:",
        "stop_conditions": "Stop conditions:",
        "iteration_cap": "Iteration cap: {count} run iteration(s)",
        "review_boundary": "Review boundary: {boundary}",
        "acceptance_checks": "Acceptance checks:",
        "loop_exits": "Loop exits:",
        "continue_only_if": "Continue only if:",
        "done_when": "Return `DONE` when:",
        "review_when": "Return for review when:",
        "blocked_when": "Return `BLOCKED` when:",
        "budget_when": "Return `BUDGET_STOPPED` when:",
        "why_mechanism": "Why this mechanism",
        "basis_auxiliary": "project auxiliary evidence",
        "basis_user": "repeated user-language evidence",
        "basis_tool": "tool-use evidence",
        "basis_available": "available local evidence",
        "basis_prefix": "Basis",
        "start_recommendation": "Start as `{mode}`",
        "shrink_recommendation": "Shrink to `{mechanism}`",
        "reject_recommendation": "Reject",
        "rerun_recommendation": "Rerun with narrower evidence",
        "not_startable": "not startable",
        "scope_heading": "## Analysis Scope",
        "approved": "Approved",
        "allowed_roles": "Allowed roles",
        "redacted_snippets": "Redacted snippets",
        "output_visibility": "Output visibility",
        "enabled": "enabled",
        "disabled": "disabled",
        "files": "Files",
        "records": "records",
        "providers": "providers",
        "source_types": "source types",
        "auxiliary_limitation": "This run used project auxiliary evidence, so proposals should stay draft until the user confirms fit.",
    },
    "zh": {
        "none": "无。",
        "yes": "是",
        "no": "否",
        "limited": "受限",
        "not_recorded": "未记录",
        "summary": "建议 {count} 个可启动的 Loop 方案。你可以选择启动、收缩成更小机制、拒绝，或缩小证据范围后重跑。",
        "no_proposal": "当前没有足够成熟的 Loop 方案。更有用的下一步是保留拒绝项作为上下文，或收集更窄、更强的会话证据。",
        "no_proposal_next": "建议下一步：缩小证据范围后重跑分析，或把这些结论保留为已拒绝上下文。",
        "overview_header": "| 优先级 | 候选项 | 建议 | 为什么值得做成 Loop | 推荐下一步 |\n| --- | --- | --- | --- | --- |",
        "overview_empty": "| - | 无可启动候选 | 重跑或拒绝 | 当前证据不足以支撑 Loop | `rerun with narrower evidence` |",
        "start_reply_note": "只需要在当前对话回复下面某一行。不要在终端执行，也不用复制整张卡片；只有要转交给另一个 agent 时才复制卡片。",
        "choose_from": "请从 {names} 中选择要启动、收缩或拒绝的方案。",
        "chosen_mode_effect": "如果选择的模式允许编辑，agent 会按该模式执行第一轮受控循环；否则只生成运行包和状态约定。",
        "proposal_title": "### {index}. {name}",
        "recommended_start": "推荐启动方式",
        "decision_line": "判断：`{decision}` | 机制：`{mechanisms}` | 置信度：`{confidence}`",
        "run_card_line": "现在可启动：`{can_use_now}` | 可确认：`{can_confirm}` | 可托管：`{can_delegate}`",
        "next_action": "下一步",
        "start_with_one": "回复其中一行：",
        "what_it_does": "它会做什么",
        "work_shape_line": "工作形态：`{work_shape}` | Loop 类型：`{loop_archetype}`",
        "heartbeat_line": "触发节奏：`{heartbeat}` | 模式：`{mode}` | 内部成熟度：`{maturity}`",
        "first_cycle": "第一轮循环：",
        "observe": "观察",
        "decide": "决策",
        "act": "执行",
        "verify": "验证",
        "state": "状态文件",
        "stop_after": "停止条件",
        "trigger": "触发时机：",
        "loop_cycle": "循环步骤：",
        "verification": "验证方式：",
        "stop_conditions": "停止条件：",
        "iteration_cap": "迭代上限：{count} 轮",
        "review_boundary": "审查边界：{boundary}",
        "acceptance_checks": "验收标准：",
        "loop_exits": "退出协议：",
        "continue_only_if": "仅在以下条件成立时继续：",
        "done_when": "返回 `DONE` 的条件：",
        "review_when": "需要返回人工审查的条件：",
        "blocked_when": "返回 `BLOCKED` 的条件：",
        "budget_when": "返回 `BUDGET_STOPPED` 的条件：",
        "why_mechanism": "为什么是这个机制",
        "basis_auxiliary": "项目辅助证据",
        "basis_user": "重复出现的用户语言证据",
        "basis_tool": "工具使用证据",
        "basis_available": "可用本地证据",
        "basis_prefix": "依据",
        "start_recommendation": "以 `{mode}` 模式启动",
        "shrink_recommendation": "先收缩成 `{mechanism}`",
        "reject_recommendation": "拒绝",
        "rerun_recommendation": "缩小证据范围后重跑",
        "not_startable": "不可启动",
        "scope_heading": "## 分析范围",
        "approved": "已批准",
        "allowed_roles": "允许角色",
        "redacted_snippets": "脱敏片段",
        "output_visibility": "输出可见性",
        "enabled": "已启用",
        "disabled": "已禁用",
        "files": "文件数",
        "records": "记录数",
        "providers": "来源",
        "source_types": "来源类型",
        "auxiliary_limitation": "本次使用的是项目辅助证据，用户确认适配前应保持草稿状态。",
    },
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")


def ui(language: str, key: str) -> str:
    return UI.get(language, UI["en"]).get(key, UI["en"][key])


def load_template(name: str, language: str = "en") -> str:
    if language != "en":
        localized = TEMPLATE_DIR / name.replace(".md", f".{language}.md")
        if localized.exists():
            return localized.read_text(encoding="utf-8")
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def fill(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def bullet(items: list[str], language: str = "en") -> str:
    if not items:
        return ui(language, "none")
    return "\n- ".join(items)


def bullet_block(items: list[str], language: str = "en") -> str:
    if not items:
        return ui(language, "none")
    return "- " + "\n- ".join(items)


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def mapping_block(value: dict, language: str = "en") -> str:
    if not value:
        return ui(language, "none")
    return "\n".join(
        f"- {key}: {localized_text(item, language, '该字段或状态的含义已记录。', str(item))}"
        for key, item in value.items()
    )


def first(items: list[str], default: str = "None.") -> str:
    return items[0] if items else default


def contains_cjk(value: object) -> bool:
    if isinstance(value, dict):
        return any(contains_cjk(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_cjk(item) for item in value)
    return bool(CJK_TEXT.search(str(value)))


def language_signal(values: list[object]) -> tuple[int, int]:
    text = "\n".join(str(value) for value in values if value)
    return len(CJK_TEXT.findall(text)), sum(len(match.group(0)) for match in LATIN_WORD.finditer(text))


def dominant_text_language(values: list[object]) -> str:
    cjk_chars, latin_chars = language_signal(values)
    if cjk_chars >= 2 and cjk_chars >= latin_chars * 0.2:
        return "zh"
    return "en"


def detect_output_language(data: dict, requested: str = "auto") -> str:
    normalized = requested.lower()
    if normalized in {"zh", "zh-cn", "chinese"}:
        return "zh"
    if normalized in {"en", "english"}:
        return "en"

    user_evidence: list[object] = []
    fallback_evidence: list[object] = []
    for candidate in data.get("candidates", []):
        for key in (
            "user_semantics",
            "why_this_loop",
            "why_not_smaller",
            "where_this_may_be_wrong",
        ):
            fallback_evidence.append(candidate.get(key))
        for item in candidate.get("evidence", []):
            if isinstance(item, dict) and item.get("role") == "user":
                user_evidence.append(item.get("snippet"))
    return dominant_text_language(user_evidence or fallback_evidence)


def needs_localization(value: object, language: str) -> bool:
    if language != "zh":
        return False
    text = str(value or "").strip()
    if not text or contains_cjk(text):
        return False
    latin_words = LATIN_WORD.findall(text)
    return len(latin_words) >= 3 or (len(latin_words) >= 2 and " " in text) or bool(ENGLISH_SENTENCE_HINT.search(text))


def localized_text(value: object, language: str, zh_fallback: str, en_fallback: str = "None.") -> str:
    text = str(value or "").strip()
    if not text:
        return zh_fallback if language == "zh" else en_fallback
    if needs_localization(text, language):
        return zh_fallback
    return text


def localized_items(items: object, language: str, zh_fallback: list[str], en_fallback: list[str] | None = None) -> list[str]:
    values = as_list(items)
    if language != "zh":
        return values or (en_fallback or [])
    localized = [str(item) for item in values if str(item).strip() and not needs_localization(item, language)]
    return localized or zh_fallback


def candidate_display_name(candidate: dict, language: str) -> str:
    name = str(candidate.get("name") or candidate.get("id") or "").strip()
    if language == "zh" and needs_localization(name, language):
        return f"候选 `{candidate.get('id', 'unknown')}`"
    return name or str(candidate.get("id", "unknown"))


def candidate_objective(candidate: dict, managed_loop: dict, language: str) -> str:
    raw = managed_loop.get("objective") or candidate.get("summary")
    zh_fallback = f"围绕 `{candidate.get('id', 'candidate')}` 执行一轮有状态、有验证、有停止条件的受控循环。"
    return localized_text(raw, language, zh_fallback, "No objective recorded.")


def candidate_reason(candidate: dict, managed_loop: dict, language: str) -> str:
    raw = candidate.get("why_this_loop") or managed_loop.get("objective") or candidate.get("summary")
    zh_fallback = "它具备可观察状态、可重复动作、验证方式和停止条件，因此值得作为候选 Loop 评估。"
    return localized_text(raw, language, zh_fallback, "No reason recorded.")


def cycle_steps(candidate: dict, managed_loop: dict, language: str) -> list[str]:
    return localized_items(
        managed_loop.get("cycle_steps", candidate.get("actions", [])),
        language,
        [
            "读取已有状态和当前输入。",
            "选择少量有直接证据支撑的事项。",
            "在当前模式边界内执行下一步。",
            "运行聚焦验证并记录结果。",
        ],
    )


def trigger_items(candidate: dict, managed_loop: dict, language: str) -> list[str]:
    return localized_items(
        managed_loop.get("cadence_or_trigger", candidate.get("trigger", [])),
        language,
        ["当该候选事项再次出现，且有可观察输入和可验证结果时运行。"],
    )


def verification_items(candidate: dict, contract: dict, language: str) -> list[str]:
    return localized_items(
        contract.get("verifier_commands", candidate.get("verification", [])),
        language,
        ["运行与该候选事项直接相关的聚焦验证，并保留通过或阻塞证据。"],
    )


def stop_items(candidate: dict, contract: dict, language: str) -> list[str]:
    return localized_items(
        contract.get("reject_conditions", candidate.get("stop_conditions", [])),
        language,
        ["验证失败重复出现、缺少可行动证据、触达审查边界，或达到迭代上限。"],
    )


def table_cell(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    return text.replace("|", r"\|")


def display_flag(value: object, language: str) -> str:
    text = str(value)
    if language != "zh":
        return text
    return {"yes": ui(language, "yes"), "no": ui(language, "no"), "limited": ui(language, "limited")}.get(text, text)


def snippets_visible(scope: dict) -> bool:
    return bool(scope.get("allow_redacted_snippets")) and scope.get("output_visibility") == "public"


def evidence_text(first_evidence: dict, scope: dict, language: str = "en") -> str:
    if snippets_visible(scope):
        return first_evidence.get("snippet", "不需要引用。" if language == "zh" else "No quote needed.")
    return "[证据片段已隐藏；完整脱敏证据见私有 candidates.json]" if language == "zh" else "[snippet hidden; see private candidates.json]"


def loop_exit_contract(candidate: dict, managed_loop: dict, contract: dict) -> dict:
    safety = candidate.get("safety") if isinstance(candidate.get("safety"), dict) else {}
    return normalize_exit_contract(
        managed_loop.get("loop_exit_contract"),
        success_criteria=contract.get("success_criteria") or candidate.get("verification"),
        reject_conditions=contract.get("reject_conditions") or candidate.get("stop_conditions"),
        approval_boundary=safety.get("requires_approval_for") or safety.get("human_checkpoint"),
        max_items=managed_loop.get("max_items_per_cycle", 3),
        max_iterations=managed_loop.get("max_iterations_per_run", 8),
    )


def exit_contract_values(exits: dict, language: str = "en") -> dict[str, str]:
    protocol = exits.get("status_protocol", {})
    return {
        "exit_continue_only_if": bullet_block(
            localized_items(exits.get("continue_only_if", []), language, ["目标未变，下一步仍在已批准范围内，且验证器能拒绝错误输出。"]),
            language,
        ),
        "exit_done_when": bullet_block(localized_items(exits.get("done_when", []), language, ["验收标准通过，并保留必要证据。"]), language),
        "exit_needs_human_when": bullet_block(
            localized_items(exits.get("needs_human_when", []), language, ["需要人工判断、显式批准或更强执行模式。"]),
            language,
        ),
        "exit_blocked_when": bullet_block(
            localized_items(exits.get("blocked_when", []), language, ["当前证据或验证器不足以继续可靠推进。"]),
            language,
        ),
        "exit_budget_stopped_when": bullet_block(
            localized_items(exits.get("budget_stopped_when", []), language, ["达到事项数、迭代数、时间、token 或成本上限。"]),
            language,
        ),
        "exit_status_protocol": mapping_block(protocol if isinstance(protocol, dict) else {}, language),
    }


def bool_label(value: bool, language: str = "en") -> str:
    return ui(language, "yes") if value else ui(language, "no")


def next_rung(current: str) -> str:
    ladder = [
        "read-only",
        "goal-loop",
        "isolated-draft",
        "verified-pr-draft",
        "scheduled-readonly",
        "scheduled-draft",
    ]
    if current not in ladder:
        return "goal-loop"
    index = ladder.index(current)
    return ladder[min(index + 1, len(ladder) - 1)]


def smaller_mechanism(candidate: dict) -> str:
    mechanisms = candidate.get("mechanisms", [])
    return "skill" if "skill" in mechanisms else "checklist"


def candidate_maturity(candidate: dict, managed_loop: dict | None = None) -> str:
    managed_loop = managed_loop if isinstance(managed_loop, dict) else candidate.get("managed_loop", {})
    if not isinstance(managed_loop, dict):
        managed_loop = {}
    return managed_loop.get("recommended_maturity", candidate.get("safety", {}).get("autonomy_level", "draft-only"))


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def start_modes_for_candidate(candidate: dict, card: dict | None = None, managed_loop: dict | None = None) -> list[str]:
    if candidate.get("decision") == "reject":
        return []

    modes = ["read-only"]
    mechanisms = set(candidate.get("mechanisms", []))
    decision = str(candidate.get("decision", ""))
    card = card or {}
    can_delegate = str(card.get("can_delegate", "yes" if "loop" in mechanisms else "no")).lower() == "yes"
    if decision in {"needs-human", "rule-only", "checklist-only"} or "loop" not in mechanisms or not can_delegate:
        return modes

    maturity = candidate_maturity(candidate, managed_loop)
    if maturity == "read-only":
        return modes
    if maturity == "scheduled-readonly":
        return unique([*modes, SCHEDULED_MODES[0]])
    if maturity == "scheduled-draft":
        return unique([*modes, *SCHEDULED_MODES])
    return unique([*modes, *RUN_MODES[1:]])


def start_options(candidate: dict, card: dict | None = None, managed_loop: dict | None = None) -> list[str]:
    candidate_id = candidate["id"]
    options = [f"start {candidate_id} as {mode}" for mode in start_modes_for_candidate(candidate, card, managed_loop)]
    if candidate.get("decision") != "reject":
        options.append(f"shrink {candidate_id} to {smaller_mechanism(candidate)}")
    options.append(f"reject {candidate_id}")
    return options


def display_mode_for_candidate(candidate: dict, card: dict | None = None, managed_loop: dict | None = None, language: str = "en") -> str:
    if candidate.get("decision") == "reject":
        return ui(language, "not_startable")
    modes = start_modes_for_candidate(candidate, card, managed_loop)
    maturity_mode = level_to_mode(candidate_maturity(candidate, managed_loop))
    return maturity_mode if maturity_mode in modes else first(modes, "read-only")


def next_mode_for_candidate(candidate: dict, card: dict, maturity: str) -> str:
    if candidate.get("decision") == "reject":
        return "not startable"
    if str(card.get("can_delegate", "no")).lower() != "yes":
        return "not available until delegation gaps are fixed"
    return level_to_mode(next_rung(maturity))


def confirmation_options(candidate: dict) -> list[str]:
    card = candidate.get("decision_card") or {}
    return start_options(candidate, card)


def first_run_defaults(
    candidate: dict,
    managed_loop: dict,
    contract: dict,
    card: dict | None = None,
    language: str = "en",
) -> dict[str, str]:
    packet = candidate.get("first_run_packet") or {}
    max_iterations = managed_loop.get("max_iterations_per_run", 8)
    verifier = first(
        contract.get("verifier_commands", []),
        first(candidate.get("verification", []), "运行聚焦验证命令。" if language == "zh" else "Run the focused verifier."),
    )
    state_file = managed_loop.get("state_file", f".sixloops/state/{candidate['id']}.json")
    approvals = candidate.get("safety", {}).get("requires_approval_for", [])
    human_gate = packet.get("human_gate") or (
        f"执行 {', '.join(approvals)} 前先询问。" if language == "zh" and approvals
        else f"Ask before {', '.join(approvals)}." if approvals
        else "扩大范围、改变风险边界或执行不可逆操作前先询问。" if language == "zh"
        else "Ask before expanding scope, changing risk boundaries, or making irreversible changes."
    )
    success_criteria = packet.get("success_criteria")
    if isinstance(success_criteria, list):
        success_text = bullet_block(
            localized_items(success_criteria, language, ["聚焦验证通过，或明确记录阻塞原因。"]),
            language,
        )
    elif success_criteria:
        success_text = localized_text(success_criteria, language, "聚焦验证通过，或明确记录阻塞原因。")
    else:
        success_text = bullet_block(
            localized_items(
                contract.get("success_criteria", candidate.get("verification", [])),
                language,
                ["聚焦验证通过，或明确记录阻塞原因。"],
            ),
            language,
        )
    maturity = managed_loop.get("recommended_maturity", "goal-loop")
    options = start_options(candidate, card, managed_loop)
    start_choices = [option for option in options if option.startswith("start ")]
    default_action = f"start {candidate['id']} as {level_to_mode(maturity)}"
    if default_action not in start_choices:
        default_action = first(start_choices, f"reject {candidate['id']}" if candidate.get("decision") == "reject" else f"shrink {candidate['id']} to {smaller_mechanism(candidate)}")
    recommended_action = str(packet.get("recommended_action", default_action))
    if recommended_action not in options:
        recommended_action = default_action
    return {
        "recommended_action": recommended_action,
        "first_run_goal": localized_text(
            packet.get("goal"),
            language,
            candidate_objective(candidate, managed_loop, language),
            managed_loop.get("objective", candidate.get("summary", "Run the loop.")),
        ),
        "first_run_success_criteria": success_text,
        "first_run_observe": str(packet.get(
            "observe",
            "读取状态文件、当前输入和最新验证证据" if language == "zh" else "read the state file, current inputs, and latest verifier evidence",
        )),
        "first_run_decide": str(packet.get(
            "decide",
            f"最多选择 {managed_loop.get('max_items_per_cycle', 3)} 个事项、下一步动作和审查边界"
            if language == "zh"
            else f"choose at most {managed_loop.get('max_items_per_cycle', 3)} item(s), the next action, and any review boundary",
        )),
        "first_run_act": str(packet.get(
            "act",
            f"只处理最多 {managed_loop.get('max_items_per_cycle', 3)} 个有直接证据支撑的事项"
            if language == "zh"
            else f"pick at most {managed_loop.get('max_items_per_cycle', 3)} directly evidenced item(s)",
        )),
        "first_run_verify": localized_text(packet.get("verify", verifier), language, first(verification_items(candidate, contract, language))),
        "first_run_stop_after": str(packet.get(
            "stop_after",
            f"{max_iterations} 轮迭代、重复失败、连续两轮无进展，或触达审查边界"
            if language == "zh"
            else f"{max_iterations} iterations, repeated failure, no progress across two iterations, or a review boundary",
        )),
        "first_run_human_gate": str(human_gate),
    }


def mechanism_decision(candidate: dict, managed_loop: dict, language: str = "en") -> dict[str, str]:
    decision = candidate.get("mechanism_decision") or {}
    mechanisms = candidate.get("mechanisms", [])
    if "loop" in mechanisms:
        why = (
            "它需要反复执行观察、决策、执行、验证，并保留状态、停止条件和恢复策略。"
            if language == "zh"
            else "This needs repeated observe-decide-act-verify behavior with state, verification, stop conditions, and resume behavior."
        )
        smaller = (
            "单纯规则、技能或清单无法保留状态，也无法推动重复验证。"
            if language == "zh"
            else "A rule, skill, or checklist alone would not preserve state or drive repeated verification."
        )
    else:
        why = "这个方向有用，但当前证据还不足以支撑托管 Loop。" if language == "zh" else "This is useful, but the evidence does not justify a managed loop yet."
        smaller = "建议先使用更小的机制。" if language == "zh" else "A smaller mechanism is recommended first."
    maturity = managed_loop.get("recommended_maturity", candidate.get("safety", {}).get("autonomy_level", "draft-only"))
    return {
        "why_this_mechanism": localized_text(
            candidate.get("why_this_loop") or decision.get("why_this_mechanism"),
            language,
            why,
            why,
        ),
        "why_not_smaller": localized_text(
            candidate.get("why_not_smaller") or decision.get("why_not_smaller"),
            language,
            smaller,
            smaller,
        ),
        "why_not_more_autonomous": localized_text(
            decision.get("why_not_more_autonomous") or candidate.get("why_not_more_autonomous"),
            language,
            f"先从 `{maturity}` 开始，等验证证据和已接受产出足够稳定后再升级。",
            f"Start at `{maturity}` until verifier evidence and accepted outputs justify promotion.",
        ),
    }


def render_trace(candidate: dict, language: str = "en") -> str:
    trace = candidate.get("decision_trace", {})
    loop_gate = candidate.get("loop_eligibility", {})
    criteria = loop_gate.get("criteria", {})
    missing = loop_gate.get("missing", [])
    role_counts = trace.get("role_counts", {})
    if language == "zh":
        lines = [
            "## 判断轨迹",
            "",
            f"分析依据：{trace.get('analysis_basis', ui(language, 'not_recorded'))}",
            "",
            f"主要证据角色：`{trace.get('primary_role', 'unknown')}`",
            "",
            "角色计数：",
            "",
        ]
    else:
        lines = [
            "## Decision Trace",
            "",
            f"Analysis basis: {trace.get('analysis_basis', 'Not recorded.')}",
            "",
            f"Primary evidence role: `{trace.get('primary_role', 'unknown')}`",
            "",
            "Role counts:",
            "",
        ]
    lines.extend([
        f"- user: {role_counts.get('user', 0)}",
        f"- tool: {role_counts.get('tool', 0)}",
        f"- assistant: {role_counts.get('assistant', 0)}",
        f"- unknown: {role_counts.get('unknown', 0)}",
        "",
        f"{'意图' if language == 'zh' else 'Intents'}: {', '.join(trace.get('intents', [])) or ui(language, 'none')}",
        "",
        "Loop 资格：" if language == "zh" else "Loop eligibility:",
        "",
        f"- eligible: {bool_label(loop_gate.get('eligible', False), language)}",
    ])
    for key, value in criteria.items():
        lines.append(f"- {key}: {bool_label(bool(value), language)}")
    missing_label = "缺失的 Loop 条件" if language == "zh" else "Missing loop criteria"
    lines.extend(["", f"{missing_label}: {', '.join(missing) if missing else ui(language, 'none')}"])
    downgrades = trace.get("downgrades", [])
    downgrade_label = "强制降级" if language == "zh" else "Hard downgrades"
    lines.extend(["", f"{downgrade_label}: {' '.join(downgrades) if downgrades else ui(language, 'none')}", ""])
    return "\n".join(lines)


def approval_boundary(candidate: dict, language: str = "en") -> str:
    approvals = candidate.get("safety", {}).get("requires_approval_for", [])
    if approvals:
        return "; ".join(approvals)
    return "除常规仓库审查外，没有记录额外审查边界。" if language == "zh" else "No extra review boundary recorded beyond normal repo review."


def control_will_not(candidate: dict, managed_loop: dict, language: str = "en") -> list[str]:
    items = []
    approvals = candidate.get("safety", {}).get("requires_approval_for", [])
    if approvals:
        items.append(
            f"在没有匹配模式的情况下落地或完成审查边界动作：{', '.join(str(item) for item in approvals)}。"
            if language == "zh"
            else f"Land or finalize review-boundary actions without the matching mode: {', '.join(str(item) for item in approvals)}."
        )
    change_policy = managed_loop.get("change_policy")
    if change_policy:
        items.append(
            localized_text(
                change_policy,
                language,
                "遵守当前模式的变更边界，不执行未获批准的高影响动作。",
                str(change_policy),
            )
        )
    return items or [
        "扩大范围、完成不可逆变更，或在没有验证证据时行动。"
        if language == "zh"
        else "Expand scope, finalize irreversible changes, or act without verifier evidence."
    ]


def where_wrong(candidate: dict, language: str = "en") -> list[str]:
    raw = candidate.get("where_this_may_be_wrong")
    items = as_list(raw)
    if items:
        return items
    trace = candidate.get("decision_trace", {})
    source_type_counts = trace.get("source_type_counts", {})
    if source_type_counts:
        return [
            f"来源组合可能限制置信度：{source_type_counts}。"
            if language == "zh"
            else f"Source mix may limit confidence: {source_type_counts}."
        ]
    return [
        "分析包可能遗漏当前项目状态或较新的失败。"
        if language == "zh"
        else "The packet set may omit current project state or newer failures."
    ]


def decision_card(candidate: dict) -> dict:
    card = candidate.get("decision_card") or {}
    next_action = card.get("next_action", "start" if candidate.get("decision") != "reject" else "reject")
    if next_action == "adopt":
        next_action = "start"
    resolved = {
        "can_use_now": card.get("can_use_now", "limited" if candidate.get("decision") != "reject" else "no"),
        "can_confirm": card.get("can_confirm", "yes" if candidate.get("verification") else "no"),
        "can_delegate": card.get("can_delegate", "yes" if "loop" in candidate.get("mechanisms", []) else "no"),
        "missing_before_delegate": card.get("missing_before_delegate", []),
        "next_action": next_action,
    }
    resolved["confirmation_options"] = start_options(candidate, resolved)
    return resolved


def proposal_candidates(candidates: list[dict]) -> list[dict]:
    loops = [item for item in candidates if item.get("decision") != "reject" and "loop" in item.get("mechanisms", [])]
    if loops:
        return loops[:3]
    return [item for item in candidates if item.get("decision") != "reject"][:3]


def why_this_loop(candidate: dict, language: str = "en") -> str:
    trace = candidate.get("decision_trace", {})
    role_counts = trace.get("role_counts", {})
    providers = trace.get("provider_counts", {})
    if providers.get("auxiliary"):
        basis = ui(language, "basis_auxiliary")
    elif role_counts.get("user", 0):
        basis = ui(language, "basis_user")
    elif role_counts.get("tool", 0):
        basis = ui(language, "basis_tool")
    else:
        basis = ui(language, "basis_available")
    fallback = "未记录摘要。" if language == "zh" else "No summary recorded."
    summary = localized_text(candidate.get("summary"), language, "该候选具备可重复处理的 Loop 信号。", fallback)
    return f"{summary} {ui(language, 'basis_prefix')}: {basis}."


def recommendation_for(candidate: dict, action: str, language: str) -> str:
    if action.startswith("start "):
        mode = action.split(" as ", 1)[1] if " as " in action else "read-only"
        return ui(language, "start_recommendation").format(mode=mode)
    if action.startswith("shrink "):
        mechanism = action.rsplit(" to ", 1)[1] if " to " in action else smaller_mechanism(candidate)
        return ui(language, "shrink_recommendation").format(mechanism=mechanism)
    if action.startswith("reject "):
        return ui(language, "reject_recommendation")
    return ui(language, "rerun_recommendation")


def proposal_overview(candidates: list[dict], language: str = "en") -> str:
    selected = proposal_candidates(candidates)
    if not selected:
        return "\n".join([ui(language, "overview_header"), ui(language, "overview_empty")])

    rows = [ui(language, "overview_header")]
    for index, candidate in enumerate(selected, start=1):
        managed_loop = candidate.get("managed_loop", {})
        contract = managed_loop.get("completion_contract", {})
        card = decision_card(candidate)
        first_run = first_run_defaults(candidate, managed_loop, contract, card, language)
        action = first_run["recommended_action"]
        reason = candidate_reason(candidate, managed_loop, language)
        rows.append(
            f"| {index} | {table_cell(candidate_display_name(candidate, language))} | "
            f"{table_cell(recommendation_for(candidate, action, language))} | {table_cell(reason)} | `{action}` |"
        )
    return "\n".join(rows)


def render_loop_proposals(candidates: list[dict], language: str = "en") -> str:
    selected = proposal_candidates(candidates)
    if not selected:
        return ui(language, "no_proposal")

    blocks = []
    for index, candidate in enumerate(selected, start=1):
        managed_loop = candidate.get("managed_loop", {})
        contract = managed_loop.get("completion_contract", {})
        card = decision_card(candidate)
        options = card["confirmation_options"]
        first_run = first_run_defaults(candidate, managed_loop, contract, card, language)
        mechanism = mechanism_decision(candidate, managed_loop, language)
        mechanisms = ", ".join(candidate.get("mechanisms") or [candidate.get("mechanism", "none")])
        work_shape = candidate.get("work_shape", "goal-driven" if "loop" in candidate.get("mechanisms", []) else "not recorded")
        loop_archetype = candidate.get("loop_archetype", "not recorded")
        state_file = managed_loop.get("state_file", f".sixloops/state/{candidate['id']}.json")
        clarify_label = "Clarify"
        act_label = "Act" if language == "en" else "Act"
        verify_label = "Verify" if language == "en" else "Verify"
        deliver_label = "Deliver / Stop" if language == "en" else "Deliver / Stop"
        reply_label = "Reply with one line:" if language == "en" else "回复其中一行："
        goal_label = "Goal" if language == "en" else "目标"
        first_cycle_label = "First cycle" if language == "en" else "第一轮"
        verify_stop_label = "Verify and stop" if language == "en" else "验证和停止"
        details_label = "Details kept in the full card" if language == "en" else "完整细节保留在单独卡片"
        review_label = "Review boundary" if language == "en" else "审查边界"
        blocks.append(
            "\n".join(
                [
                    ui(language, "proposal_title").format(index=index, name=candidate_display_name(candidate, language)),
                    "",
                    f"{ui(language, 'recommended_start')}: `{first_run['recommended_action']}`",
                    "",
                    f"{goal_label}: {candidate_objective(candidate, managed_loop, language)}",
                    "",
                    reply_label,
                    "",
                    "\n".join(f"- `{option}`" for option in options),
                    "",
                    f"{first_cycle_label}:",
                    "",
                    f"1. {clarify_label}: {first_run['first_run_observe']}; {first_run['first_run_decide']}.",
                    f"2. {act_label}: {first_run['first_run_act']}.",
                    f"3. {verify_label}: {first_run['first_run_verify']}",
                    f"4. {deliver_label}: {ui(language, 'state')} `{state_file}`; {ui(language, 'stop_after')} {first_run['first_run_stop_after']}; {review_label}: {first_run['first_run_human_gate']}",
                    "",
                    f"{verify_stop_label}:",
                    "",
                    bullet_block(verification_items(candidate, contract, language), language),
                    "",
                    bullet_block(stop_items(candidate, contract, language), language),
                    "",
                    ui(language, "run_card_line").format(
                        can_use_now=display_flag(card["can_use_now"], language),
                        can_confirm=display_flag(card["can_confirm"], language),
                        can_delegate=display_flag(card["can_delegate"], language),
                    ),
                    "",
                    ui(language, "decision_line").format(
                        decision=candidate["decision"], mechanisms=mechanisms, confidence=candidate["confidence"]
                    ),
                    "",
                    ui(language, "work_shape_line").format(work_shape=work_shape, loop_archetype=loop_archetype),
                    "",
                    f"{details_label}: `cards/{candidate['id']}.md`",
                    "",
                    f"{ui(language, 'why_mechanism')}: {mechanism['why_this_mechanism']}",
                ]
            )
        )
    return "\n\n".join(blocks)


def confirmation_prompt(candidates: list[dict], language: str = "en") -> str:
    selected = proposal_candidates(candidates)
    if not selected:
        return ui(language, "no_proposal_next")
    names = ", ".join(candidate_display_name(item, language) for item in selected)
    options = "\n".join(f"- `{option}`" for item in selected for option in decision_card(item)["confirmation_options"])
    return (
        f"{ui(language, 'start_reply_note')}\n\n"
        f"{ui(language, 'choose_from').format(names=names)} "
        f"{ui(language, 'chosen_mode_effect')}\n\n"
        f"{options}"
    )


def source_limitations(data: dict, language: str = "en") -> str:
    source = data.get("source", {})
    providers = source.get("providers") or {}
    source_types = source.get("source_types") or {}
    provider_text = ", ".join(f"{key}={value}" for key, value in providers.items()) if providers else ui(language, "not_recorded")
    source_type_text = ", ".join(f"{key}={value}" for key, value in source_types.items()) if source_types else ui(language, "not_recorded")
    parts = [
        f"{ui(language, 'files')}: {source.get('transcript_files', 0)}",
        f"{ui(language, 'records')}: {source.get('records', 0)}",
        f"{ui(language, 'providers')}: {provider_text}",
        f"{ui(language, 'source_types')}: {source_type_text}",
    ]
    if source_types.get("auxiliary-evidence") and not (providers.get("codex") or providers.get("claude")):
        parts.append(ui(language, "auxiliary_limitation"))
    return "; ".join(str(part) for part in parts)


SECRET_ASSIGNMENT = re.compile(
    r"\b(?:api[_-]?key|token|secret|password|passwd|pwd|credential)\s*[:=]\s*[^\s'\"`]+",
    re.IGNORECASE,
)
BEARER_TOKEN = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE)
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
WINDOWS_PRIVATE_PATH = re.compile(r"\b[A-Za-z]:\\(?:Users|WorkFILE|Documents and Settings)\\[^\s'\"`<>|]+", re.IGNORECASE)
POSIX_PRIVATE_PATH = re.compile(r"(?<!\w)/(?:Users|home)/[^\s'\"`<>|]+")
HIGH_ENTROPY = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_+/=-]{40,}(?![A-Za-z0-9])")


def entropy(value: str) -> float:
    if not value:
        return 0.0
    frequencies = {char: value.count(char) / len(value) for char in set(value)}
    return -sum(freq * math.log2(freq) for freq in frequencies.values())


def looks_like_secret(value: str) -> bool:
    return any(char.isalpha() for char in value) and any(char.isdigit() for char in value) and entropy(value) >= 4.3


def scan_public_text(text: str) -> list[dict]:
    findings: list[dict] = []
    checks = [
        ("secret-assignment", SECRET_ASSIGNMENT),
        ("bearer-token", BEARER_TOKEN),
        ("email", EMAIL),
        ("private-windows-path", WINDOWS_PRIVATE_PATH),
        ("private-posix-path", POSIX_PRIVATE_PATH),
    ]
    for kind, pattern in checks:
        for match in pattern.finditer(text):
            findings.append({"kind": kind, "match": match.group(0)[:120]})
    for match in HIGH_ENTROPY.finditer(text):
        token = match.group(0)
        if looks_like_secret(token):
            findings.append({"kind": "high-entropy-token", "match": token[:120]})
    return findings


def run_optional_secret_scanner(out_dir: Path) -> dict:
    scanners = {"gitleaks": shutil.which("gitleaks"), "trufflehog": shutil.which("trufflehog")}
    result = {"available": {key: bool(value) for key, value in scanners.items()}, "executed": [], "findings": [], "errors": []}
    if scanners["gitleaks"]:
        try:
            completed = subprocess.run(
                [
                    scanners["gitleaks"],
                    "detect",
                    "--no-git",
                    "--source",
                    str(out_dir),
                    "--redact",
                    "--exit-code",
                    "1",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            result["executed"].append("gitleaks")
            if completed.returncode == 1:
                result["findings"].append({"tool": "gitleaks", "summary": (completed.stdout + completed.stderr)[-1000:]})
            elif completed.returncode not in {0}:
                result["errors"].append({"tool": "gitleaks", "summary": (completed.stdout + completed.stderr)[-1000:]})
        except (OSError, subprocess.SubprocessError) as exc:
            result["errors"].append({"tool": "gitleaks", "error": str(exc)})
    if scanners["trufflehog"]:
        try:
            completed = subprocess.run(
                [scanners["trufflehog"], "filesystem", "--json", str(out_dir)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            result["executed"].append("trufflehog")
            if completed.stdout.strip():
                result["findings"].append({"tool": "trufflehog", "summary": completed.stdout[-1000:]})
            elif completed.returncode not in {0}:
                result["errors"].append({"tool": "trufflehog", "summary": completed.stderr[-1000:]})
        except (OSError, subprocess.SubprocessError) as exc:
            result["errors"].append({"tool": "trufflehog", "error": str(exc)})
    return result


def scan_public_artifacts(out_dir: Path) -> dict:
    stdlib_findings: list[dict] = []
    for path in out_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for finding in scan_public_text(text):
            stdlib_findings.append({"path": path.as_posix(), **finding})
    optional = run_optional_secret_scanner(out_dir)
    return {
        "version": 1,
        "scanner": "stdlib-context-entropy-plus-optional-tools",
        "stdlib_findings": stdlib_findings,
        "optional_scanners": optional,
        "blocked": bool(stdlib_findings or optional.get("findings")),
    }


def safe_candidate_summary(candidate: dict) -> dict:
    card = decision_card(candidate)
    managed_loop = candidate.get("managed_loop", {}) if isinstance(candidate.get("managed_loop"), dict) else {}
    contract = managed_loop.get("completion_contract", {}) if isinstance(managed_loop.get("completion_contract"), dict) else {}
    return {
        "id": candidate.get("id"),
        "name": candidate.get("name"),
        "summary": candidate.get("summary"),
        "decision": candidate.get("decision"),
        "mechanisms": candidate.get("mechanisms", []),
        "confidence": candidate.get("confidence"),
        "can_delegate": card.get("can_delegate"),
        "confirmation_options": card.get("confirmation_options", []),
        "control": {
            "will_do": as_list(managed_loop.get("cycle_steps", candidate.get("actions", [])))[:5],
            "must_ask_before": candidate.get("safety", {}).get("requires_approval_for", []),
            "verifies_with": contract.get("verifier_commands", candidate.get("verification", [])),
            "stops_when": contract.get("reject_conditions", candidate.get("stop_conditions", [])),
        },
        "source_limitations": where_wrong(candidate),
    }


def safe_scope_policy(scope: dict) -> dict:
    return {
        "approved": bool(scope.get("approved")),
        "allowed_roles": scope.get("allowed_roles", []),
        "allow_redacted_snippets": bool(scope.get("allow_redacted_snippets")),
        "output_visibility": scope.get("output_visibility", "private"),
    }


def safe_source_summary(source: dict) -> dict:
    return {
        "transcript_files": source.get("transcript_files", 0),
        "records": source.get("records", 0),
        "providers": source.get("providers", {}),
        "source_types": source.get("source_types", {}),
    }


def candidate_card(candidate: dict, scope: dict | None = None, language: str = "en") -> str:
    scope = scope or {}
    evidence = candidate.get("evidence", [{}])
    first_evidence = evidence[0] if evidence else {}
    managed_loop = candidate.get("managed_loop", {})
    contract = managed_loop.get("completion_contract", {})
    exits = loop_exit_contract(candidate, managed_loop, contract)
    card = decision_card(candidate)
    first_run = first_run_defaults(candidate, managed_loop, contract, card, language)
    mechanism = mechanism_decision(candidate, managed_loop, language)
    economics = candidate.get("economics") or {}
    maturity = managed_loop.get(
        "recommended_maturity",
        candidate.get("safety", {}).get("autonomy_level", "draft-only"),
    )
    mode = display_mode_for_candidate(candidate, card, managed_loop, language)
    generated_options = card["confirmation_options"]
    start_options_text = "\n".join(f"- `{option}`" for option in generated_options) or f"- `reject {candidate['id']}`"
    values = {
        "name": candidate_display_name(candidate, language),
        "id": candidate["id"],
        "decision": candidate["decision"],
        "confidence": candidate["confidence"],
        "mechanism": ", ".join(candidate.get("mechanisms") or [candidate.get("mechanism", "none")]),
        "work_shape": candidate.get("work_shape", "goal-driven" if "loop" in candidate.get("mechanisms", []) else "not recorded"),
        "loop_archetype": candidate.get("loop_archetype", "not recorded"),
        "can_use_now": display_flag(card["can_use_now"], language),
        "can_confirm": display_flag(card["can_confirm"], language),
        "can_delegate": display_flag(card["can_delegate"], language),
        "missing_before_delegate": bullet(card.get("missing_before_delegate", []), language),
        "next_action": card["next_action"],
        "recommended_action": first_run["recommended_action"],
        "mode_display": mode,
        "start_options": start_options_text,
        "first_run_goal": first_run["first_run_goal"],
        "first_run_success_criteria": first_run["first_run_success_criteria"],
        "first_run_observe": first_run["first_run_observe"],
        "first_run_decide": first_run["first_run_decide"],
        "first_run_act": first_run["first_run_act"],
        "first_run_verify": first_run["first_run_verify"],
        "first_run_stop_after": first_run["first_run_stop_after"],
        "first_run_human_gate": first_run["first_run_human_gate"],
        "why_this_mechanism": mechanism["why_this_mechanism"],
        "why_not_smaller": mechanism["why_not_smaller"],
        "why_not_more_autonomous": mechanism["why_not_more_autonomous"],
        "primary_verifier": bullet_block(verification_items(candidate, contract, language), language),
        "checker": localized_text(
            contract.get("evaluator_agent"),
            language,
            "优先使用确定性检查；命令无法判断时使用只读 checker。",
            "Use deterministic checks first; use a read-only checker when commands cannot decide.",
        ),
        "pass_evidence_required": bullet_block(
            localized_items(contract.get("pass_evidence_required", []), language, ["命令输出、状态检查、截图、结构化结果或明确验证说明。"]),
            language,
        ),
        "current_rung": mode,
        "next_rung": next_mode_for_candidate(candidate, card, maturity),
        "expected_trigger_frequency": str(economics.get("expected_trigger_frequency", "unknown")),
        "expected_per_run_cost": str(economics.get("expected_per_run_cost", "unknown")),
        "automatic_rejection_signals": bullet_block(
            localized_items(
                economics.get("automatic_rejection_signals", candidate.get("verification", [])),
                language,
                ["验证信号不足、审查边界被触发，或当前事项不再可行动。"],
            ),
            language,
        ),
        "human_review_load": str(economics.get("human_review_load", "medium")),
        "demote_if": localized_text(
            economics.get("demote_if"),
            language,
            "当已审查产出少于一半被接受、验证证据持续较弱，或人工判断主导该 Loop 时降级。",
            "Demote when fewer than half of reviewed outputs are accepted, verifier evidence stays weak, or human judgment dominates the loop.",
        ),
        "summary": localized_text(candidate.get("summary"), language, "该候选用于处理重复出现、可验证、需要边界控制的问题。", candidate.get("summary", "")),
        "source": first_evidence.get("source", "n/a"),
        "signal_kind": (
            f"{first_evidence.get('kind', 'n/a')} / {first_evidence.get('role', 'unknown')} / "
            f"{first_evidence.get('provider', 'unknown')} / {first_evidence.get('source_type', 'unknown')} / "
            f"{first_evidence.get('intent', 'unknown')}"
        ),
        "snippet": evidence_text(first_evidence, scope, language),
        "control_will_do": bullet_block(cycle_steps(candidate, managed_loop, language)[:5], language),
        "control_will_not": bullet_block(control_will_not(candidate, managed_loop, language), language),
        "control_must_ask": bullet_block(
            candidate.get("safety", {}).get("requires_approval_for", [])
            or candidate.get("safety", {}).get("human_checkpoint", [])
            or (["扩大范围、不可逆动作或需要人工判断"] if language == "zh" else ["scope expansion, irreversible action, or human judgment"]),
            language,
        ),
        "control_verify": bullet_block(verification_items(candidate, contract, language), language),
        "control_stop": bullet_block(stop_items(candidate, contract, language) or [first_run["first_run_stop_after"]], language),
        "control_why": mechanism["why_this_mechanism"],
        "where_this_may_be_wrong": bullet_block(where_wrong(candidate, language), language),
        "trigger": bullet(trigger_items(candidate, managed_loop, language), language),
        "artifact": bullet(candidate.get("artifacts", []), language),
        "goal": localized_text(candidate.get("summary"), language, "该候选用于处理重复出现、可验证、需要边界控制的问题。", candidate.get("summary", "")),
        "input": bullet(localized_items(candidate.get("inputs", []), language, ["当前输入、状态文件、相关日志或项目上下文。"]), language),
        "action": bullet(cycle_steps(candidate, managed_loop, language), language),
        "verification": bullet(verification_items(candidate, contract, language), language),
        "stop_condition": bullet(stop_items(candidate, contract, language), language),
        "managed_objective": candidate_objective(candidate, managed_loop, language),
        "managed_trigger": bullet_block(trigger_items(candidate, managed_loop, language), language),
        "managed_discovery_sources": bullet_block(
            localized_items(managed_loop.get("discovery_sources", candidate.get("inputs", [])), language, ["当前输入、状态文件、相关日志或项目上下文。"]),
            language,
        ),
        "managed_heartbeat": managed_loop.get("heartbeat", "goal"),
        "managed_recommended_maturity": maturity,
        "managed_display_mode": mode,
        "managed_state_file": managed_loop.get("state_file", f".sixloops/state/{candidate['id']}.json"),
        "managed_state_schema": mapping_block(managed_loop.get("state_schema", {}), language),
        "managed_cycle_steps": bullet_block(cycle_steps(candidate, managed_loop, language), language),
        "managed_selection_policy": bullet_block(
            localized_items(managed_loop.get("selection_policy", []), language, ["优先处理影响明确、证据充分、验证路径清楚的事项。"]),
            language,
        ),
        "managed_max_items_per_cycle": str(managed_loop.get("max_items_per_cycle", 3)),
        "managed_max_iterations_per_run": str(managed_loop.get("max_iterations_per_run", 8)),
        "contract_success_criteria": bullet_block(
            localized_items(contract.get("success_criteria", []), language, ["聚焦验证通过，或明确记录阻塞原因。"]),
            language,
        ),
        "contract_verifier_commands": bullet_block(verification_items(candidate, contract, language), language),
        "contract_evaluator_agent": localized_text(
            contract.get("evaluator_agent"),
            language,
            "优先使用确定性检查；命令无法判断时使用只读 checker。",
            ui(language, "not_recorded"),
        ),
        "contract_pass_evidence_required": bullet_block(
            localized_items(contract.get("pass_evidence_required", []), language, ["命令输出、状态检查、截图、结构化结果或明确验证说明。"]),
            language,
        ),
        "contract_reject_conditions": bullet_block(stop_items(candidate, contract, language), language),
        "contract_no_progress_policy": localized_text(
            contract.get("no_progress_policy"),
            language,
            "如果连续两轮没有新增证据、范围没有收窄、验证仍不清楚，记录阻塞并停止。",
            ui(language, "not_recorded"),
        ),
        **exit_contract_values(exits, language),
        "managed_change_policy": localized_text(
            managed_loop.get("change_policy"),
            language,
            "只在有直接证据时做低风险修改；改文件时使用隔离分支或 worktree。",
            "Only make low-risk changes with direct evidence. Use an isolated branch or worktree when modifying files.",
        ),
        "managed_deliverables": bullet_block(
            localized_items(managed_loop.get("deliverables", []), language, ["状态摘要、验证证据、必要时的补丁或交接说明。"]),
            language,
        ),
        "managed_resume_policy": localized_text(
            managed_loop.get("resume_policy"),
            language,
            "先读取状态文件，继续未完成事项，再开始新工作。",
            "Read the state file first and continue unresolved items before starting new work.",
        ),
        "managed_failure_policy": localized_text(
            managed_loop.get("failure_policy"),
            language,
            "验证失败或需要人工判断时记录阻塞并停止。",
            "Record the blocker and stop when verification fails or human judgment is required.",
        ),
        "managed_promotion_criteria": bullet_block(
            localized_items(managed_loop.get("promotion_criteria", []), language, ["多次运行通过验证且人工审查持续接受产出后再升级。"]),
            language,
        ),
        "managed_demotion_criteria": bullet_block(
            localized_items(managed_loop.get("demotion_criteria", []), language, ["产出反复被拒、验证不稳定、成本上升或人工判断长期主导时降级。"]),
            language,
        ),
        "autonomy_level": candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        "approval_required_action": bullet(candidate.get("safety", {}).get("requires_approval_for", []), language),
        "human_checkpoint": bullet(candidate.get("safety", {}).get("human_checkpoint", []), language),
        "budget_caps": bullet(candidate.get("safety", {}).get("budget_caps", []), language),
        "downgrade_notes": candidate.get("downgrade_notes", ui(language, "none")),
    }
    return fill(load_template("loop-card.md", language), values) + "\n" + render_trace(candidate, language)


def claude_loop(candidate: dict) -> str:
    managed_loop = candidate.get("managed_loop", {})
    contract = managed_loop.get("completion_contract", {})
    exits = loop_exit_contract(candidate, managed_loop, contract)
    values = {
        "loop_name": candidate["name"],
        "goal": managed_loop.get("objective", candidate["summary"]),
        "cadence_or_trigger": bullet_block(managed_loop.get("cadence_or_trigger", candidate.get("trigger", []))),
        "heartbeat": managed_loop.get("heartbeat", "goal"),
        "recommended_maturity": managed_loop.get(
            "recommended_maturity",
            candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        ),
        "discovery_sources": bullet_block(managed_loop.get("discovery_sources", candidate.get("inputs", []))),
        "context_source": bullet_block(candidate.get("inputs", [])),
        "state_file": managed_loop.get("state_file", f".sixloops/state/{candidate['id']}.json"),
        "state_schema": mapping_block(managed_loop.get("state_schema", {})),
        "contract_success_criteria": bullet_block(contract.get("success_criteria", [])),
        "contract_verifier_commands": bullet_block(contract.get("verifier_commands", [])),
        "contract_evaluator_agent": contract.get("evaluator_agent", "Not recorded."),
        "contract_pass_evidence_required": bullet_block(contract.get("pass_evidence_required", [])),
        "contract_reject_conditions": bullet_block(contract.get("reject_conditions", [])),
        "contract_no_progress_policy": contract.get("no_progress_policy", "Not recorded."),
        **exit_contract_values(exits),
        "cycle_steps": bullet_block(managed_loop.get("cycle_steps", candidate.get("actions", []))),
        "selection_policy": bullet_block(managed_loop.get("selection_policy", [])),
        "max_items_per_cycle": str(managed_loop.get("max_items_per_cycle", 3)),
        "max_iterations_per_run": str(managed_loop.get("max_iterations_per_run", 8)),
        "change_policy": managed_loop.get("change_policy", "Only make low-risk changes with direct evidence. Use an isolated branch or worktree when modifying files."),
        "deliverables": bullet_block(managed_loop.get("deliverables", [])),
        "verification_signal": bullet_block(candidate.get("verification", [])),
        "resume_policy": managed_loop.get("resume_policy", "Read the state file first and continue unresolved items before starting new work."),
        "failure_policy": managed_loop.get("failure_policy", "Record the blocker and stop when verification fails or human judgment is required."),
        "stop_condition": bullet_block(candidate.get("stop_conditions", [])),
        "promotion_criteria": bullet_block(managed_loop.get("promotion_criteria", [])),
        "demotion_criteria": bullet_block(managed_loop.get("demotion_criteria", [])),
        "autonomy_level": candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        "approval_required_action": bullet_block(candidate.get("safety", {}).get("requires_approval_for", [])),
        "human_checkpoint": bullet_block(candidate.get("safety", {}).get("human_checkpoint", [])),
        "budget_caps": bullet_block(candidate.get("safety", {}).get("budget_caps", [])),
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


def decision_index(candidates: list[dict], language: str = "en") -> str:
    return "\n".join(
        f"| {table_cell(candidate_display_name(item, language))} | {table_cell(', '.join(item.get('mechanisms') or [item.get('mechanism', 'none')]))} | "
        f"{table_cell(item['decision'])} | {table_cell(item['confidence'])} |"
        for item in candidates
    ) or ("| 无 | none | reject | low |" if language == "zh" else "| None | none | reject | low |")


def playbook(data: dict, out_dir: Path, rendered_paths: list[str], language: str = "en") -> str:
    candidates = data.get("candidates", [])
    selected = proposal_candidates(candidates)
    selected_count = len(selected)
    summary = ui(language, "summary").format(count=selected_count)
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
        line = f"- `{item['id']}`: {localized_text(item.get('summary'), language, '该候选用于处理重复出现、可验证、需要边界控制的问题。', item.get('summary', ''))}"
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
            by_mechanism["rejected"].append(
                f"- `{item['id']}`: {localized_text(item.get('downgrade_notes'), language, '该候选当前不适合启动。', item.get('downgrade_notes', ''))}"
            )

    template = load_template("loop-playbook.md", language)
    values = {
        "project": Path.cwd().name,
        "analysis_window": "显式本地输入" if language == "zh" else "explicit local inputs",
        "transcript_source_summary": (
            f"{data.get('source', {}).get('transcript_files', 0)} 个文件，"
            f"{data.get('source', {}).get('records', 0)} 条记录"
            if language == "zh"
            else f"{data.get('source', {}).get('transcript_files', 0)} file(s), "
            f"{data.get('source', {}).get('records', 0)} record(s)"
        ),
        "redaction_status": ui(language, "enabled"),
        "summary": summary,
        "proposal_overview": proposal_overview(candidates, language),
        "loop_proposals": render_loop_proposals(candidates, language),
        "confirmation_prompt": confirmation_prompt(candidates, language),
        "candidate": selected[0]["id"] if selected else "<candidate-id>",
        "rules_and_memory": "\n".join(by_mechanism["rule"]) or ui(language, "none"),
        "skill_candidates": "\n".join(by_mechanism["skill"]) or ui(language, "none"),
        "hook_candidates": "\n".join(by_mechanism["hook"]) or ui(language, "none"),
        "loop_candidates": "\n".join(by_mechanism["loop"]) or ui(language, "none"),
        "approval_gates": "\n".join(by_mechanism["approval"]) or ui(language, "none"),
        "rejected_candidates": "\n".join(by_mechanism["rejected"]) or ui(language, "none"),
        "decision_index": decision_index(candidates, language),
        "private_output": ".sixloops/private/candidates.json",
        "shareable_output": "\n- ".join(rendered_paths) if rendered_paths else str(out_dir / "loop-playbook.md"),
        "source_limitations": source_limitations(data, language),
    }
    rendered = fill(template, values)
    scope = data.get("scope_policy") or {}
    scope_lines = [
        "",
        ui(language, "scope_heading"),
        "",
        f"{ui(language, 'approved')}: `{bool_label(bool(scope.get('approved', False)), language)}`",
        "",
        f"{ui(language, 'allowed_roles')}: `{', '.join(scope.get('allowed_roles', [])) or ui(language, 'not_recorded')}`",
        "",
        f"{ui(language, 'redacted_snippets')}: `{ui(language, 'enabled') if scope.get('allow_redacted_snippets', True) else ui(language, 'disabled')}`",
        "",
        f"{ui(language, 'output_visibility')}: `{scope.get('output_visibility', 'private')}`",
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
    parser.add_argument(
        "--language",
        default="auto",
        choices=["auto", "en", "zh"],
        help="User-facing artifact language. Default: auto-detect from user evidence.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    language = detect_output_language(data, args.language)
    scope_policy = data.get("scope_policy") or {}
    out_dir = Path(args.out_dir)
    cards_dir = out_dir / "cards"
    loops_dir = out_dir / "claude-loops"
    skills_dir = out_dir / "skills"
    for directory in (cards_dir, loops_dir, skills_dir):
        directory.mkdir(parents=True, exist_ok=True)

    rendered_paths: list[str] = []
    for candidate in data.get("candidates", []):
        card_path = cards_dir / f"{candidate['id']}.md"
        card_path.write_text(candidate_card(candidate, scope_policy, language), encoding="utf-8")
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
        "scope_policy": safe_scope_policy(scope_policy),
        "source": safe_source_summary(data.get("source", {})),
        "redaction": data.get("redaction"),
        "artifact_visibility": "local-shareable-after-review",
        "private_candidates": ".sixloops/private/candidates.json",
        "candidates": [safe_candidate_summary(candidate) for candidate in data.get("candidates", [])],
    }
    summary_path.write_text(json.dumps(public_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rendered_paths.append(summary_path.as_posix())

    playbook_path = out_dir / "loop-playbook.md"
    playbook_path.write_text(playbook(data, out_dir, rendered_paths, language), encoding="utf-8")
    rendered_paths.append(playbook_path.as_posix())
    scan_result = scan_public_artifacts(out_dir)
    scan_path = out_dir / "artifact-safety.json"
    scan_path.write_text(json.dumps(scan_result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rendered_paths.append(scan_path.as_posix())
    public_summary["artifact_safety"] = {
        "scanner": scan_result.get("scanner"),
        "blocked": scan_result.get("blocked", False),
        "stdlib_findings": len(scan_result.get("stdlib_findings", [])),
        "optional_scanners": {
            "available": scan_result.get("optional_scanners", {}).get("available", {}),
            "executed": scan_result.get("optional_scanners", {}).get("executed", []),
            "findings": len(scan_result.get("optional_scanners", {}).get("findings", [])),
            "errors": len(scan_result.get("optional_scanners", {}).get("errors", [])),
        },
    }
    summary_path.write_text(json.dumps(public_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if scan_result["blocked"]:
        raise ValueError(f"Public artifact safety scan found possible leaks: {scan_path}")
    print(f"Rendered {len(rendered_paths)} artifact(s): {out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"render_artifacts.py: {exc}", file=sys.stderr)
        raise SystemExit(1)
