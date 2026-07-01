"""Host-native start packet rendering.

SixLoops owns the loop policy and contract. Host runtimes such as Codex and
Claude Code own execution, tool permissions, cancellation, and continuation.
This module renders the bridge between those two layers.
"""

from __future__ import annotations

import json
import platform
import shlex
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOST_PACKET_VERSION = 1
HOST_PACKET_SCHEMA = "https://sixloops.local/schemas/host-start-packet.schema.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strings(value: Any) -> list[str]:
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
        return "1. None."
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1))


def fenced_json(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def clipboard_tool() -> str | None:
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        return "pbcopy"
    if sys.platform.startswith("win"):
        return "Set-Clipboard"
    for tool in ("wl-copy", "xclip", "xsel"):
        if shutil.which(tool):
            return tool
    return None


def detect_host_environment() -> dict:
    return {
        "os": platform.system() or sys.platform,
        "codex": shutil.which("codex"),
        "claude": shutil.which("claude"),
        "clipboard": clipboard_tool(),
    }


def clipboard_command(path: Path) -> str | None:
    resolved = path.resolve()
    if sys.platform == "darwin" and shutil.which("pbcopy"):
        return f"pbcopy < {shlex.quote(str(resolved))}"
    if sys.platform.startswith("win"):
        quoted = "'" + str(resolved).replace("'", "''") + "'"
        return f"Get-Content -Raw {quoted} | Set-Clipboard"
    if shutil.which("wl-copy"):
        return f"wl-copy < {shlex.quote(str(resolved))}"
    if shutil.which("xclip"):
        return f"xclip -selection clipboard < {shlex.quote(str(resolved))}"
    if shutil.which("xsel"):
        return f"xsel --clipboard --input < {shlex.quote(str(resolved))}"
    return None


def launch_command(host: str, project_root: str | None) -> str | None:
    root = shlex.quote(str(Path(project_root or ".").resolve()))
    if host == "codex" and shutil.which("codex"):
        return f"codex -C {root}"
    if host == "claude" and shutil.which("claude"):
        return f"cd {root} && claude"
    return None


def abs_path(path: Path) -> str:
    return str(path.resolve())


def build_host_target(
    *,
    host: str,
    entrypoint: str,
    packet_file: Path,
    project_root: str | None,
    environment: dict,
    language: str,
) -> dict:
    binary = environment.get(host)
    copy = clipboard_command(packet_file)
    if language == "zh":
        instruction = (
            f"运行复制命令后，打开 `{host}` 交互环境，输入 `{entrypoint}`，再粘贴剪贴板内容启动。"
            if binary
            else f"未检测到 `{host}` 命令；仍可手动复制 `{packet_file.name}` 到支持 `{entrypoint}` 的宿主环境。"
        )
    else:
        instruction = (
            f"Run the copy command, open `{host}`, enter `{entrypoint}`, then paste the clipboard content to start."
            if binary
            else f"`{host}` was not detected; manually copy `{packet_file.name}` into a host that supports `{entrypoint}`."
        )
    return {
        "host": host,
        "entrypoint": entrypoint,
        "available": bool(binary),
        "binary": binary,
        "packet_file": abs_path(packet_file),
        "copy_command": copy,
        "launch_command": launch_command(host, project_root),
        "instruction": instruction,
    }


def build_host_manifest(spec: dict, host_files: dict[str, Path]) -> dict:
    language = str(spec.get("language") or "en")
    environment = detect_host_environment()
    targets = [
        build_host_target(
            host="codex",
            entrypoint="/goal",
            packet_file=host_files["codex_goal"],
            project_root=spec.get("project_root"),
            environment=environment,
            language=language,
        ),
        build_host_target(
            host="claude",
            entrypoint="/loop",
            packet_file=host_files["claude_loop"],
            project_root=spec.get("project_root"),
            environment=environment,
            language=language,
        ),
    ]
    return {
        "$schema": HOST_PACKET_SCHEMA,
        "version": HOST_PACKET_VERSION,
        "generated_at": now_iso(),
        "loop_id": spec.get("loop_id"),
        "name": spec.get("name"),
        "source_kind": spec.get("source_kind"),
        "project_root": str(Path(spec.get("project_root") or ".").resolve()),
        "runtime_boundary": (
            "SixLoops emits host-native packets and governs the loop contract; "
            "Codex or Claude Code executes the loop."
        ),
        "environment": environment,
        "targets": targets,
        "files": {key: abs_path(path) for key, path in host_files.items()},
        "governance": {
            "owner": "SixLoops skill collection",
            "review_cadence": "per-release",
            "maturity_tier": "library",
            "lifecycle_stage": "library",
            "rollback_boundary": "Host packets may direct isolated local work, but they do not push, merge, deploy, mutate production, or install hooks.",
            "output_contract": "Codex /goal and Claude /loop packets must include Change Map, verifier, autonomy, progression, exit, state, and approval boundaries.",
        },
    }


def render_host_start(manifest: dict, language: str) -> str:
    targets = manifest["targets"]
    if language == "zh":
        lines = [
            f"# Host 启动包：{manifest['name']}",
            "",
            "SixLoops 只生成宿主可执行的 loop 逻辑包；Codex 或 Claude Code 负责实际运行、工具权限、取消和续跑。",
            "",
            "## 当前环境",
            "",
            f"- Codex CLI：{manifest['environment'].get('codex') or '未检测到'}",
            f"- Claude Code CLI：{manifest['environment'].get('claude') or '未检测到'}",
            f"- 剪贴板工具：{manifest['environment'].get('clipboard') or '未检测到'}",
            "",
            "## 复制命令",
            "",
        ]
        for target in targets:
            lines.extend(
                [
                    f"### {target['host']} `{target['entrypoint']}`",
                    "",
                    f"- Packet：`{target['packet_file']}`",
                    f"- 可用：`{str(target['available']).lower()}`",
                    f"- 复制：`{target['copy_command'] or '手动打开 packet 文件并复制全文'}`",
                    f"- 打开宿主：`{target['launch_command'] or '手动打开宿主环境'}`",
                    f"- 启动方式：{target['instruction']}",
                    "",
                ]
            )
        lines.extend(
            [
                "## 治理边界",
                "",
                "- 这些命令只复制 packet 或打开宿主，不会直接执行 loop。",
                "- `/goal` 和 `/loop` 内的自动纠正、状态更新、回滚边界和交还条件由 SixLoops packet 定义。",
                "- 触达 push、merge、deploy、生产、数据、凭证、计费、不可逆或扩范围动作时必须停止并交还。",
                "",
                "## 文件",
                "",
                bullet([f"`{path}`" for path in manifest["files"].values()]),
                "",
            ]
        )
        return "\n".join(lines)

    lines = [
        f"# Host Start Packet: {manifest['name']}",
        "",
        "SixLoops emits the host-native loop contract; Codex or Claude Code owns execution, tool permissions, cancellation, and continuation.",
        "",
        "## Environment",
        "",
        f"- Codex CLI: {manifest['environment'].get('codex') or 'not detected'}",
        f"- Claude Code CLI: {manifest['environment'].get('claude') or 'not detected'}",
        f"- Clipboard tool: {manifest['environment'].get('clipboard') or 'not detected'}",
        "",
        "## Copy Commands",
        "",
    ]
    for target in targets:
        lines.extend(
            [
                f"### {target['host']} `{target['entrypoint']}`",
                "",
                f"- Packet: `{target['packet_file']}`",
                f"- Available: `{str(target['available']).lower()}`",
                f"- Copy: `{target['copy_command'] or 'manually open the packet file and copy all text'}`",
                f"- Open host: `{target['launch_command'] or 'open the host manually'}`",
                f"- Start: {target['instruction']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Governance Boundary",
            "",
            "- These commands copy a packet or open a host; they do not directly execute the loop.",
            "- SixLoops defines autocorrection, state updates, rollback boundaries, and return conditions inside the `/goal` or `/loop` packet.",
            "- Stop and return before push, merge, deploy, production, data, credential, billing, irreversible, or scope-expanding actions.",
            "",
            "## Files",
            "",
            bullet([f"`{path}`" for path in manifest["files"].values()]),
            "",
        ]
    )
    return "\n".join(lines)


def render_host_packet(spec: dict, target: str) -> str:
    language = str(spec.get("language") or "en")
    is_zh = language == "zh"
    host_name = "Codex" if target == "codex" else "Claude Code"
    entrypoint = "/goal" if target == "codex" else "/loop"
    title = f"{host_name} {entrypoint} Packet"
    if is_zh:
        return f"""# {title}：{spec["name"]}

把本文件全文复制到 {host_name} 的 `{entrypoint}` 输入中启动。SixLoops 负责 loop 逻辑、自动纠正策略、状态契约和回滚边界；{host_name} 负责实际运行。

## 运行边界

- 宿主入口：`{entrypoint}`
- 项目根目录：`{spec.get("project_root")}`
- 运行模式：`{spec.get("mode")}`（内部级别 `{spec.get("internal_level")}`）
- 协作方式：`{spec.get("team_mode")}`
- 状态文件：`{spec.get("state_file")}`
- 单轮最多事项：`{spec.get("max_items")}`
- 单次最多轮数：`{spec.get("max_iterations")}`

## 目标

{spec.get("objective")}

## 改造图景

{spec.get("change_map")}

## 首轮执行

{spec.get("first_cycle")}

## 每轮协议

{numbered(strings(spec.get("cycle_steps")))}

## 自动纠正策略

- 验收失败时，不要问用户普通工程优先级；先基于失败证据选择一个更小、更可验证、更可回退的下一步。
- 如果存在多个可行下一步，按用户价值、验收器可用性、可回退性、风险和 Change Map 推进程度排序，选择最高价值的非阻塞步骤。
- 不重复同一步，除非下一次使用了新证据、更窄假设或不同验收器。
- 只有下一轮能产生新的验收证据，且 `next_cursor`、`next_expected_evidence`、`next_verifier` 具体时，才返回 `CONTINUE`。
- 如果产品、架构、发布、安全、数据、计费、权限、生产、不可逆或扩范围判断阻塞下一步，先写决策包，再交还用户。

## 选择规则

{bullet(strings(spec.get("selection_policy")))}

## 验收方式

{bullet(strings(spec.get("verification")))}

必须留下的通过证据：

{bullet(strings(spec.get("pass_evidence")))}

## 回滚和隔离

{bullet(strings(spec.get("rollback_policy")))}

## 推进合同

{fenced_json(spec.get("progression_contract"))}

## 自主合同

{fenced_json(spec.get("autonomy_contract"))}

## 退出合同

{fenced_json(spec.get("exit_contract"))}

## 明确批准点

{bullet(strings(spec.get("approval_boundary")))}

## 返回格式

结束前只返回一个状态：`DONE`、`CONTINUE`、`NEEDS_HUMAN`、`BLOCKED` 或 `BUDGET_STOPPED`。

返回前更新状态，至少写入：

{bullet(strings(spec.get("state_updates_required")))}
"""

    return f"""# {title}: {spec["name"]}

Copy this entire file into the {host_name} `{entrypoint}` input to start. SixLoops owns the loop policy, autocorrection strategy, state contract, and rollback boundary; {host_name} owns runtime execution.

## Runtime Boundary

- Host entrypoint: `{entrypoint}`
- Project root: `{spec.get("project_root")}`
- Mode: `{spec.get("mode")}` (`{spec.get("internal_level")}` internally)
- Team mode: `{spec.get("team_mode")}`
- State file: `{spec.get("state_file")}`
- Max items per cycle: `{spec.get("max_items")}`
- Max iterations per run: `{spec.get("max_iterations")}`

## Objective

{spec.get("objective")}

## Change Map

{spec.get("change_map")}

## First Cycle

{spec.get("first_cycle")}

## Cycle Protocol

{numbered(strings(spec.get("cycle_steps")))}

## Autocorrection Strategy

- When verification fails, do not ask the user for ordinary engineering prioritization; choose a smaller, more verifiable, more reversible next shot from the failure evidence.
- When multiple next actions are plausible, rank by user value, verifier availability, reversibility, risk, and progress toward the Change Map, then choose the best non-blocking action.
- Do not repeat a shot unless the next attempt uses new evidence, a narrower hypothesis, or a different verifier.
- Return `CONTINUE` only when the next cycle can produce new verifier evidence and `next_cursor`, `next_expected_evidence`, and `next_verifier` are concrete.
- If product, architecture, release, security, data, billing, permission, production, irreversible, or scope expansion judgment blocks the next action, write a decision packet before returning to the user.

## Selection Policy

{bullet(strings(spec.get("selection_policy")))}

## Verification

{bullet(strings(spec.get("verification")))}

Required pass evidence:

{bullet(strings(spec.get("pass_evidence")))}

## Rollback And Isolation

{bullet(strings(spec.get("rollback_policy")))}

## Progression Contract

{fenced_json(spec.get("progression_contract"))}

## Autonomy Contract

{fenced_json(spec.get("autonomy_contract"))}

## Exit Contract

{fenced_json(spec.get("exit_contract"))}

## Explicit Approval Points

{bullet(strings(spec.get("approval_boundary")))}

## Return Format

Return exactly one status before stopping: `DONE`, `CONTINUE`, `NEEDS_HUMAN`, `BLOCKED`, or `BUDGET_STOPPED`.

Before returning, update state with at least:

{bullet(strings(spec.get("state_updates_required")))}
"""
