# [Input] Public Claude SDK status/boundary/root usage messages and saved Chat display metadata.
# [Output] Copied compaction/context-use snapshots and closed public history projection; only a real boundary confirms completion.
# [Pos] Service-local display projection, independent of Runtime execution/controls.
# [Sync] 2026-10-12: preserve cycle identity, boundary deduplication and sealed terminal snapshots.
# [Sync] 2026-10-12: project latest root request input usage with the CLI-reported model window, never billing aggregates.
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


def _safe_integer(value: Any, *, positive: bool = False) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and (1 if positive else 0) <= value <= 2**53 - 1


def public_context_usage(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("status") == "unavailable":
        return {"status": "unavailable"}
    model, tokens, window = (value.get(key) for key in ("model", "inputTokens", "contextWindow"))
    if (value.get("status") != "available" or not isinstance(model, str) or not model.strip()
            or not _safe_integer(tokens) or not _safe_integer(window, positive=True)):
        return None
    return {"status": "available", "model": model, "inputTokens": tokens, "contextWindow": window}


def public_context_compaction_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Project only the closed display fields from saved Chat metadata."""
    usage = public_context_usage(metadata.get("contextUsage"))
    result: dict[str, Any] = {"contextUsage": usage} if usage is not None else {}
    candidates = metadata.get("contextCompactions")
    if not isinstance(candidates, list):
        return result
    rows: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        identity, state, trigger = (candidate.get(key) for key in ("id", "state", "trigger"))
        if (not isinstance(identity, str) or not identity.strip()
                or state not in ("running", "completed", "cancelled", "failed", "unconfirmed")
                or trigger not in (None, "manual", "auto")
                or (state == "completed" and trigger is None)):
            continue
        rows[identity] = {"id": identity, "state": state, "trigger": trigger}
    if not rows:
        return result
    result["contextCompactions"] = list(rows.values())
    completion = metadata.get("compactCompletionText")
    if (isinstance(completion, str)
            and (completion.strip() == "Compacted" or completion.strip().startswith("Compacted "))
            and any(row["state"] == "completed" and row["trigger"] == "manual" for row in rows.values())):
        result["compactCompletionText"] = completion
    return result


@dataclass
class ContextUsageTracker:
    """Display-only last root API input usage; the CLI owns window resolution."""
    candidate: tuple[str, int] | None = None
    snapshot: dict[str, Any] = field(default_factory=lambda: {"status": "unavailable"})
    closed: bool = False
    stream_model: str | None = None
    stream_usage: dict[str, Any] = field(default_factory=dict)

    def invalidate(self) -> bool:
        if self.closed:
            return False
        changed = self.snapshot["status"] != "unavailable"
        self.candidate = None
        self.stream_model = None
        self.stream_usage = {}
        self.snapshot = {"status": "unavailable"}
        return changed

    def observe_assistant(self, model: Any, usage: Any, *, parent: Any = None, error: Any = None) -> None:
        if self.closed or parent is not None or model == "<synthetic>" or self.stream_model is not None:
            return
        self.invalidate()
        if error is not None or not isinstance(model, str) or not model.strip() or not isinstance(usage, Mapping):
            return
        counts = [usage.get("input_tokens"), usage.get("cache_creation_input_tokens", 0), usage.get("cache_read_input_tokens", 0)]
        if not all(_safe_integer(count) for count in counts):
            return
        total = sum(counts)
        if _safe_integer(total):
            self.candidate = (model, total)

    def observe_stream(self, event: Any, *, parent: Any = None) -> None:
        """Merge one root API request's final usage, never a turn aggregate.

        OpenAI/Responses bridges may report input only in message_delta;
        the SDK assistant block can precede that final update with zero input.
        """
        if self.closed or parent is not None or not isinstance(event, Mapping):
            return
        kind = event.get("type")
        if kind == "message_start":
            self.invalidate()
            message = event.get("message")
            model = message.get("model") if isinstance(message, Mapping) else None
            if not isinstance(model, str) or not model.strip() or model == "<synthetic>":
                return
            self.stream_model = model
            usage = message.get("usage")
        elif kind == "message_delta" and self.stream_model is not None:
            usage = event.get("usage")
        elif kind == "message_stop" and self.stream_model is not None:
            counts = [self.stream_usage.get("input_tokens"), self.stream_usage.get("cache_creation_input_tokens", 0), self.stream_usage.get("cache_read_input_tokens", 0)]
            if all(_safe_integer(count) for count in counts) and _safe_integer(sum(counts)):
                self.candidate = (self.stream_model, sum(counts))
            return
        else:
            return
        if isinstance(usage, Mapping):
            for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
                if key in usage:
                    self.stream_usage[key] = usage[key]

    def observe_result(self, model_usage: Any, selected_model: Any, *, is_error: bool) -> bool:
        if self.closed:
            return False
        previous = self.snapshot
        self.snapshot = {"status": "unavailable"}
        if not is_error and self.candidate is not None and isinstance(model_usage, Mapping):
            actual_model, tokens = self.candidate
            details = model_usage.get(actual_model)
            window = details.get("contextWindow") if isinstance(details, Mapping) else None
            projected = public_context_usage({"status": "available", "model": selected_model,
                                              "inputTokens": tokens, "contextWindow": window})
            if projected is not None:
                self.snapshot = projected
        return previous != self.snapshot

    def finish(self, *, invalidate: bool) -> bool:
        changed = self.invalidate() if invalidate else False
        self.closed = True
        return changed

    def metadata(self) -> dict[str, Any]:
        return {"contextUsage": dict(self.snapshot)}


@dataclass
class ContextCompactionTracker:
    rows: list[dict[str, Any]] = field(default_factory=list)
    current: dict[str, Any] | None = None
    completion_text: str | None = None
    closed: bool = False
    _status_ids: set[str] = field(default_factory=set)
    _boundary_ids: set[str] = field(default_factory=set)

    def consume(self, subtype: str, data: Mapping[str, Any]) -> bool:
        if self.closed:
            return False
        event_id = data.get("uuid")
        if not isinstance(event_id, str) or not event_id.strip():
            return False
        if subtype == "status":
            if "status" not in data or data["status"] not in ("compacting", None):
                return False
            if event_id in self._status_ids:
                return False
            self._status_ids.add(event_id)
            if data["status"] == "compacting":
                if self.current is None:
                    self.current = {"id": event_id, "state": "running", "trigger": None}
                    self.rows.append(self.current)
                    return True
                if self.current["state"] != "running":
                    self.current["state"] = "running"
                    return True
            elif self.current is not None and self.current["state"] == "running":
                self.current["state"] = "unconfirmed"
                return True
            return False

        if subtype != "compact_boundary" or event_id in self._boundary_ids:
            return False
        metadata = data.get("compact_metadata")
        if not isinstance(metadata, Mapping) or metadata.get("trigger") not in ("manual", "auto"):
            return False
        self._boundary_ids.add(event_id)
        if self.current is None:
            self.current = {"id": event_id, "state": "completed", "trigger": metadata["trigger"]}
            self.rows.append(self.current)
        else:
            self.current.update(state="completed", trigger=metadata["trigger"])
        self.current = None
        return True

    def finish(self, state: str) -> bool:
        """Terminate an unfinished display row without inventing a boundary."""
        if self.closed:
            return False
        self.closed = True
        if self.current is None:
            return False
        changed = self.current["state"] != state
        self.current["state"] = state
        self.current = None
        return changed

    def record_completion_text(self, text: str) -> bool:
        if self.closed:
            return False
        normalized = text.strip()
        if normalized != "Compacted" and not normalized.startswith("Compacted "):
            return False
        if self.completion_text == text:
            return False
        self.completion_text = text
        return any(row["state"] == "completed" and row["trigger"] == "manual" for row in self.rows)

    def metadata(self) -> dict[str, Any]:
        if not self.rows:
            return {}
        result: dict[str, Any] = {"contextCompactions": [dict(row) for row in self.rows]}
        if self.completion_text is not None and any(
            row["state"] == "completed" and row["trigger"] == "manual" for row in self.rows
        ):
            result["compactCompletionText"] = self.completion_text
        return result
