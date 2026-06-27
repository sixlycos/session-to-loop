#!/usr/bin/env python3
"""Normalize Codex, Claude Code, and generic JSONL transcript records."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator


@dataclass
class SourceClassification:
    provider: str
    source_type: str
    confidence: str
    reason: str


@dataclass
class NormalizedEvent:
    provider: str
    session_id: str
    event_index: int
    role: str
    event_kind: str
    text: str
    tool_name: str | None = None
    structured: dict[str, Any] = field(default_factory=dict)
    raw_type: str | None = None

    @property
    def source(self) -> str:
        return f"session:{self.session_id}#event-{self.event_index}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source"] = self.source
        return data


def iter_jsonl(path: Path) -> Iterator[tuple[int, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                yield line_number, json.loads(line)


def lower_str(value: Any) -> str:
    return value.lower() if isinstance(value, str) else ""


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)
    if isinstance(value, dict):
        preferred = []
        for key in (
            "text",
            "content",
            "message",
            "name",
            "command",
            "arguments",
            "input",
            "output",
            "result",
            "kind",
            "case",
            "provider",
            "http_status",
            "latency_ms",
            "assertion",
            "action",
            "route",
            "target",
            "snapshot",
            "screenshot",
            "i18n",
            "stdout",
            "stderr",
            "summary",
            "msg",
        ):
            if key in value:
                preferred.append(flatten_text(value[key]))
        if preferred:
            return " ".join(part for part in preferred if part)
        return " ".join(flatten_text(item) for item in value.values())
    return ""


def content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") in {"text", "input_text", "output_text"}:
                parts.append(flatten_text(item.get("text") or item.get("content")))
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(part for part in parts if part)
    return flatten_text(content)


def codex_session_meta_id(record: dict[str, Any]) -> str | None:
    meta = record.get("session_meta")
    if not isinstance(meta, dict):
        return None
    payload = meta.get("payload")
    if isinstance(payload, dict):
        for key in ("id", "session_id", "conversation_id"):
            if payload.get(key):
                return str(payload[key])
    for key in ("id", "session_id", "conversation_id"):
        if meta.get(key):
            return str(meta[key])
    return None


def detect_provider(record: Any) -> str:
    if not isinstance(record, dict):
        return "generic"
    if any(key in record for key in ("response_item", "event_msg", "session_meta", "turn_context")):
        return "codex"
    if "sessionId" in record or "uuid" in record or "parentUuid" in record:
        return "claude"
    message = record.get("message")
    if isinstance(message, dict) and isinstance(message.get("role"), str):
        return "claude"
    return "generic"


def classify_file(path: Path, sample_size: int = 20) -> SourceClassification:
    records = []
    providers: dict[str, int] = {}
    for _, record in iter_jsonl(path):
        records.append(record)
        provider = detect_provider(record)
        providers[provider] = providers.get(provider, 0) + 1
        if len(records) >= sample_size:
            break

    if providers.get("codex", 0):
        return SourceClassification("codex", "native-transcript", "high", "matched Codex session_meta/response_item/event_msg shape")
    if providers.get("claude", 0):
        return SourceClassification("claude", "native-transcript", "high", "matched Claude sessionId/message/tool content shape")
    if looks_auxiliary_evidence(path, records):
        return SourceClassification("auxiliary", "auxiliary-evidence", "medium", "matched engineering log/audit/result indicators")
    return SourceClassification("generic", "generic-jsonl", "low", "JSONL shape did not match native transcript indicators")


def looks_auxiliary_evidence(path: Path, records: list[Any]) -> bool:
    path_text = path.as_posix().lower()
    name_hints = (
        "audit",
        "browse",
        "soak",
        "result",
        "results/raw",
        "log",
        "eval",
        "report",
        "screenshot",
        "latency",
    )
    if any(hint in path_text for hint in name_hints):
        return True

    text = " ".join(flatten_text(record).lower() for record in records[:10])
    content_hints = (
        "http 200",
        "status",
        "latency",
        "assertion",
        "screenshot",
        "snapshot",
        "goto",
        "click",
        "fill",
        "request",
        "response",
        "passed",
        "failed",
    )
    return any(hint in text for hint in content_hints)


class CodexAdapter:
    provider = "codex"

    def __init__(self) -> None:
        self.session_id = "unknown-session"

    def normalize(self, record: Any, event_index: int) -> list[NormalizedEvent]:
        if not isinstance(record, dict):
            return []
        meta_id = codex_session_meta_id(record)
        if meta_id:
            self.session_id = meta_id
        if "session_meta" in record and len(record) == 1:
            return []

        item = record.get("response_item")
        if isinstance(item, dict):
            return self._response_item(item, record, event_index)

        event = record.get("event_msg")
        if isinstance(event, dict):
            return [
                NormalizedEvent(
                    provider=self.provider,
                    session_id=self.session_id,
                    event_index=event_index,
                    role="tool",
                    event_kind="status",
                    text=flatten_text(event),
                    tool_name=tool_name_from(event),
                    structured={"event_msg": event},
                    raw_type="event_msg",
                )
            ]
        return []

    def _response_item(self, item: dict[str, Any], record: dict[str, Any], event_index: int) -> list[NormalizedEvent]:
        session_id = str(item.get("session_id") or item.get("conversation_id") or self.session_id)
        item_type = lower_str(item.get("type"))
        role = lower_str(item.get("role"))
        if role in {"user", "assistant"}:
            return [
                NormalizedEvent(
                    provider=self.provider,
                    session_id=session_id,
                    event_index=event_index,
                    role=role,
                    event_kind="message",
                    text=content_text(item.get("content") or item.get("text") or item.get("message")),
                    structured={"response_item": item},
                    raw_type=item_type or None,
                )
            ]
        if item_type in {"function_call", "tool_call"}:
            return [
                NormalizedEvent(
                    provider=self.provider,
                    session_id=session_id,
                    event_index=event_index,
                    role="tool",
                    event_kind="tool_call",
                    text=flatten_text({"name": item.get("name"), "arguments": item.get("arguments") or item.get("input")}),
                    tool_name=tool_name_from(item),
                    structured={"response_item": item},
                    raw_type=item_type,
                )
            ]
        if item_type in {"function_call_output", "tool_result"}:
            return [
                NormalizedEvent(
                    provider=self.provider,
                    session_id=session_id,
                    event_index=event_index,
                    role="tool",
                    event_kind="tool_result",
                    text=flatten_text(item.get("output") or item.get("content") or item.get("result")),
                    tool_name=tool_name_from(item),
                    structured={"response_item": item},
                    raw_type=item_type,
                )
            ]
        if item_type == "reasoning":
            return [
                NormalizedEvent(
                    provider=self.provider,
                    session_id=session_id,
                    event_index=event_index,
                    role="assistant",
                    event_kind="reasoning",
                    text=flatten_text(item),
                    structured={"response_item": item},
                    raw_type=item_type,
                )
            ]
        return []


class ClaudeAdapter:
    provider = "claude"

    def normalize(self, record: Any, event_index: int) -> list[NormalizedEvent]:
        if not isinstance(record, dict):
            return []
        session_id = str(record.get("sessionId") or record.get("session_id") or record.get("conversation_id") or "unknown-session")
        record_type = lower_str(record.get("type"))
        message = record.get("message")
        if isinstance(message, dict):
            return self._message(record, message, session_id, record_type, event_index)
        if record_type in {"user", "assistant", "tool"}:
            return [
                NormalizedEvent(
                    provider=self.provider,
                    session_id=session_id,
                    event_index=event_index,
                    role=record_type,
                    event_kind="message" if record_type != "tool" else "tool_result",
                    text=flatten_text(record),
                    tool_name=tool_name_from(record),
                    structured={"record": record},
                    raw_type=record_type,
                )
            ]
        return []

    def _message(
        self,
        record: dict[str, Any],
        message: dict[str, Any],
        session_id: str,
        record_type: str,
        event_index: int,
    ) -> list[NormalizedEvent]:
        role = lower_str(message.get("role") or record_type)
        content = message.get("content")
        events: list[NormalizedEvent] = []

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if not isinstance(item, dict):
                    text_parts.append(flatten_text(item))
                    continue
                item_type = lower_str(item.get("type"))
                if item_type in {"text", "input_text", "output_text"}:
                    text_parts.append(flatten_text(item.get("text") or item.get("content")))
                elif item_type == "tool_use":
                    events.append(
                        NormalizedEvent(
                            provider=self.provider,
                            session_id=session_id,
                            event_index=event_index,
                            role="tool",
                            event_kind="tool_call",
                            text=flatten_text({"name": item.get("name"), "input": item.get("input")}),
                            tool_name=tool_name_from(item),
                            structured={"tool_use": item},
                            raw_type=item_type,
                        )
                    )
                elif item_type == "tool_result":
                    events.append(
                        NormalizedEvent(
                            provider=self.provider,
                            session_id=session_id,
                            event_index=event_index,
                            role="tool",
                            event_kind="tool_result",
                            text=flatten_text(item.get("content") or item.get("text")),
                            tool_name=tool_name_from(item),
                            structured={"tool_result": item},
                            raw_type=item_type,
                        )
                    )
            text = " ".join(part for part in text_parts if part)
        else:
            text = flatten_text(content)

        if role in {"user", "assistant"} and text:
            events.insert(
                0,
                NormalizedEvent(
                    provider=self.provider,
                    session_id=session_id,
                    event_index=event_index,
                    role=role,
                    event_kind="message",
                    text=text,
                    structured={"message": message},
                    raw_type=record_type or None,
                ),
            )
        return events


class GenericJsonlAdapter:
    provider = "generic"

    def normalize(self, record: Any, event_index: int) -> list[NormalizedEvent]:
        if not isinstance(record, dict):
            return [
                NormalizedEvent(
                    provider=self.provider,
                    session_id="unknown-session",
                    event_index=event_index,
                    role="unknown",
                    event_kind="raw",
                    text=flatten_text(record),
                    structured={},
                )
            ]
        role = role_from_generic(record)
        session_id = str(record.get("session_id") or record.get("conversation_id") or record.get("sessionId") or "unknown-session")
        return [
            NormalizedEvent(
                provider=self.provider,
                session_id=session_id,
                event_index=event_index,
                role=role,
                event_kind="message" if role in {"user", "assistant"} else "tool_event" if role == "tool" else "raw",
                text=flatten_text(record),
                tool_name=tool_name_from(record),
                structured={"record": record},
                raw_type=lower_str(record.get("type") or record.get("role")) or None,
            )
        ]


class AuxiliaryEvidenceAdapter:
    provider = "auxiliary"

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    def normalize(self, record: Any, event_index: int) -> list[NormalizedEvent]:
        return [
            NormalizedEvent(
                provider=self.provider,
                session_id=self.session_id,
                event_index=event_index,
                role="tool",
                event_kind="auxiliary_evidence",
                text=flatten_text(record),
                tool_name=tool_name_from(record) if isinstance(record, dict) else None,
                structured={"record": record} if isinstance(record, dict) else {},
                raw_type=lower_str(record.get("type")) if isinstance(record, dict) else None,
            )
        ]


def role_from_generic(record: dict[str, Any]) -> str:
    role = record.get("type") or record.get("role")
    if isinstance(role, str) and role.lower() in {"user", "assistant", "tool"}:
        return role.lower()
    message = record.get("message")
    if isinstance(message, dict) and isinstance(message.get("role"), str):
        return message["role"].lower()
    return "unknown"


def tool_name_from(value: dict[str, Any]) -> str | None:
    for key in ("name", "tool_name"):
        if isinstance(value.get(key), str):
            return value[key]
    return None


def iter_normalized_events(path: Path, source_type: str | None = None, provider_hint: str | None = None) -> Iterator[NormalizedEvent]:
    if source_type == "auxiliary-evidence" or provider_hint == "auxiliary":
        adapter = AuxiliaryEvidenceAdapter(path.stem)
        for event_index, record in iter_jsonl(path):
            for event in adapter.normalize(record, event_index):
                yield event
        return

    adapters = {
        "codex": CodexAdapter(),
        "claude": ClaudeAdapter(),
        "generic": GenericJsonlAdapter(),
    }
    for event_index, record in iter_jsonl(path):
        provider = detect_provider(record)
        for event in adapters[provider].normalize(record, event_index):
            yield event
