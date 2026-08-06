"""Safe, run-bound Dream Agent message projections and dispatch claims.

The generic Claude Agent routes intentionally expose rich UI parts.  This
adapter is the only Story Workspace boundary that turns those parts/events
into the small text-and-safe-activity contract consumed by the Dream workbench.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import sqlite3
import math
import re
import time
from typing import Any, AsyncGenerator, Callable, Optional
from uuid import uuid4

try:
    from story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessage,
        StoryWorkspaceDreamAgentActivityContent,
        StoryWorkspaceDreamAgentMessageAccepted,
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamAgentMessageSnapshot,
        StoryWorkspaceDreamAgentTextContent,
        StoryWorkspaceDreamAgentToolConfirmationAccepted,
        StoryWorkspaceDreamAgentToolConfirmationCommand,
        StoryWorkspaceDreamRunContext,
        STORY_WORKSPACE_DREAM_AGENT_ANSWER_TEXT_MAX,
        STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX,
        STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
        STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX,
        STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX,
    )
    from services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )
except ModuleNotFoundError:
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessage,
        StoryWorkspaceDreamAgentActivityContent,
        StoryWorkspaceDreamAgentMessageAccepted,
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamAgentMessageSnapshot,
        StoryWorkspaceDreamAgentTextContent,
        StoryWorkspaceDreamAgentToolConfirmationAccepted,
        StoryWorkspaceDreamAgentToolConfirmationCommand,
        StoryWorkspaceDreamRunContext,
        STORY_WORKSPACE_DREAM_AGENT_ANSWER_TEXT_MAX,
        STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX,
        STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
        STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX,
        STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX,
    )
    from backend.services.story_workspace.dream_confirmation_service import (
        story_workspace_read_dream_confirmation_fact,
    )


STORY_WORKSPACE_DREAM_AGENT_USER_KIND = "story-workspace-dream-agent-user"
STORY_WORKSPACE_DREAM_AGENT_SOURCE_KEY = "story_workspace_dream_source"
STORY_WORKSPACE_DREAM_AGENT_SOURCE_KINDS = frozenset({
    "story-workspace-dream-launch",
    "story-workspace-dream-confirmation",
    STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
})
_CONFIRM_KIND = "story-workspace-dream-confirmation"
_ACTIVE = frozenset({"pending", "dispatching"})
_LEASE_SECONDS = 60
_LEASE_HEARTBEAT_SECONDS = 15
_TOOL_CALL_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,255}$")
_SAFE_TOOL_NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,120}$")
_SAFE_NETWORK_HOST = re.compile(
    r"^(?:[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?|[A-Fa-f0-9:]+)(?::[0-9]{1,5})?$"
)
_ASK_USER_TOOL_NAMES = frozenset({
    "askuserquestion",
    "ask_user_question",
    "ask_user",
    "askuser",
})
_TOOL_OUTPUT_TYPES = frozenset({
    "tool-output-available",
    "tool-output-error",
    "tool-error",
})
_ACTIVITY_LABELS = {
    "workspace_read": "读取工作区资料",
    "dream_write": "更新 Dream 内容",
    "reference_lookup": "查找参考资料",
    "delegation": "协同处理创作任务",
    "other": "处理 Dream 创作任务",
}
_WORKSPACE_READ_TOOLS = frozenset({
    "read", "glob", "grep", "ls", "list", "listdir", "notebookread", "todowrite",
})
_REFERENCE_LOOKUP_TOOLS = frozenset({"webfetch", "websearch", "search", "fetch"})
_DELEGATION_TOOLS = frozenset({"agent", "task"})
_DREAM_PUBLIC_TOOL_CONFIRMATIONS_ATTR = (
    "_story_workspace_dream_public_tool_confirmations"
)
_DREAM_PUBLIC_TOOL_CONFIRMATION_SUBSCRIBERS_ATTR = (
    "_story_workspace_dream_public_tool_confirmation_subscribers"
)
_DREAM_PUBLIC_TOOL_CONFIRMATIONS_MAX = 256
_ASK_USER_QUESTIONS_MAX = 8
_ASK_USER_OPTIONS_MAX = 12
_DREAM_PUBLIC_TEXT_REDACTION = "[已隐藏敏感内容]"
_DREAM_PUBLIC_TEXT_TRAILING_GUARD = 96
_DREAM_PUBLIC_TEXT_STREAM_MAX_PENDING = 16 * 1024
_DREAM_PUBLIC_TEXT_BOUNDARY = re.compile(r"[\s。！？；：，、,.!?;:]")
_SENSITIVE_ABSOLUTE_USER_PATH = re.compile(
    r"(?:"
    r"(?<![A-Za-z0-9])/(?:Users|home)/[^/\s]+(?:/[^\s]*)?|"
    r"(?<![A-Za-z0-9])[A-Za-z]:\\Users\\[^\\\s]+(?:\\[^\s]*)?"
    r")",
    re.IGNORECASE,
)
_SENSITIVE_ASK_USER_TEXT = re.compile(
    r"(?:"
    r"(?<![A-Za-z0-9])authorization(?:header|value|token)?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])bearer(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])credentials?(?:value)?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])tokens?(?:value)?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])(?:access|auth|refresh|secret)[\s_-]*tokens?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])api[\s_-]*keys?(?:value)?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])commands?(?:text|line)?(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])chain[\s_-]*(?:of[\s_-]*)?thought(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])hidden[\s_-]*reasoning(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])internal[\s_-]*reasoning(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])system[\s_-]*prompt(?![A-Za-z0-9])|"
    r"凭证|令牌|密钥|口令|命令|隐藏推理|内部推理|思维链|系统提示词"
    r")",
    re.IGNORECASE,
)
_SENSITIVE_INTERNAL_DREAM_DIAGNOSTIC = re.compile(
    r"(?:"
    r"(?<![A-Za-z0-9])(?:"
    r"agent_id|binding_revision|bind_first_episode|DREAM_WRITE_REJECTED"
    r")(?![A-Za-z0-9])|"
    r"(?<![A-Za-z0-9])mcp__story_workspace__"
    r")",
    re.IGNORECASE,
)
_HIGH_CONFIDENCE_ASK_USER_SECRETS = (
    re.compile(
        r"(?<![A-Za-z0-9_-])"
        r"eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}\."
        r"[A-Za-z0-9_-]{8,}"
        r"(?![A-Za-z0-9_-])"
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])"
        r"(?:sk-(?:(?:ant|proj)-)?|gh[pousr]_|xox[baprs]-)"
        r"[A-Za-z0-9_-]{16,}"
        r"(?![A-Za-z0-9_-])",
        re.IGNORECASE,
    ),
    re.compile(r"(?<![A-Za-z0-9_-])AIza[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_-])"),
    re.compile(r"(?<![A-Z0-9])AKIA[A-Z0-9]{16}(?![A-Z0-9])"),
    re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])rm\s+"
        r"(?:--recursive(?:\s+--force)?|-[A-Za-z]*r[A-Za-z]*)\s+\S+",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])(?:curl|wget)\b.{0,500}\|\s*"
        r"(?:(?:/usr)?/bin/)?(?:(?:ba|z|fi)?sh|python(?:3(?:\.\d+)?)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])cat\s+(?:"
        r"~?/\.ssh/\S+|/etc/(?:passwd|shadow)\b|"
        r"\S*(?:credential|secret|token|private[_-]?key)\S*"
        r")",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])python(?:3(?:\.\d+)?)?\s+(?:-c\b|<<)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])(?:ba|z|fi)?sh\s+-c\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])dd\b(?=[^\n]{0,240}\bif=\S+)"
        r"(?=[^\n]{0,240}\bof=\S+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])node\s+(?:-e|--eval)\b",
        re.IGNORECASE,
    ),
)
_LONG_HEX_SECRET = re.compile(
    r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{32,}(?![A-Fa-f0-9])"
)
_LONG_TOKEN_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9+/_=-])[A-Za-z0-9+/_-]{32,}={0,2}"
    r"(?![A-Za-z0-9+/_=-])"
)
_ASSIGNED_TOKEN_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9_.-])[A-Za-z_][A-Za-z0-9_.-]{0,40}\s*[:=]\s*"
    r"([A-Za-z0-9+/_-]{16,}={0,2})"
)
_PUBLIC_DREAM_RUN_ID = re.compile(r"run_[0-9a-f]{32}")


class StoryWorkspaceDreamAgentMessageError(RuntimeError):
    """An allowlisted HTTP-safe error at the Dream message boundary."""

    def __init__(self, code: str, status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _looks_like_high_entropy_secret(value: str) -> bool:
    def high_entropy(
        candidate: str,
        *,
        threshold: float,
        minimum_character_classes: int,
    ) -> bool:
        token = candidate.rstrip("=")
        if not token:
            return False
        counts = {character: token.count(character) for character in set(token)}
        entropy = -sum(
            (count / len(token)) * math.log2(count / len(token))
            for count in counts.values()
        )
        character_classes = sum((
            any(character.islower() for character in token),
            any(character.isupper() for character in token),
            any(character.isdigit() for character in token),
            any(character in "+/_-" for character in token),
        ))
        return (
            character_classes >= minimum_character_classes
            and entropy >= threshold
        )

    if any(
        high_entropy(
            match.group(0),
            threshold=3.0,
            minimum_character_classes=1,
        )
        for match in _LONG_HEX_SECRET.finditer(value)
        if value[max(0, match.start() - 4):match.start()].lower() != "run_"
    ):
        return True

    if any(
        high_entropy(
            match.group(1),
            threshold=3.0,
            minimum_character_classes=3,
        )
        for match in _ASSIGNED_TOKEN_CANDIDATE.finditer(value)
    ):
        return True
    return any(
        high_entropy(
            match.group(0),
            threshold=3.5,
            minimum_character_classes=3,
        )
        for match in _LONG_TOKEN_CANDIDATE.finditer(value)
        if _PUBLIC_DREAM_RUN_ID.fullmatch(match.group(0)) is None
    )


def story_workspace_guard_persisted_dream_agent_message_turn(
    db: sqlite3.Connection,
    *,
    thread_id: str,
    actor_id: str,
    message_id: str | None,
    metadata: Optional[dict],
) -> bool:
    """Keep a fresh widget claim from being overwritten by its queued runner.

    The client command has already been persisted under ``BEGIN IMMEDIATE``.
    A runner may begin later with a stale metadata copy, so the generic user
    persistence path must verify and preserve the database owner rather than
    replacing a renewed lease.
    """

    if not isinstance(message_id, str) or not message_id.startswith("dream_agent_"):
        return False
    row = db.execute(
        "SELECT message.thread_id, message.role, message.metadata, thread.user_id "
        "FROM chat_message AS message JOIN chat_thread AS thread "
        "ON thread.id = message.thread_id WHERE message.id = ?",
        (message_id,),
    ).fetchone()
    if row is None:
        return False
    stored = _decode(row["metadata"])
    if stored.get("kind") != STORY_WORKSPACE_DREAM_AGENT_USER_KIND:
        raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
    if not (
        row["thread_id"] == thread_id
        and row["role"] == "user"
        and str(row["user_id"]) == str(actor_id)
        and isinstance(metadata, dict)
        and metadata.get("kind") == STORY_WORKSPACE_DREAM_AGENT_USER_KIND
        and metadata.get("story_workspace_run_id")
        == stored.get("story_workspace_run_id")
        and metadata.get("command_fingerprint")
        == stored.get("command_fingerprint")
    ):
        raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
    return True


@dataclass(frozen=True)
class StoryWorkspaceDreamAgentPendingDispatch:
    thread_id: str
    actor_id: str
    context: StoryWorkspaceDreamRunContext
    message_id: str
    parts: list[dict[str, str]]
    metadata: dict[str, Any]


class StoryWorkspaceDreamAgentMessageCoordinator:
    """Coalesce durable pending-claim delivery attempts by message identity."""

    def __init__(
        self,
        dispatcher: Callable[[StoryWorkspaceDreamAgentPendingDispatch], Any],
    ) -> None:
        self._dispatcher = dispatcher
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def schedule(self, pending: StoryWorkspaceDreamAgentPendingDispatch) -> bool:
        existing = self._tasks.get(pending.message_id)
        if existing is not None and not existing.done():
            return False
        task = asyncio.create_task(
            self._dispatcher(pending),
            name=f"story-workspace-dream-agent-dispatch-{pending.message_id}",
        )
        self._tasks[pending.message_id] = task
        task.add_done_callback(
            lambda completed, message_id=pending.message_id: (
                self._tasks.pop(message_id, None)
                if self._tasks.get(message_id) is completed
                else None
            )
        )
        return True


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode(value: Any) -> dict[str, Any]:
    try:
        loaded = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _public_text_is_sensitive(value: str) -> bool:
    normalized = value.strip()
    return bool(
        _SENSITIVE_ASK_USER_TEXT.search(normalized)
        or _SENSITIVE_INTERNAL_DREAM_DIAGNOSTIC.search(normalized)
        or _SENSITIVE_ABSOLUTE_USER_PATH.search(normalized)
        or any(pattern.search(normalized) for pattern in _HIGH_CONFIDENCE_ASK_USER_SECRETS)
        or _looks_like_high_entropy_secret(normalized)
    )


def _public_text_projection(value: str) -> tuple[str, bool, bool]:
    """Apply one conservative public-text policy to snapshot and live output."""

    normalized = value.strip()
    if not normalized:
        return "", False, False
    if _public_text_is_sensitive(normalized):
        return _DREAM_PUBLIC_TEXT_REDACTION, False, True
    return (
        normalized[:STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX],
        len(normalized) > STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX,
        False,
    )


def _incremental_public_text_split(value: str) -> tuple[str, str]:
    """Release only a boundary-terminated prefix before the trailing guard."""

    safe_limit = len(value) - _DREAM_PUBLIC_TEXT_TRAILING_GUARD
    if safe_limit <= 0:
        return "", value
    boundary_end = 0
    for match in _DREAM_PUBLIC_TEXT_BOUNDARY.finditer(value, 0, safe_limit + 1):
        boundary_end = match.end()
    if boundary_end <= 0:
        return "", value
    return value[:boundary_end], value[boundary_end:]


def _parts_text(parts: Any) -> tuple[str, bool]:
    if not isinstance(parts, list):
        return "", False
    text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    )
    public_text, truncated, _redacted = _public_text_projection(text)
    return public_text, truncated


def _activity_category(tool_name: Any) -> str:
    """Map a private runtime tool name to one fixed public category."""

    if not isinstance(tool_name, str):
        return "other"
    leaf = tool_name.rsplit("__", 1)[-1].replace("_", "").lower()
    if leaf in {name.replace("_", "") for name in _WORKSPACE_READ_TOOLS}:
        return "workspace_read"
    if leaf in {"writedreamrun", "writedreamstage"}:
        return "dream_write"
    if leaf in {name.replace("_", "") for name in _REFERENCE_LOOKUP_TOOLS}:
        return "reference_lookup"
    if leaf in _DELEGATION_TOOLS:
        return "delegation"
    return "other"


def _activity_status(value: Any, *, is_error: bool = False) -> str:
    if is_error or value in {"output-error", "error", "stopped"}:
        return "stopped"
    if value in {"output-available", "completed"}:
        return "completed"
    return "running"


def _opaque_activity_id(*identity: str) -> str:
    digest = hashlib.sha256(_json(identity).encode("utf-8")).hexdigest()
    return f"dream_activity_{digest}"


def _activity_projection(
    *,
    activity_id: str,
    tool_name: Any,
    status: str,
) -> StoryWorkspaceDreamAgentActivityContent:
    category = _activity_category(tool_name)
    return StoryWorkspaceDreamAgentActivityContent(
        id=activity_id,
        category=category,
        label=_ACTIVITY_LABELS[category],
        status=status,
    )


def _persisted_activity_part(
    part: Any,
    *,
    message_id: str,
    part_index: int,
) -> StoryWorkspaceDreamAgentActivityContent | None:
    if not isinstance(part, dict) or part.get("type") not in {
        "tool-invocation", "dynamic-tool",
    }:
        return None
    tool_name = part.get("toolName")
    if not isinstance(tool_name, str):
        invocation = part.get("toolInvocation")
        tool_name = invocation.get("toolName") if isinstance(invocation, dict) else None
    return _activity_projection(
        activity_id=_opaque_activity_id("persisted", message_id, str(part_index)),
        tool_name=tool_name,
        status=_activity_status(part.get("state")),
    )


def _safe_content(
    parts: Any,
    *,
    message_id: str,
    include_activities: bool,
) -> list[StoryWorkspaceDreamAgentTextContent | StoryWorkspaceDreamAgentActivityContent]:
    """Project ordered public content without retaining any raw tool object."""

    if not isinstance(parts, list):
        return []
    joined_text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict)
        and part.get("type") == "text"
        and isinstance(part.get("text"), str)
    )
    _message_text, _message_truncated, text_is_redacted = _public_text_projection(
        joined_text
    )
    remaining_text = STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX
    redaction_emitted = False
    content: list[
        StoryWorkspaceDreamAgentTextContent | StoryWorkspaceDreamAgentActivityContent
    ] = []
    for index, part in enumerate(parts):
        if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
            if text_is_redacted:
                if not redaction_emitted:
                    content.append(StoryWorkspaceDreamAgentTextContent(
                        text=_DREAM_PUBLIC_TEXT_REDACTION,
                        truncated=False,
                    ))
                    redaction_emitted = True
                continue
            normalized = part["text"].strip()
            if not normalized or remaining_text <= 0:
                continue
            public_text = normalized[:remaining_text]
            content.append(StoryWorkspaceDreamAgentTextContent(
                text=public_text,
                truncated=len(normalized) > len(public_text),
            ))
            remaining_text -= len(public_text)
            continue
        if include_activities:
            activity = _persisted_activity_part(
                part,
                message_id=message_id,
                part_index=index,
            )
            if activity is not None:
                content.append(activity)
    return content


def _message_id(actor_id: str, run_id: str, key: str) -> str:
    digest = hashlib.sha256(_json({"actor": actor_id, "run": run_id, "key": key}).encode()).hexdigest()
    return f"dream_agent_{digest}"


def _fingerprint(actor_id: str, run_id: str, command: StoryWorkspaceDreamAgentMessageCommand) -> str:
    return "sha256:" + hashlib.sha256(
        _json({"actor": actor_id, "run": run_id, "text": command.text, "key": command.idempotency_key}).encode()
    ).hexdigest()


def _parse_sse(frame: str) -> tuple[str, dict[str, Any]] | None:
    event = "message"
    raw_data: list[str] = []
    for line in frame.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            raw_data.append(line[5:].strip())
    if not raw_data:
        return None
    try:
        data = json.loads("\n".join(raw_data))
    except ValueError:
        return None
    return (event, data) if isinstance(data, dict) else None


def _has_data_frame(frame: str) -> bool:
    """Whether an upstream SSE frame consumes one stable raw ordinal."""

    return any(line.startswith("data:") for line in frame.splitlines())


def _dream_public_cursor_position(
    cursor: str | None,
    *,
    turn_id: str,
) -> tuple[int, int]:
    """Decode `<turn>:<raw ordinal>[:<stable subevent>]` for replay."""

    if not cursor:
        return -1, -1
    parts = cursor.split(":")
    if len(parts) not in {2, 3} or parts[0] != turn_id:
        return -1, -1
    try:
        ordinal = int(parts[1])
        subevent = int(parts[2]) if len(parts) == 3 else 0
    except ValueError:
        return -1, -1
    if ordinal < 0 or subevent < 0:
        return -1, -1
    return ordinal, subevent


def _safe_public_text(value: Any, *, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    if not normalized:
        return None
    return normalized[:max_length]


def _strict_ask_user_public_text(value: Any, *, max_length: int) -> str | None:
    """Accept a bounded public field only when the complete value is safe."""

    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split()).strip()
    if (
        not normalized
        or len(normalized) > max_length
        or _SENSITIVE_ASK_USER_TEXT.search(normalized)
        or any(
            pattern.search(normalized)
            for pattern in _HIGH_CONFIDENCE_ASK_USER_SECRETS
        )
        or _looks_like_high_entropy_secret(normalized)
    ):
        return None
    return normalized


def _safe_tool_call_id(value: Any) -> str | None:
    return value if isinstance(value, str) and _TOOL_CALL_ID.fullmatch(value) else None


def _safe_tool_display_name(value: Any) -> str:
    if not isinstance(value, str) or not _SAFE_TOOL_NAME.fullmatch(value):
        return "Agent tool"
    candidate = value.rsplit("__", 1)[-1]
    display = candidate.replace("_", " ").strip()
    return display[:80] or "Agent tool"


def _is_ask_user_tool(tool_name: Any) -> bool:
    if not isinstance(tool_name, str):
        return False
    normalized = tool_name.lower()
    return (
        normalized in _ASK_USER_TOOL_NAMES
        or normalized.endswith("__ask_user")
        or normalized.endswith("__askuserquestion")
    )


def _safe_question_options(value: Any) -> list[dict[str, str]] | None:
    if not isinstance(value, list):
        return []
    if len(value) > _ASK_USER_OPTIONS_MAX:
        return None
    safe: list[dict[str, str]] = []
    for option in value:
        if isinstance(option, dict):
            raw_label = option.get("label")
            raw_value = option.get("value")
            for raw_field in (raw_label, raw_value):
                if isinstance(raw_field, str) and _strict_ask_user_public_text(
                    raw_field,
                    max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
                ) is None:
                    return None
            candidate = raw_label or raw_value
        else:
            candidate = option
        text = _strict_ask_user_public_text(
            candidate,
            max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_OPTION_MAX,
        )
        if text is None:
            return None
        projected = {"label": text, "value": text}
        if projected in safe:
            return None
        safe.append(projected)
    return safe


def _safe_ask_user_questions(tool_input: Any) -> list[dict[str, Any]] | None:
    if not isinstance(tool_input, dict):
        return None
    raw_questions = tool_input.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raw_questions = [{
            "question": (
                tool_input.get("question")
                or tool_input.get("message")
                or tool_input.get("text")
                or tool_input.get("prompt")
            ),
            "options": tool_input.get("options") or tool_input.get("choices"),
            "type": tool_input.get("type"),
            "required": tool_input.get("required"),
            "placeholder": tool_input.get("placeholder"),
            "multiSelect": tool_input.get("multiSelect"),
        }]
    if len(raw_questions) > _ASK_USER_QUESTIONS_MAX:
        return None
    safe: list[dict[str, Any]] = []
    seen_runner_answer_keys: set[str] = set()
    for index, question in enumerate(raw_questions):
        if not isinstance(question, dict):
            return None
        public_candidates = (
            question.get("question"),
            question.get("label"),
            question.get("header"),
        )
        for candidate in public_candidates:
            if isinstance(candidate, str) and _strict_ask_user_public_text(
                candidate,
                max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX,
            ) is None:
                return None
        text = _strict_ask_user_public_text(
            next((item for item in public_candidates if item), None),
            max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_TEXT_MAX,
        )
        if text is None:
            return None
        if text in seen_runner_answer_keys:
            return None
        seen_runner_answer_keys.add(text)
        # Raw model IDs are neither trusted nor public. Sequence-derived IDs
        # are stable across a full replay of the same pending AskUser input.
        question_id = f"q{index}"
        question_type = (
            question.get("type")
            if question.get("type") in {
                "text", "textarea", "select", "checkbox", "radio", "number",
            }
            else "radio" if question.get("options") else "text"
        )
        projected: dict[str, Any] = {
            "id": question_id,
            "question": text,
            "type": question_type,
            "required": (
                question.get("required")
                if isinstance(question.get("required"), bool)
                else True
            ),
        }
        raw_placeholder = question.get("placeholder")
        placeholder = (
            _strict_ask_user_public_text(
                raw_placeholder,
                max_length=STORY_WORKSPACE_DREAM_AGENT_QUESTION_PLACEHOLDER_MAX,
            )
            if raw_placeholder is not None
            else None
        )
        if raw_placeholder is not None and placeholder is None:
            return None
        if placeholder is not None:
            projected["placeholder"] = placeholder
        if isinstance(question.get("multiSelect"), bool):
            projected["multiSelect"] = question["multiSelect"]
        options = _safe_question_options(question.get("options"))
        if options is None:
            return None
        if options:
            projected["options"] = options
        if (
            question_type in {"select", "radio"}
            or projected.get("multiSelect") is True
        ) and not options:
            return None
        safe.append(projected)
    return safe or None


def story_workspace_project_dream_tool_confirmation(
    data: dict[str, Any],
) -> dict[str, Any] | None:
    """Project one raw approval frame without retaining raw tool input."""

    tool_call_id = _safe_tool_call_id(data.get("toolCallId"))
    if tool_call_id is None:
        return None
    tool_name = data.get("toolName")
    confirmation: dict[str, Any] = {
        "toolCallId": tool_call_id,
        "kind": "approval",
        "toolName": _safe_tool_display_name(tool_name),
    }
    if data.get("confirmationKind") == "sandbox_network":
        request = data.get("networkRequest")
        request = request if isinstance(request, dict) else {}
        raw_host = request.get("host")
        host = (
            raw_host[:253]
            if isinstance(raw_host, str)
            and len(raw_host) <= 253
            and _SAFE_NETWORK_HOST.fullmatch(raw_host)
            else None
        )
        raw_policy = request.get("policyMode")
        policy = raw_policy if raw_policy in {"allowlist", "open", "deny"} else "unknown"
        confirmation.update({
            "kind": "sandbox_network",
            "network": {"host": host, "policy": policy},
        })
    elif _is_ask_user_tool(tool_name):
        questions = _safe_ask_user_questions(data.get("input"))
        if questions is None:
            return None
        confirmation.update({
            "kind": "ask_user",
            "questions": questions,
        })
    return confirmation


def _dream_public_confirmation_key(
    *,
    thread_id: str,
    turn_id: str,
    run_id: str,
    actor_id: str,
    tool_call_id: str,
) -> tuple[str, str, str, str, str]:
    return (thread_id, turn_id, run_id, actor_id, tool_call_id)


def _dream_public_confirmation_registry(
    factory: Any,
    *,
    create: bool,
) -> dict[tuple[str, str, str, str, str], dict[str, Any]] | None:
    registry = getattr(factory, _DREAM_PUBLIC_TOOL_CONFIRMATIONS_ATTR, None)
    if isinstance(registry, dict):
        return registry
    if not create:
        return None
    registry = {}
    try:
        setattr(factory, _DREAM_PUBLIC_TOOL_CONFIRMATIONS_ATTR, registry)
    except (AttributeError, TypeError):
        return None
    return registry


def _remember_dream_public_confirmation(
    factory: Any,
    *,
    thread_id: str,
    turn_id: str,
    run_id: str,
    actor_id: str,
    confirmation: dict[str, Any],
) -> bool:
    registry = _dream_public_confirmation_registry(factory, create=True)
    if registry is None:
        return False
    confirmation_key = _dream_public_confirmation_key(
        thread_id=thread_id,
        turn_id=turn_id,
        run_id=run_id,
        actor_id=actor_id,
        tool_call_id=confirmation["toolCallId"],
    )
    if (
        confirmation_key not in registry
        and len(registry) >= _DREAM_PUBLIC_TOOL_CONFIRMATIONS_MAX
    ):
        return False
    registry[confirmation_key] = confirmation
    return True


def _forget_dream_public_confirmation(
    factory: Any,
    *,
    thread_id: str,
    turn_id: str,
    run_id: str,
    actor_id: str,
    tool_call_id: str,
) -> None:
    registry = _dream_public_confirmation_registry(factory, create=False)
    if registry is not None:
        registry.pop(_dream_public_confirmation_key(
            thread_id=thread_id,
            turn_id=turn_id,
            run_id=run_id,
            actor_id=actor_id,
            tool_call_id=tool_call_id,
        ), None)


def _forget_dream_public_confirmations_for_turn(
    factory: Any,
    *,
    thread_id: str,
    turn_id: str,
    run_id: str,
    actor_id: str,
) -> None:
    registry = _dream_public_confirmation_registry(factory, create=False)
    if registry is None:
        return
    turn_prefix = (thread_id, turn_id, run_id, actor_id)
    for confirmation_key in tuple(registry):
        if confirmation_key[:4] == turn_prefix:
            registry.pop(confirmation_key, None)


def _dream_public_confirmation_subscribers(
    factory: Any,
    *,
    create: bool,
) -> dict[tuple[str, str, str, str], int] | None:
    subscribers = getattr(
        factory,
        _DREAM_PUBLIC_TOOL_CONFIRMATION_SUBSCRIBERS_ATTR,
        None,
    )
    if isinstance(subscribers, dict):
        return subscribers
    if not create:
        return None
    subscribers = {}
    try:
        setattr(
            factory,
            _DREAM_PUBLIC_TOOL_CONFIRMATION_SUBSCRIBERS_ATTR,
            subscribers,
        )
    except (AttributeError, TypeError):
        return None
    return subscribers


def _retain_dream_public_confirmation_turn(
    factory: Any,
    *,
    thread_id: str,
    turn_id: str,
    run_id: str,
    actor_id: str,
) -> bool:
    subscribers = _dream_public_confirmation_subscribers(factory, create=True)
    if subscribers is None:
        return False
    turn_key = (thread_id, turn_id, run_id, actor_id)
    subscribers[turn_key] = subscribers.get(turn_key, 0) + 1
    return True


def _release_dream_public_confirmation_turn(
    factory: Any,
    *,
    thread_id: str,
    turn_id: str,
    run_id: str,
    actor_id: str,
    terminal: bool,
) -> None:
    subscribers = _dream_public_confirmation_subscribers(factory, create=False)
    turn_key = (thread_id, turn_id, run_id, actor_id)
    remaining = subscribers.get(turn_key, 0) if subscribers is not None else 0
    if terminal or remaining <= 1:
        if subscribers is not None:
            subscribers.pop(turn_key, None)
        _forget_dream_public_confirmations_for_turn(
            factory,
            thread_id=thread_id,
            turn_id=turn_id,
            run_id=run_id,
            actor_id=actor_id,
        )
        return
    subscribers[turn_key] = remaining - 1


def _validate_dream_public_confirmation_answers(
    *,
    command: StoryWorkspaceDreamAgentToolConfirmationCommand,
    confirmation: dict[str, Any],
) -> dict[str, Any] | None:
    """Validate only against the public projection shown for this pending tool."""

    answers = command.answers
    if not command.approved:
        if answers:
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                422,
            )
        return None
    if confirmation.get("kind") != "ask_user":
        if answers:
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                422,
            )
        return None
    questions = confirmation.get("questions")
    if not isinstance(questions, list) or not questions:
        raise StoryWorkspaceDreamAgentMessageError(
            "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
            409,
        )
    answer_map = answers or {}
    questions_by_id = {
        question["id"]: question
        for question in questions
        if isinstance(question, dict) and isinstance(question.get("id"), str)
    }
    if len(questions_by_id) != len(questions) or not set(answer_map).issubset(
        questions_by_id
    ):
        raise StoryWorkspaceDreamAgentMessageError(
            "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
            422,
        )
    runner_answers: dict[str, Any] = {}
    for question_id, question in questions_by_id.items():
        present = question_id in answer_map
        if question.get("required") is True and not present:
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                422,
            )
        if not present:
            continue
        answer = answer_map[question_id]
        options = question.get("options")
        allowed_values = {
            option["value"]
            for option in options or []
            if isinstance(option, dict) and isinstance(option.get("value"), str)
        }
        if question.get("multiSelect") is True:
            if (
                not isinstance(answer, list)
                or not answer
                or len(answer) != len(set(answer))
                or any(value not in allowed_values for value in answer)
            ):
                raise StoryWorkspaceDreamAgentMessageError(
                    "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                    422,
                )
        elif allowed_values:
            if not isinstance(answer, str) or answer not in allowed_values:
                raise StoryWorkspaceDreamAgentMessageError(
                    "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                    422,
                )
        elif question.get("type") == "checkbox":
            if not isinstance(answer, bool):
                raise StoryWorkspaceDreamAgentMessageError(
                    "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                    422,
                )
        elif question.get("type") == "number":
            if isinstance(answer, bool) or not isinstance(answer, int):
                raise StoryWorkspaceDreamAgentMessageError(
                    "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                    422,
                )
        elif (
            not isinstance(answer, str)
            or len(answer) > STORY_WORKSPACE_DREAM_AGENT_ANSWER_TEXT_MAX
            or (question.get("required") is True and not answer.strip())
        ):
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_INVALID",
                422,
            )
        question_text = question.get("question")
        if not isinstance(question_text, str) or question_text in runner_answers:
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
                409,
            )
        runner_answers[question_text] = answer
    return runner_answers


class StoryWorkspaceDreamAgentMessageService:
    """Owns safe projections while callers retain run authorization/context."""

    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        thread_factory: Any | None = None,
        db_factory: Callable[[], sqlite3.Connection] | None = None,
    ) -> None:
        self._db = db
        self._thread_factory = thread_factory
        self._db_factory = db_factory

    def snapshot(
        self, *, run_id: str, thread_id: str, actor_id: str
    ) -> StoryWorkspaceDreamAgentMessageSnapshot:
        confirmation_accepted, confirmation_dispatched = story_workspace_read_dream_confirmation_fact(
            self._db, actor_id=actor_id, thread_id=thread_id, run_id=run_id
        )
        session = self._thread_factory.session_snapshot(thread_id) if self._thread_factory else None
        running = bool(session and session.get("lifecycle") == "running")
        active_turn_id = str(session.get("current_turn_id")) if running and session.get("current_turn_id") else None
        has_active_claim = self._has_active_claim(
            run_id=run_id,
            thread_id=thread_id,
            actor_id=actor_id,
        )
        if has_active_claim:
            reason: str | None = "busy"
        elif running:
            reason: str | None = "busy" if confirmation_dispatched else (
                "continuing" if confirmation_accepted else "generating"
            )
        elif not confirmation_accepted:
            reason = "waiting_confirmation"
        elif not confirmation_dispatched:
            reason = "continuing"
        else:
            reason = None
        return StoryWorkspaceDreamAgentMessageSnapshot(
            story_workspace_run_id=run_id,
            lifecycle="streaming" if running else "idle",
            active_turn_id=active_turn_id,
            can_send=reason is None,
            send_block_reason=reason,
            messages=self._safe_messages(
                run_id=run_id, thread_id=thread_id, actor_id=actor_id
            ),
            snapshot_at=datetime.now(UTC),
        )

    def _safe_messages(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
    ) -> list[StoryWorkspaceDreamAgentMessage]:
        rows = self._db.execute(
            "SELECT id, thread_id, role, parts, metadata, created_at FROM chat_message "
            "WHERE thread_id = ? ORDER BY created_at ASC, id ASC", (thread_id,)
        ).fetchall()
        source_rows = {
            str(row["id"]): row
            for row in rows
            if row["role"] == "user"
        }
        safe: list[StoryWorkspaceDreamAgentMessage] = []
        for row in rows:
            metadata = _decode(row["metadata"])
            kind = metadata.get("kind")
            # Only explicit widget user messages are public.  Assistant text is
            # public only after the run source and never when tied to a control turn.
            if row["role"] == "user":
                if (
                    kind != STORY_WORKSPACE_DREAM_AGENT_USER_KIND
                    or metadata.get("story_workspace_run_id") != run_id
                    or str(metadata.get("actor_id") or "") != actor_id
                ):
                    continue
            elif row["role"] == "assistant":
                if not self._assistant_has_authorized_source(
                    metadata,
                    source_rows=source_rows,
                    run_id=run_id,
                    thread_id=thread_id,
                    actor_id=actor_id,
                ):
                    continue
            else:
                continue
            try:
                parts = json.loads(row["parts"]) if row["parts"] else []
            except (TypeError, ValueError):
                continue
            text, truncated = _parts_text(parts)
            if not text:
                continue
            created = row["created_at"]
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    continue
            if not isinstance(created, datetime):
                continue
            safe.append(StoryWorkspaceDreamAgentMessage(
                id=str(row["id"]),
                role=row["role"],
                text=text,
                truncated=truncated,
                content=_safe_content(
                    parts,
                    message_id=str(row["id"]),
                    include_activities=row["role"] == "assistant",
                ),
                created_at=created,
            ))
        return safe

    def _has_active_claim(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
    ) -> bool:
        """A durable pending/leased command blocks a second visible send."""

        rows = self._db.execute(
            "SELECT metadata FROM chat_message WHERE thread_id = ? AND role = 'user'",
            (thread_id,),
        ).fetchall()
        for row in rows:
            metadata = _decode(row["metadata"])
            if (
                metadata.get("kind") == STORY_WORKSPACE_DREAM_AGENT_USER_KIND
                and metadata.get("story_workspace_run_id") == run_id
                and str(metadata.get("actor_id") or "") == actor_id
                and metadata.get("dispatch_status") in _ACTIVE
            ):
                return True
        return False

    @staticmethod
    def _assistant_has_authorized_source(
        metadata: dict[str, Any],
        *,
        source_rows: dict[str, Any],
        run_id: str,
        thread_id: str,
        actor_id: str,
    ) -> bool:
        """Prove an assistant reply descends from a permitted Dream user turn."""

        source = metadata.get(STORY_WORKSPACE_DREAM_AGENT_SOURCE_KEY)
        if not isinstance(source, dict):
            return False
        source_id = source.get("message_id")
        source_kind = source.get("kind")
        if not (
            isinstance(source_id, str)
            and source_kind in STORY_WORKSPACE_DREAM_AGENT_SOURCE_KINDS
            and source.get("run_id") == run_id
            and source.get("thread_id") == thread_id
            and str(source.get("actor_id") or "") == actor_id
        ):
            return False
        row = source_rows.get(source_id)
        if row is None or row["thread_id"] != thread_id:
            return False
        source_metadata = _decode(row["metadata"])
        if source_metadata.get("kind") != source_kind:
            return False
        if source_kind == "story-workspace-dream-launch":
            return (
                source_metadata.get("workflowRunId") == run_id
                and source_metadata.get("threadId") == thread_id
                and str(source_metadata.get("actorId") or "") == actor_id
            )
        return (
            source_metadata.get("story_workspace_run_id") == run_id
            and str(source_metadata.get("thread_id") or "") == thread_id
            and str(source_metadata.get("actor_id") or source_metadata.get("actor") or "")
            == actor_id
        )

    async def events(
        self,
        *,
        thread_id: str,
        run_id: str,
        actor_id: str,
        after: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Normalize public text and safe tool lifecycle; raw frames never escape."""
        if self._thread_factory is None:
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"
            return
        snapshot = self._thread_factory.session_snapshot(thread_id)
        if not snapshot or snapshot.get("lifecycle") != "running":
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"
            return
        turn_id = str(snapshot.get("current_turn_id") or "")
        turn_matcher = getattr(
            self._thread_factory,
            "is_expected_story_workspace_dream_turn",
            None,
        )
        if not callable(turn_matcher) or not turn_matcher(
            thread_id, turn_id, run_id, actor_id
        ):
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"
            return
        after_position = _dream_public_cursor_position(after, turn_id=turn_id)

        def cursor_consumed(raw_ordinal: int, subevent: int = 0) -> bool:
            return (raw_ordinal, subevent) <= after_position

        ordinal = -1
        pending_tool_call_ids: set[str] = set()
        activity_tool_names: dict[str, str] = {}
        started_activity_ids: set[str] = set()
        public_text_pending = ""
        public_text_redacted = False
        public_text_redaction_emitted = False
        public_text_emitted_chars = 0
        if not _retain_dream_public_confirmation_turn(
            self._thread_factory,
            thread_id=thread_id,
            turn_id=turn_id,
            run_id=run_id,
            actor_id=actor_id,
        ):
            yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"
            return
        terminal = False
        try:
            yield f"event: status\ndata: {_json({'lifecycle': 'streaming'})}\n\n"
            # A comment is transport-only: it cannot alter raw-frame ordinals and
            # proves intermediary/proxy connections remain alive without leaking a
            # generic Claude Agent frame.
            yield ": keepalive\n\n"
            subscribe_expected = getattr(
                self._thread_factory,
                "subscribe_expected_stream",
                None,
            )
            stream = (
                subscribe_expected(thread_id, turn_id)
                if callable(subscribe_expected)
                else self._thread_factory.subscribe_stream(thread_id)
            )
            async for frame in stream:
                if isinstance(frame, str) and frame.lstrip().startswith(":"):
                    yield ": keepalive\n\n"
                    continue
                if not isinstance(frame, str) or not _has_data_frame(frame):
                    continue
                ordinal += 1
                parsed = _parse_sse(frame)
                if parsed is None:
                    continue
                _event, data = parsed
                frame_type = data.get("type")
                if frame_type == "finish":
                    terminal = True
                    break
                if frame_type in {"tool-input-start", "tool-input-available"}:
                    tool_call_id = _safe_tool_call_id(data.get("toolCallId"))
                    tool_name = data.get("toolName")
                    if tool_call_id is None or not isinstance(tool_name, str):
                        continue
                    activity_tool_names[tool_call_id] = tool_name
                    activity_id = _opaque_activity_id(
                        "live", run_id, thread_id, turn_id, tool_call_id
                    )
                    if activity_id in started_activity_ids:
                        continue
                    started_activity_ids.add(activity_id)
                    if cursor_consumed(ordinal):
                        continue
                    activity = _activity_projection(
                        activity_id=activity_id,
                        tool_name=tool_name,
                        status="running",
                    ).model_dump(mode="json", by_alias=True)
                    payload = {"turnId": turn_id, "activity": activity}
                    yield (
                        f"id: {turn_id}:{ordinal}\n"
                        f"event: agent_activity_started\n"
                        f"data: {_json(payload)}\n\n"
                    )
                    continue
                if frame_type == "tool-approval-request":
                    confirmation = story_workspace_project_dream_tool_confirmation(data)
                    if confirmation is None:
                        continue
                    tool_call_id = confirmation["toolCallId"]
                    if not _remember_dream_public_confirmation(
                        self._thread_factory,
                        thread_id=thread_id,
                        turn_id=turn_id,
                        run_id=run_id,
                        actor_id=actor_id,
                        confirmation=confirmation,
                    ):
                        continue
                    pending_tool_call_ids.add(tool_call_id)
                    if cursor_consumed(ordinal):
                        continue
                    payload = {"turnId": turn_id, "confirmation": confirmation}
                    yield (
                        f"id: {turn_id}:{ordinal}\n"
                        f"event: tool_confirmation_requested\n"
                        f"data: {_json(payload)}\n\n"
                    )
                    continue
                if frame_type in _TOOL_OUTPUT_TYPES:
                    tool_call_id = _safe_tool_call_id(data.get("toolCallId"))
                    if tool_call_id is None:
                        continue
                    was_pending_confirmation = tool_call_id in pending_tool_call_ids
                    if was_pending_confirmation:
                        pending_tool_call_ids.discard(tool_call_id)
                        _forget_dream_public_confirmation(
                            self._thread_factory,
                            thread_id=thread_id,
                            turn_id=turn_id,
                            run_id=run_id,
                            actor_id=actor_id,
                            tool_call_id=tool_call_id,
                        )
                    tool_name = activity_tool_names.get(tool_call_id)
                    activity_id = _opaque_activity_id(
                        "live", run_id, thread_id, turn_id, tool_call_id
                    )
                    has_public_activity = (
                        tool_name is not None and activity_id in started_activity_ids
                    )
                    activity = (
                        _activity_projection(
                            activity_id=activity_id,
                            tool_name=tool_name,
                            status=_activity_status(
                                "output-available" if frame_type == "tool-output-available" else "output-error",
                                is_error=(
                                    frame_type != "tool-output-available"
                                    or data.get("isError") is True
                                ),
                            ),
                        ).model_dump(mode="json", by_alias=True)
                        if has_public_activity
                        else None
                    )
                    if was_pending_confirmation:
                        if not cursor_consumed(ordinal, 0):
                            payload = {"turnId": turn_id, "toolCallId": tool_call_id}
                            yield (
                                f"id: {turn_id}:{ordinal}:0\n"
                                f"event: tool_confirmation_resolved\n"
                                f"data: {_json(payload)}\n\n"
                            )
                        if activity is not None and not cursor_consumed(ordinal, 1):
                            payload = {"turnId": turn_id, "activity": activity}
                            yield (
                                f"id: {turn_id}:{ordinal}:1\n"
                                f"event: agent_activity_finished\n"
                                f"data: {_json(payload)}\n\n"
                            )
                        continue
                    if activity is not None and not cursor_consumed(ordinal):
                        payload = {"turnId": turn_id, "activity": activity}
                        yield (
                            f"id: {turn_id}:{ordinal}\n"
                            f"event: agent_activity_finished\n"
                            f"data: {_json(payload)}\n\n"
                        )
                    continue
                if frame_type == "message-final":
                    terminal = True
                    payload = {"turnId": turn_id}
                    final_text = ""
                    if not public_text_redacted:
                        public_text, _truncated, text_is_redacted = (
                            _public_text_projection(public_text_pending)
                        )
                        if text_is_redacted:
                            public_text_redacted = True
                            public_text_pending = ""
                            if not public_text_redaction_emitted:
                                final_text = _DREAM_PUBLIC_TEXT_REDACTION
                                public_text_redaction_emitted = True
                        else:
                            remaining = max(
                                0,
                                STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX
                                - public_text_emitted_chars,
                            )
                            final_text = public_text[:remaining]
                            public_text_emitted_chars += len(final_text)
                            public_text_pending = ""
                    if final_text:
                        if not cursor_consumed(ordinal, 0):
                            text_payload = {"turnId": turn_id, "delta": final_text}
                            yield (
                                f"id: {turn_id}:{ordinal}:0\n"
                                f"event: assistant_text_delta\n"
                                f"data: {_json(text_payload)}\n\n"
                            )
                        if not cursor_consumed(ordinal, 1):
                            yield (
                                f"id: {turn_id}:{ordinal}:1\n"
                                f"event: assistant_message_committed\n"
                                f"data: {_json(payload)}\n\n"
                            )
                    elif not cursor_consumed(ordinal):
                        yield f"id: {turn_id}:{ordinal}\nevent: assistant_message_committed\ndata: {_json(payload)}\n\n"
                    break
                if frame_type == "text-delta" and isinstance(data.get("delta"), str):
                    if public_text_redacted:
                        continue
                    public_text_pending += data["delta"]
                    text_is_sensitive = (
                        len(public_text_pending)
                        > _DREAM_PUBLIC_TEXT_STREAM_MAX_PENDING
                        or _public_text_is_sensitive(public_text_pending)
                    )
                    if text_is_sensitive:
                        public_text_redacted = True
                        public_text_pending = ""
                        if not public_text_redaction_emitted:
                            public_text_redaction_emitted = True
                            if not cursor_consumed(ordinal):
                                text_payload = {
                                    "turnId": turn_id,
                                    "delta": _DREAM_PUBLIC_TEXT_REDACTION,
                                }
                                yield (
                                    f"id: {turn_id}:{ordinal}\n"
                                    f"event: assistant_text_delta\n"
                                    f"data: {_json(text_payload)}\n\n"
                                )
                        continue
                    public_prefix, public_text_pending = (
                        _incremental_public_text_split(public_text_pending)
                    )
                    remaining = max(
                        0,
                        STORY_WORKSPACE_DREAM_AGENT_MESSAGE_TEXT_MAX
                        - public_text_emitted_chars,
                    )
                    public_prefix = public_prefix[:remaining]
                    public_text_emitted_chars += len(public_prefix)
                    if public_prefix and not cursor_consumed(ordinal):
                        text_payload = {
                            "turnId": turn_id,
                            "delta": public_prefix,
                        }
                        yield (
                            f"id: {turn_id}:{ordinal}\n"
                            f"event: assistant_text_delta\n"
                            f"data: {_json(text_payload)}\n\n"
                        )
        finally:
            _release_dream_public_confirmation_turn(
                self._thread_factory,
                thread_id=thread_id,
                turn_id=turn_id,
                run_id=run_id,
                actor_id=actor_id,
                terminal=terminal,
            )
        yield "event: status\ndata: {\"lifecycle\":\"idle\"}\n\n"

    def confirm_tool(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
        command: StoryWorkspaceDreamAgentToolConfirmationCommand,
    ) -> StoryWorkspaceDreamAgentToolConfirmationAccepted:
        """Resolve one tool only while the run's trusted Dream turn is active."""

        factory = self._thread_factory
        if factory is None:
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
                409,
            )
        snapshot = factory.session_snapshot(thread_id)
        turn_id = (
            str(snapshot.get("current_turn_id") or "")
            if isinstance(snapshot, dict)
            and snapshot.get("lifecycle") == "running"
            else ""
        )
        matcher = getattr(
            factory,
            "is_expected_story_workspace_dream_turn",
            None,
        )
        if (
            not turn_id
            or not callable(matcher)
            or not matcher(thread_id, turn_id, run_id, actor_id)
        ):
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
                409,
            )
        registry = _dream_public_confirmation_registry(factory, create=False)
        confirmation_key = _dream_public_confirmation_key(
            thread_id=thread_id,
            turn_id=turn_id,
            run_id=run_id,
            actor_id=actor_id,
            tool_call_id=command.tool_call_id,
        )
        confirmation = registry.get(confirmation_key) if registry is not None else None
        if not isinstance(confirmation, dict):
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
                409,
            )
        answers = _validate_dream_public_confirmation_answers(
            command=command,
            confirmation=confirmation,
        )
        resolved = factory.confirm_tool(
            session_id=thread_id,
            tool_call_id=command.tool_call_id,
            approved=command.approved,
            reason=command.reason,
            answers=answers,
        )
        if not resolved:
            raise StoryWorkspaceDreamAgentMessageError(
                "DREAM_AGENT_TOOL_CONFIRMATION_NOT_READY",
                409,
            )
        registry.pop(confirmation_key, None)
        return StoryWorkspaceDreamAgentToolConfirmationAccepted(
            story_workspace_run_id=run_id,
            tool_call_id=command.tool_call_id,
            approved=command.approved,
        )

    def claim_message(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
        context: StoryWorkspaceDreamRunContext,
        command: StoryWorkspaceDreamAgentMessageCommand,
    ) -> tuple[StoryWorkspaceDreamAgentMessageAccepted, StoryWorkspaceDreamAgentPendingDispatch | None]:
        """Atomically persist/replay one command and prevent a second live turn."""
        if (
            context.workflow_run_id != run_id
            or context.thread_id != thread_id
            or not isinstance(actor_id, str)
            or not actor_id
        ):
            raise StoryWorkspaceDreamAgentMessageError("WORKFLOW_PERMISSION_DENIED", 403)
        accepted, dispatched = story_workspace_read_dream_confirmation_fact(
            self._db, actor_id=actor_id, thread_id=thread_id, run_id=run_id
        )
        running = bool(self._thread_factory and (self._thread_factory.session_snapshot(thread_id) or {}).get("lifecycle") == "running")
        if not accepted or not dispatched or running:
            raise StoryWorkspaceDreamAgentMessageError("DREAM_AGENT_MESSAGE_NOT_READY", 409)
        message_id = _message_id(actor_id, run_id, command.idempotency_key)
        fingerprint = _fingerprint(actor_id, run_id, command)
        now = time.time()
        try:
            self._db.execute("BEGIN IMMEDIATE")
            existing = self._db.execute("SELECT metadata FROM chat_message WHERE id = ?", (message_id,)).fetchone()
            if existing is not None:
                metadata = _decode(existing["metadata"])
                if metadata.get("command_fingerprint") != fingerprint:
                    raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
                if metadata.get("kind") != STORY_WORKSPACE_DREAM_AGENT_USER_KIND:
                    raise StoryWorkspaceDreamAgentMessageError("IDEMPOTENCY_CONFLICT", 409)
                status = metadata.get("dispatch_status")
                lease_until = metadata.get("dispatch_claim_lease_until", 0)
                lease_expired = (
                    not isinstance(lease_until, (int, float))
                    or isinstance(lease_until, bool)
                    or not math.isfinite(float(lease_until))
                    or float(lease_until) <= now
                )
                if status in _ACTIVE and lease_expired:
                    previous_metadata = existing["metadata"]
                    metadata["dispatch_status"] = "dispatching"
                    metadata["dispatch_claim_id"] = str(uuid4())
                    metadata["dispatch_claim_lease_until"] = now + _LEASE_SECONDS
                    handoff = self._db.execute(
                        "UPDATE chat_message SET metadata = ? WHERE id = ? AND metadata = ?",
                        (_json(metadata), message_id, previous_metadata),
                    )
                    if handoff.rowcount != 1:
                        raise StoryWorkspaceDreamAgentMessageError("DREAM_AGENT_MESSAGE_BUSY", 409)
                    self._db.commit()
                    pending = StoryWorkspaceDreamAgentPendingDispatch(
                        thread_id, actor_id, context, message_id,
                        [{"type": "text", "text": command.text.strip()}], metadata,
                    )
                    return StoryWorkspaceDreamAgentMessageAccepted(
                        story_workspace_run_id=run_id, message_id=message_id
                    ), pending
                self._db.commit()
                return StoryWorkspaceDreamAgentMessageAccepted(story_workspace_run_id=run_id, message_id=message_id), None
            rows = self._db.execute("SELECT metadata FROM chat_message WHERE thread_id = ? AND role = 'user'", (thread_id,)).fetchall()
            for row in rows:
                metadata = _decode(row["metadata"])
                if (
                    metadata.get("kind") == STORY_WORKSPACE_DREAM_AGENT_USER_KIND
                    and metadata.get("story_workspace_run_id") == run_id
                    and str(metadata.get("actor_id") or "") == actor_id
                    and metadata.get("dispatch_status") in _ACTIVE
                ):
                    raise StoryWorkspaceDreamAgentMessageError("DREAM_AGENT_MESSAGE_BUSY", 409)
            metadata = {
                "kind": STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
                "story_workspace_run_id": run_id,
                "actor_id": actor_id,
                "thread_id": thread_id,
                "idempotency_key": command.idempotency_key,
                "command_fingerprint": fingerprint,
                "dispatch_status": "dispatching",
                "dispatch_claim_id": str(uuid4()),
                "dispatch_claim_lease_until": now + _LEASE_SECONDS,
            }
            parts = [{"type": "text", "text": command.text.strip()}]
            self._db.execute(
                "INSERT INTO chat_message (id, thread_id, role, parts, metadata) VALUES (?, ?, 'user', ?, ?)",
                (message_id, thread_id, _json(parts), _json(metadata)),
            )
            self._db.execute("UPDATE chat_thread SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (thread_id,))
            self._db.commit()
        except StoryWorkspaceDreamAgentMessageError:
            if self._db.in_transaction:
                self._db.rollback()
            raise
        except sqlite3.Error as exc:
            if self._db.in_transaction:
                self._db.rollback()
            raise StoryWorkspaceDreamAgentMessageError("DECK_RUNTIME_CONFIG_UNAVAILABLE", 503) from exc
        pending = StoryWorkspaceDreamAgentPendingDispatch(thread_id, actor_id, context, message_id, parts, metadata)
        return StoryWorkspaceDreamAgentMessageAccepted(story_workspace_run_id=run_id, message_id=message_id), pending

    async def dispatch(self, pending: StoryWorkspaceDreamAgentPendingDispatch) -> bool:
        """Run the already claimed source message on the authoritative thread."""
        if self._thread_factory is None:
            self._release_claim(pending.message_id, pending.metadata["dispatch_claim_id"])
            return False
        heartbeat = asyncio.create_task(
            self._heartbeat_claim(
                pending.message_id,
                pending.metadata["dispatch_claim_id"],
            ),
            name=f"story-workspace-dream-agent-lease-{pending.message_id}",
        )
        try:
            try:
                from claude_agent.service import ClaudeAgentRunRequest
            except ModuleNotFoundError:
                from backend.claude_agent.service import ClaudeAgentRunRequest
            request = ClaudeAgentRunRequest(
                user_id=pending.actor_id, thread_id=pending.thread_id, resume=True,
                message_id=pending.message_id, message_parts=pending.parts,
                message_metadata=pending.metadata, story_workspace_dream_context=pending.context,
            )
            saw_final = False
            finished = False
            async for frame in self._thread_factory.run_streaming(request):
                parsed = _parse_sse(frame) if isinstance(frame, str) else None
                if parsed is None:
                    continue
                _event, event = parsed
                if event.get("type") == "error":
                    break
                if event.get("type") == "message-final":
                    saw_final = True
                if event.get("type") == "finish":
                    finished = event.get("finishReason") != "error"
                    break
            if not (saw_final and finished):
                self._release_claim(pending.message_id, pending.metadata["dispatch_claim_id"])
                return False
            self._mark_dispatched(pending.message_id, pending.metadata["dispatch_claim_id"])
            return True
        except Exception:
            self._release_claim(pending.message_id, pending.metadata["dispatch_claim_id"])
            return False
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat

    async def _heartbeat_claim(self, message_id: str, claim_id: str) -> None:
        """Renew a live dispatch lease; database writes always use a fresh DB."""

        while True:
            await asyncio.sleep(_LEASE_HEARTBEAT_SECONDS)
            renewed = await asyncio.to_thread(self._renew_claim, message_id, claim_id)
            if not renewed:
                return

    def _renew_claim(self, message_id: str, claim_id: str) -> bool:
        db = self._db_factory() if self._db_factory is not None else self._db
        close_after = db is not self._db
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT metadata FROM chat_message WHERE id = ?",
                (message_id,),
            ).fetchone()
            previous_metadata = row["metadata"] if row else None
            metadata = _decode(previous_metadata) if previous_metadata else {}
            if (
                metadata.get("dispatch_claim_id") != claim_id
                or metadata.get("dispatch_status") != "dispatching"
            ):
                db.rollback()
                return False
            metadata["dispatch_claim_lease_until"] = time.time() + _LEASE_SECONDS
            renewed = db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ? AND metadata = ?",
                (_json(metadata), message_id, previous_metadata),
            )
            if renewed.rowcount != 1:
                db.rollback()
                return False
            db.commit()
            return True
        except sqlite3.Error:
            if db.in_transaction:
                db.rollback()
            return False
        finally:
            if close_after:
                db.close()

    def _mark_dispatched(self, message_id: str, claim_id: str) -> bool:
        return self._update_claim(message_id, claim_id, dispatched=True)

    def _release_claim(self, message_id: str, claim_id: str) -> bool:
        return self._update_claim(message_id, claim_id, dispatched=False)

    def _update_claim(self, message_id: str, claim_id: str, *, dispatched: bool) -> bool:
        db = self._db_factory() if self._db_factory is not None else self._db
        close_after = db is not self._db
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT metadata FROM chat_message WHERE id = ?", (message_id,)).fetchone()
            previous_metadata = row["metadata"] if row else None
            metadata = _decode(previous_metadata) if previous_metadata else {}
            if (
                metadata.get("dispatch_claim_id") != claim_id
                or metadata.get("dispatch_status") != "dispatching"
            ):
                db.rollback()
                return False
            metadata["dispatch_status"] = "dispatched" if dispatched else "pending"
            metadata["dispatch_claim_lease_until"] = 0
            updated = db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ? AND metadata = ?",
                (_json(metadata), message_id, previous_metadata),
            )
            if updated.rowcount != 1:
                db.rollback()
                return False
            db.commit()
            return True
        except sqlite3.Error:
            if db.in_transaction:
                db.rollback()
            return False
        finally:
            if close_after:
                db.close()
