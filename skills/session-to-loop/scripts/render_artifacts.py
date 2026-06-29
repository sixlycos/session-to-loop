#!/usr/bin/env python3
"""Render redacted candidate artifacts from scored pipeline output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from loop_contract import normalize_exit_contract


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


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def mapping_block(value: dict) -> str:
    if not value:
        return "None."
    return "\n".join(f"- {key}: {item}" for key, item in value.items())


def first(items: list[str], default: str = "None.") -> str:
    return items[0] if items else default


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


def exit_contract_values(exits: dict) -> dict[str, str]:
    protocol = exits.get("status_protocol", {})
    return {
        "exit_continue_only_if": bullet_block(exits.get("continue_only_if", [])),
        "exit_done_when": bullet_block(exits.get("done_when", [])),
        "exit_needs_human_when": bullet_block(exits.get("needs_human_when", [])),
        "exit_blocked_when": bullet_block(exits.get("blocked_when", [])),
        "exit_budget_stopped_when": bullet_block(exits.get("budget_stopped_when", [])),
        "exit_status_protocol": mapping_block(protocol if isinstance(protocol, dict) else {}),
    }


def bool_label(value: bool) -> str:
    return "yes" if value else "no"


def next_rung(current: str) -> str:
    ladder = [
        "read-only-report",
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


def confirmation_options(candidate: dict) -> list[str]:
    card = candidate.get("decision_card") or {}
    options = card.get("confirmation_options")
    if isinstance(options, list) and options:
        return [str(item) for item in options[:4]]
    candidate_id = candidate["id"]
    smaller = "skill" if "skill" in candidate.get("mechanisms", []) else "checklist"
    return [
        f"adopt {candidate_id} as read-only",
        f"adopt {candidate_id} as goal-loop",
        f"shrink {candidate_id} to {smaller}",
        f"reject {candidate_id}",
    ]


def first_run_defaults(candidate: dict, managed_loop: dict, contract: dict) -> dict[str, str]:
    packet = candidate.get("first_run_packet") or {}
    max_iterations = managed_loop.get("max_iterations_per_run", 8)
    verifier = first(contract.get("verifier_commands", []), first(candidate.get("verification", []), "Run the focused verifier."))
    state_file = managed_loop.get("state_file", f".session-to-loop/state/{candidate['id']}.json")
    approvals = candidate.get("safety", {}).get("requires_approval_for", [])
    human_gate = packet.get("human_gate") or (
        f"Ask before {', '.join(approvals)}." if approvals else "Ask before expanding scope, changing risk boundaries, or making irreversible changes."
    )
    success_criteria = packet.get("success_criteria")
    if isinstance(success_criteria, list):
        success_text = bullet_block([str(item) for item in success_criteria])
    elif success_criteria:
        success_text = str(success_criteria)
    else:
        success_text = bullet_block(contract.get("success_criteria", candidate.get("verification", [])))
    maturity = managed_loop.get("recommended_maturity", "goal-loop")
    default_action = "adopt as read-only" if maturity == "read-only-report" else "adopt as goal-loop"
    return {
        "recommended_action": str(packet.get(
            "recommended_action",
            default_action,
        )),
        "first_run_goal": str(packet.get("goal", managed_loop.get("objective", candidate.get("summary", "Run the loop.")))),
        "first_run_success_criteria": success_text,
        "first_run_observe": str(packet.get(
            "observe",
            "read the state file, current inputs, and latest verifier evidence",
        )),
        "first_run_decide": str(packet.get(
            "decide",
            f"choose at most {managed_loop.get('max_items_per_cycle', 3)} item(s), the next action, and any human gate",
        )),
        "first_run_act": str(packet.get(
            "act",
            f"pick at most {managed_loop.get('max_items_per_cycle', 3)} directly evidenced item(s)",
        )),
        "first_run_verify": str(packet.get("verify", verifier)),
        "first_run_stop_after": str(packet.get(
            "stop_after",
            f"{max_iterations} iterations, repeated failure, no progress across two iterations, or a human gate",
        )),
        "first_run_human_gate": str(human_gate),
    }


def mechanism_decision(candidate: dict, managed_loop: dict) -> dict[str, str]:
    decision = candidate.get("mechanism_decision") or {}
    mechanisms = candidate.get("mechanisms", [])
    if "loop" in mechanisms:
        why = "This needs repeated observe-decide-act-verify behavior with state, verification, stop conditions, and resume behavior."
        smaller = "A rule, skill, or checklist alone would not preserve state or drive repeated verification."
    else:
        why = "This is useful, but the evidence does not justify a managed loop yet."
        smaller = "A smaller mechanism is recommended first."
    maturity = managed_loop.get("recommended_maturity", candidate.get("safety", {}).get("autonomy_level", "draft-only"))
    return {
        "why_this_mechanism": decision.get("why_this_mechanism", why),
        "why_not_smaller": decision.get("why_not_smaller", smaller),
        "why_not_more_autonomous": decision.get(
            "why_not_more_autonomous",
            f"Start at `{maturity}` until verifier evidence and accepted outputs justify promotion.",
        ),
    }


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


def approval_boundary(candidate: dict) -> str:
    approvals = candidate.get("safety", {}).get("requires_approval_for", [])
    if approvals:
        return "; ".join(approvals)
    return "No extra approval boundary recorded beyond normal repo review."


def decision_card(candidate: dict) -> dict:
    card = candidate.get("decision_card") or {}
    return {
        "can_use_now": card.get("can_use_now", "limited" if candidate.get("decision") != "reject" else "no"),
        "can_confirm": card.get("can_confirm", "yes" if candidate.get("verification") else "no"),
        "can_delegate": card.get("can_delegate", "yes" if "loop" in candidate.get("mechanisms", []) else "no"),
        "missing_before_delegate": card.get("missing_before_delegate", []),
        "next_action": card.get("next_action", "adopt" if candidate.get("decision") != "reject" else "reject"),
        "confirmation_options": confirmation_options(candidate),
    }


def proposal_candidates(candidates: list[dict]) -> list[dict]:
    loops = [item for item in candidates if item.get("decision") != "reject" and "loop" in item.get("mechanisms", [])]
    if loops:
        return loops[:3]
    return [item for item in candidates if item.get("decision") != "reject"][:3]


def why_this_loop(candidate: dict) -> str:
    trace = candidate.get("decision_trace", {})
    role_counts = trace.get("role_counts", {})
    providers = trace.get("provider_counts", {})
    if providers.get("auxiliary"):
        basis = "project auxiliary evidence"
    elif role_counts.get("user", 0):
        basis = "repeated user-language evidence"
    elif role_counts.get("tool", 0):
        basis = "tool-use evidence"
    else:
        basis = "available local evidence"
    return f"{candidate.get('summary', 'No summary recorded.')} Basis: {basis}."


def render_loop_proposals(candidates: list[dict]) -> str:
    selected = proposal_candidates(candidates)
    if not selected:
        return "No loop proposal is ready. The useful outcome is to keep the rejected findings as context and gather better session evidence."

    blocks = []
    for index, candidate in enumerate(selected, start=1):
        managed_loop = candidate.get("managed_loop", {})
        contract = managed_loop.get("completion_contract", {})
        exits = loop_exit_contract(candidate, managed_loop, contract)
        card = decision_card(candidate)
        options = card["confirmation_options"]
        first_run = first_run_defaults(candidate, managed_loop, contract)
        mechanism = mechanism_decision(candidate, managed_loop)
        mechanisms = ", ".join(candidate.get("mechanisms") or [candidate.get("mechanism", "none")])
        work_shape = candidate.get("work_shape", "goal-driven" if "loop" in candidate.get("mechanisms", []) else "not recorded")
        loop_archetype = candidate.get("loop_archetype", "not recorded")
        heartbeat = managed_loop.get("heartbeat", "goal")
        maturity = managed_loop.get(
            "recommended_maturity",
            candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        )
        state_file = managed_loop.get("state_file", f".session-to-loop/state/{candidate['id']}.json")
        blocks.append(
            "\n".join(
                [
                    f"### {index}. {candidate['name']}",
                    "",
                    f"Decision: `{candidate['decision']}` | Mechanism: `{mechanisms}` | Confidence: `{candidate['confidence']}`",
                    "",
                    f"Can use now: `{card['can_use_now']}` | Can confirm: `{card['can_confirm']}` | Can delegate: `{card['can_delegate']}`",
                    "",
                    f"Next action: `{card['next_action']}`",
                    "",
                    "Confirm with one:",
                    "",
                    "\n".join(f"- `{option}`" for option in options),
                    "",
                    f"Goal: {managed_loop.get('objective', candidate.get('summary', 'No objective recorded.'))}",
                    "",
                    f"Work shape: `{work_shape}` | Archetype: `{loop_archetype}`",
                    "",
                    f"Heartbeat: `{heartbeat}` | Recommended starting level: `{maturity}`",
                    "",
                    "First run:",
                    "",
                    f"- Observe: {first_run['first_run_observe']}",
                    f"- Decide: {first_run['first_run_decide']}",
                    f"- Act: {first_run['first_run_act']}",
                    f"- Verify: {first_run['first_run_verify']}",
                    f"- State: {state_file}",
                    f"- Stop after: {first_run['first_run_stop_after']}",
                    "",
                    "Trigger:",
                    "",
                    bullet_block(managed_loop.get("cadence_or_trigger", candidate.get("trigger", []))),
                    "",
                    "Loop cycle:",
                    "",
                    bullet_block(managed_loop.get("cycle_steps", candidate.get("actions", []))),
                    "",
                    "Verification:",
                    "",
                    bullet_block(candidate.get("verification", [])),
                    "",
                    "Stop conditions:",
                    "",
                    bullet_block(candidate.get("stop_conditions", [])),
                    "",
                    f"Iteration cap: {managed_loop.get('max_iterations_per_run', 8)} run iteration(s)",
                    "",
                    f"Approval boundary: {approval_boundary(candidate)}",
                    "",
                    "Acceptance contract:",
                    "",
                    bullet_block(contract.get("success_criteria", [])),
                    "",
                    "Exit contract:",
                    "",
                    "Continue only if:",
                    "",
                    bullet_block(exits.get("continue_only_if", [])),
                    "",
                    "Return `DONE` when:",
                    "",
                    bullet_block(exits.get("done_when", [])),
                    "",
                    "Return `NEEDS_HUMAN` when:",
                    "",
                    bullet_block(exits.get("needs_human_when", [])),
                    "",
                    "Return `BLOCKED` when:",
                    "",
                    bullet_block(exits.get("blocked_when", [])),
                    "",
                    "Return `BUDGET_STOPPED` when:",
                    "",
                    bullet_block(exits.get("budget_stopped_when", [])),
                    "",
                    f"Why this mechanism: {mechanism['why_this_mechanism']} {why_this_loop(candidate)}",
                ]
            )
        )
    return "\n\n".join(blocks)


def confirmation_prompt(candidates: list[dict]) -> str:
    selected = proposal_candidates(candidates)
    if not selected:
        return "Recommended next step: run a narrower transcript analysis or keep these as rejected context."
    names = ", ".join(f"`{item['name']}`" for item in selected)
    options = "\n".join(f"- `{option}`" for item in selected for option in confirmation_options(item))
    return (
        f"Confirm which proposal(s) to adopt from {names}. After confirmation, generate the concrete loop card, "
        "draft skill or hook/checklist, and the state-file convention for the selected loop.\n\n"
        f"{options}"
    )


def source_limitations(data: dict) -> str:
    source = data.get("source", {})
    providers = source.get("providers") or {}
    source_types = source.get("source_types") or {}
    provider_text = ", ".join(f"{key}={value}" for key, value in providers.items()) if providers else "not recorded"
    source_type_text = ", ".join(f"{key}={value}" for key, value in source_types.items()) if source_types else "not recorded"
    parts = [
        f"Files: {source.get('transcript_files', 0)}",
        f"records: {source.get('records', 0)}",
        f"providers: {provider_text}",
        f"source types: {source_type_text}",
    ]
    if source_types.get("auxiliary-evidence") and not (providers.get("codex") or providers.get("claude")):
        parts.append("This run used project auxiliary evidence, so proposals should stay draft until the user confirms fit.")
    return "; ".join(str(part) for part in parts)


def candidate_card(candidate: dict) -> str:
    evidence = candidate.get("evidence", [{}])
    first_evidence = evidence[0] if evidence else {}
    managed_loop = candidate.get("managed_loop", {})
    contract = managed_loop.get("completion_contract", {})
    exits = loop_exit_contract(candidate, managed_loop, contract)
    card = decision_card(candidate)
    options = card["confirmation_options"]
    first_run = first_run_defaults(candidate, managed_loop, contract)
    mechanism = mechanism_decision(candidate, managed_loop)
    economics = candidate.get("economics") or {}
    maturity = managed_loop.get(
        "recommended_maturity",
        candidate.get("safety", {}).get("autonomy_level", "draft-only"),
    )
    values = {
        "name": candidate["name"],
        "id": candidate["id"],
        "decision": candidate["decision"],
        "confidence": candidate["confidence"],
        "mechanism": ", ".join(candidate.get("mechanisms") or [candidate.get("mechanism", "none")]),
        "work_shape": candidate.get("work_shape", "goal-driven" if "loop" in candidate.get("mechanisms", []) else "not recorded"),
        "loop_archetype": candidate.get("loop_archetype", "not recorded"),
        "can_use_now": card["can_use_now"],
        "can_confirm": card["can_confirm"],
        "can_delegate": card["can_delegate"],
        "missing_before_delegate": bullet(card.get("missing_before_delegate", [])),
        "next_action": card["next_action"],
        "recommended_action": first_run["recommended_action"],
        "confirm_as_read_only": options[0] if len(options) > 0 else f"adopt {candidate['id']} as read-only",
        "confirm_as_goal_loop": options[1] if len(options) > 1 else f"adopt {candidate['id']} as goal-loop",
        "shrink_to_smaller_mechanism": options[2] if len(options) > 2 else f"shrink {candidate['id']} to skill",
        "reject_candidate": options[3] if len(options) > 3 else f"reject {candidate['id']}",
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
        "primary_verifier": bullet_block(contract.get("verifier_commands", candidate.get("verification", []))),
        "checker": contract.get("evaluator_agent", "Use deterministic checks first; use a read-only checker when commands cannot decide."),
        "pass_evidence_required": bullet_block(contract.get("pass_evidence_required", [])),
        "current_rung": maturity,
        "next_rung": next_rung(maturity),
        "expected_trigger_frequency": str(economics.get("expected_trigger_frequency", "unknown")),
        "expected_per_run_cost": str(economics.get("expected_per_run_cost", "unknown")),
        "automatic_rejection_signals": bullet_block(
            as_list(economics.get("automatic_rejection_signals", candidate.get("verification", [])))
        ),
        "human_review_load": str(economics.get("human_review_load", "medium")),
        "demote_if": str(economics.get(
            "demote_if",
            "Demote when fewer than half of reviewed outputs are accepted, verifier evidence stays weak, or human judgment dominates the loop.",
        )),
        "summary": candidate["summary"],
        "source": first_evidence.get("source", "n/a"),
        "signal_kind": (
            f"{first_evidence.get('kind', 'n/a')} / {first_evidence.get('role', 'unknown')} / "
            f"{first_evidence.get('provider', 'unknown')} / {first_evidence.get('source_type', 'unknown')} / "
            f"{first_evidence.get('intent', 'unknown')}"
        ),
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
        "managed_discovery_sources": bullet_block(managed_loop.get("discovery_sources", candidate.get("inputs", []))),
        "managed_heartbeat": managed_loop.get("heartbeat", "goal"),
        "managed_recommended_maturity": maturity,
        "managed_state_file": managed_loop.get("state_file", f".session-to-loop/state/{candidate['id']}.json"),
        "managed_state_schema": mapping_block(managed_loop.get("state_schema", {})),
        "managed_cycle_steps": bullet_block(managed_loop.get("cycle_steps", candidate.get("actions", []))),
        "managed_selection_policy": bullet_block(managed_loop.get("selection_policy", [])),
        "managed_max_items_per_cycle": str(managed_loop.get("max_items_per_cycle", 3)),
        "managed_max_iterations_per_run": str(managed_loop.get("max_iterations_per_run", 8)),
        "contract_success_criteria": bullet_block(contract.get("success_criteria", [])),
        "contract_verifier_commands": bullet_block(contract.get("verifier_commands", [])),
        "contract_evaluator_agent": contract.get("evaluator_agent", "Not recorded."),
        "contract_pass_evidence_required": bullet_block(contract.get("pass_evidence_required", [])),
        "contract_reject_conditions": bullet_block(contract.get("reject_conditions", [])),
        "contract_no_progress_policy": contract.get("no_progress_policy", "Not recorded."),
        **exit_contract_values(exits),
        "managed_change_policy": managed_loop.get("change_policy", "Only make low-risk changes with direct evidence. Use an isolated branch or worktree when modifying files."),
        "managed_deliverables": bullet_block(managed_loop.get("deliverables", [])),
        "managed_resume_policy": managed_loop.get("resume_policy", "Read the state file first and continue unresolved items before starting new work."),
        "managed_failure_policy": managed_loop.get("failure_policy", "Record the blocker and stop when verification fails or human judgment is required."),
        "managed_promotion_criteria": bullet_block(managed_loop.get("promotion_criteria", [])),
        "managed_demotion_criteria": bullet_block(managed_loop.get("demotion_criteria", [])),
        "autonomy_level": candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        "approval_required_action": bullet(candidate.get("safety", {}).get("requires_approval_for", [])),
        "human_checkpoint": bullet(candidate.get("safety", {}).get("human_checkpoint", [])),
        "budget_caps": bullet(candidate.get("safety", {}).get("budget_caps", [])),
        "downgrade_notes": candidate.get("downgrade_notes", "None."),
    }
    return fill(load_template("loop-card.md"), values) + "\n" + render_trace(candidate)


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
        "state_file": managed_loop.get("state_file", f".session-to-loop/state/{candidate['id']}.json"),
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


def playbook(data: dict, out_dir: Path, rendered_paths: list[str]) -> str:
    candidates = data.get("candidates", [])
    selected = proposal_candidates(candidates)
    selected_count = len(selected)
    summary = f"Prepared {selected_count} user-confirmable loop engineering proposal(s) from local evidence."
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
        "loop_proposals": render_loop_proposals(candidates),
        "confirmation_prompt": confirmation_prompt(candidates),
        "candidate": selected[0]["id"] if selected else "<candidate-id>",
        "rules_and_memory": "\n".join(by_mechanism["rule"]) or "None.",
        "skill_candidates": "\n".join(by_mechanism["skill"]) or "None.",
        "hook_candidates": "\n".join(by_mechanism["hook"]) or "None.",
        "loop_candidates": "\n".join(by_mechanism["loop"]) or "None.",
        "approval_gates": "\n".join(by_mechanism["approval"]) or "None.",
        "rejected_candidates": "\n".join(by_mechanism["rejected"]) or "None.",
        "private_output": ".session-to-loop/private/candidates.json",
        "shareable_output": "\n- ".join(rendered_paths) if rendered_paths else str(out_dir / "loop-playbook.md"),
        "source_limitations": source_limitations(data),
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
        "source": data.get("source"),
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
