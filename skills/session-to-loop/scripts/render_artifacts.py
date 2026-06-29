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

from loop_contract import normalize_exit_contract
from mode_policy import RUN_MODES, SCHEDULED_MODES, level_to_mode


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


def snippets_visible(scope: dict) -> bool:
    return bool(scope.get("allow_redacted_snippets")) and scope.get("output_visibility") == "public"


def evidence_text(first_evidence: dict, scope: dict) -> str:
    if snippets_visible(scope):
        return first_evidence.get("snippet", "No quote needed.")
    return "[snippet hidden; see private candidates.json]"


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


def display_mode_for_candidate(candidate: dict, card: dict | None = None, managed_loop: dict | None = None) -> str:
    if candidate.get("decision") == "reject":
        return "not startable"
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


def first_run_defaults(candidate: dict, managed_loop: dict, contract: dict, card: dict | None = None) -> dict[str, str]:
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
        "first_run_goal": str(packet.get("goal", managed_loop.get("objective", candidate.get("summary", "Run the loop.")))),
        "first_run_success_criteria": success_text,
        "first_run_observe": str(packet.get(
            "observe",
            "read the state file, current inputs, and latest verifier evidence",
        )),
        "first_run_decide": str(packet.get(
            "decide",
            f"choose at most {managed_loop.get('max_items_per_cycle', 3)} item(s), the next action, and any review boundary",
        )),
        "first_run_act": str(packet.get(
            "act",
            f"pick at most {managed_loop.get('max_items_per_cycle', 3)} directly evidenced item(s)",
        )),
        "first_run_verify": str(packet.get("verify", verifier)),
        "first_run_stop_after": str(packet.get(
            "stop_after",
            f"{max_iterations} iterations, repeated failure, no progress across two iterations, or a review boundary",
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
        "why_this_mechanism": candidate.get("why_this_loop") or decision.get("why_this_mechanism", why),
        "why_not_smaller": candidate.get("why_not_smaller") or decision.get("why_not_smaller", smaller),
        "why_not_more_autonomous": decision.get(
            "why_not_more_autonomous",
            candidate.get("why_not_more_autonomous")
            or f"Start at `{maturity}` until verifier evidence and accepted outputs justify promotion.",
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
    return "No extra review boundary recorded beyond normal repo review."


def control_will_not(candidate: dict, managed_loop: dict) -> list[str]:
    items = []
    approvals = candidate.get("safety", {}).get("requires_approval_for", [])
    if approvals:
        items.append(f"Land or finalize review-boundary actions without the matching mode: {', '.join(str(item) for item in approvals)}.")
    change_policy = managed_loop.get("change_policy")
    if change_policy:
        items.append(str(change_policy))
    return items or ["Expand scope, finalize irreversible changes, or act without verifier evidence."]


def where_wrong(candidate: dict) -> list[str]:
    raw = candidate.get("where_this_may_be_wrong")
    items = as_list(raw)
    if items:
        return items
    trace = candidate.get("decision_trace", {})
    source_type_counts = trace.get("source_type_counts", {})
    if source_type_counts:
        return [f"Source mix may limit confidence: {source_type_counts}."]
    return ["The packet set may omit current project state or newer failures."]


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
        first_run = first_run_defaults(candidate, managed_loop, contract, card)
        mechanism = mechanism_decision(candidate, managed_loop)
        mechanisms = ", ".join(candidate.get("mechanisms") or [candidate.get("mechanism", "none")])
        work_shape = candidate.get("work_shape", "goal-driven" if "loop" in candidate.get("mechanisms", []) else "not recorded")
        loop_archetype = candidate.get("loop_archetype", "not recorded")
        heartbeat = managed_loop.get("heartbeat", "goal")
        maturity = managed_loop.get(
            "recommended_maturity",
            candidate.get("safety", {}).get("autonomy_level", "draft-only"),
        )
        mode = display_mode_for_candidate(candidate, card, managed_loop)
        state_file = managed_loop.get("state_file", f".session-to-loop/state/{candidate['id']}.json")
        blocks.append(
            "\n".join(
                [
                    f"### {index}. {candidate['name']}",
                    "",
                    f"Recommended start: `{first_run['recommended_action']}`",
                    "",
                    f"Decision: `{candidate['decision']}` | Mechanism: `{mechanisms}` | Confidence: `{candidate['confidence']}`",
                    "",
                    f"Can start now: `{card['can_use_now']}` | Can confirm: `{card['can_confirm']}` | Can delegate: `{card['can_delegate']}`",
                    "",
                    f"Next action: `{card['next_action']}`",
                    "",
                    "Start with one:",
                    "",
                    "\n".join(f"- `{option}`" for option in options),
                    "",
                    f"What it does: {managed_loop.get('objective', candidate.get('summary', 'No objective recorded.'))}",
                    "",
                    f"Work shape: `{work_shape}` | Archetype: `{loop_archetype}`",
                    "",
                    f"Heartbeat: `{heartbeat}` | Mode: `{mode}` | Internal maturity: `{maturity}`",
                    "",
                    "First cycle:",
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
                    f"Review boundary: {approval_boundary(candidate)}",
                    "",
                    "Acceptance checks:",
                    "",
                    bullet_block(contract.get("success_criteria", [])),
                    "",
                    "Loop exits:",
                    "",
                    "Continue only if:",
                    "",
                    bullet_block(exits.get("continue_only_if", [])),
                    "",
                    "Return `DONE` when:",
                    "",
                    bullet_block(exits.get("done_when", [])),
                    "",
                    "Return for review when:",
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
    options = "\n".join(f"- `{option}`" for item in selected for option in decision_card(item)["confirmation_options"])
    return (
        f"Choose which proposal to start, shrink, or reject from {names}. "
        "If the chosen mode allows edits, run the first controlled cycle in that mode; otherwise generate the run packet and state convention.\n\n"
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


def candidate_card(candidate: dict, scope: dict | None = None) -> str:
    scope = scope or {}
    evidence = candidate.get("evidence", [{}])
    first_evidence = evidence[0] if evidence else {}
    managed_loop = candidate.get("managed_loop", {})
    contract = managed_loop.get("completion_contract", {})
    exits = loop_exit_contract(candidate, managed_loop, contract)
    card = decision_card(candidate)
    first_run = first_run_defaults(candidate, managed_loop, contract, card)
    mechanism = mechanism_decision(candidate, managed_loop)
    economics = candidate.get("economics") or {}
    maturity = managed_loop.get(
        "recommended_maturity",
        candidate.get("safety", {}).get("autonomy_level", "draft-only"),
    )
    mode = display_mode_for_candidate(candidate, card, managed_loop)
    generated_options = card["confirmation_options"]
    start_options_text = "\n".join(f"- `{option}`" for option in generated_options) or f"- `reject {candidate['id']}`"
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
        "primary_verifier": bullet_block(contract.get("verifier_commands", candidate.get("verification", []))),
        "checker": contract.get("evaluator_agent", "Use deterministic checks first; use a read-only checker when commands cannot decide."),
        "pass_evidence_required": bullet_block(contract.get("pass_evidence_required", [])),
        "current_rung": mode,
        "next_rung": next_mode_for_candidate(candidate, card, maturity),
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
        "snippet": evidence_text(first_evidence, scope),
        "control_will_do": bullet_block(as_list(managed_loop.get("cycle_steps", candidate.get("actions", [])))[:5]),
        "control_will_not": bullet_block(control_will_not(candidate, managed_loop)),
        "control_must_ask": bullet_block(
            candidate.get("safety", {}).get("requires_approval_for", [])
            or candidate.get("safety", {}).get("human_checkpoint", [])
            or ["scope expansion, irreversible action, or human judgment"]
        ),
        "control_verify": bullet_block(contract.get("verifier_commands", candidate.get("verification", []))),
        "control_stop": bullet_block(
            as_list(contract.get("reject_conditions", []))
            or as_list(candidate.get("stop_conditions", []))
            or [first_run["first_run_stop_after"]]
        ),
        "control_why": mechanism["why_this_mechanism"],
        "where_this_may_be_wrong": bullet_block(where_wrong(candidate)),
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
        "managed_display_mode": mode,
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
    summary = f"Recommended {selected_count} startable loop plan(s). Choose a mode, shrink the idea, reject it, or rerun with narrower evidence."
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
        card_path.write_text(candidate_card(candidate, scope_policy), encoding="utf-8")
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
        "private_candidates": ".session-to-loop/private/candidates.json",
        "candidates": [safe_candidate_summary(candidate) for candidate in data.get("candidates", [])],
    }
    summary_path.write_text(json.dumps(public_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rendered_paths.append(summary_path.as_posix())

    playbook_path = out_dir / "loop-playbook.md"
    playbook_path.write_text(playbook(data, out_dir, rendered_paths), encoding="utf-8")
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
