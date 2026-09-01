# [Input] Structured DreamArtifactValidationIssue, canonical chat_message persistence, and server-owned Dream Turn identity.
# [Output] One stable visible auto-repair user message plus bounded dispatch-status settlement helpers.
# [Pos] Dream application service between the post-turn Hook and ClaudeAgentService; it never runs the Agent.
# [Sync] 2026-09-01: initial persistence-first, one-attempt auto-repair message contract.

"""Build and persist one allowlisted Dream workspace auto-repair message."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping

try:
    import database
    from services.story_workspace.dream_artifact_turn_hook import (
        DreamArtifactRepairability,
        DreamArtifactValidationIssue,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend import database
    from backend.services.story_workspace.dream_artifact_turn_hook import (
        DreamArtifactRepairability,
        DreamArtifactValidationIssue,
    )


DREAM_AUTO_REPAIR_METADATA_KIND = "story-workspace-dream-auto-repair"
DREAM_AUTO_REPAIR_SCHEMA_VERSION = "story-workspace-dream-auto-repair/v1"
DREAM_AUTO_REPAIR_DISPATCHING = "dispatching"
DREAM_AUTO_REPAIR_DISPATCHED = "dispatched"
DREAM_AUTO_REPAIR_FAILED = "failed"

_MESSAGE_ID_PREFIX = "dream_repair_"
_STORY_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FINAL_STATUSES = frozenset(
    {DREAM_AUTO_REPAIR_DISPATCHED, DREAM_AUTO_REPAIR_FAILED}
)


class DreamAutoRepairError(RuntimeError):
    """Safe fail-closed error for auto-repair message orchestration."""

    def __init__(
        self,
        code: str,
        public_message: str,
        *,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.retryable = False
        if cause is not None:
            self.__cause__ = cause


class DreamAutoRepairExhaustedError(DreamAutoRepairError):
    """The only repair attempt ended without satisfying the same Hook."""

    def __init__(self, validation_code: str) -> None:
        super().__init__(
            "DREAM_WORKBENCH_AUTO_REPAIR_FAILED",
            (
                "Dream 工作区自动修正后仍未通过校验"
                f"（{validation_code}）。已停止自动修正，请查看上方修正消息。"
            ),
        )


@dataclass(frozen=True)
class DreamAutoRepairMessage:
    """Exact chat_message identity used by persistence, SSE, and next Turn."""

    id: str
    thread_id: str
    parts: tuple[dict[str, str], ...]
    metadata: dict[str, Any]

    def persistence_parts(self) -> list[dict[str, str]]:
        return [dict(part) for part in self.parts]

    def sse_message(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": "user",
            "parts": self.persistence_parts(),
            "metadata": dict(self.metadata),
        }


def dream_auto_repair_metadata_is_valid(metadata: object) -> bool:
    """Recognize only the server-authored v1 attempt marker."""

    return (
        isinstance(metadata, Mapping)
        and metadata.get("kind") == DREAM_AUTO_REPAIR_METADATA_KIND
        and metadata.get("schemaVersion") == DREAM_AUTO_REPAIR_SCHEMA_VERSION
        and metadata.get("repairAttempt") == 1
        and isinstance(metadata.get("originatingMessageId"), str)
        and bool(metadata.get("originatingMessageId"))
        and isinstance(metadata.get("originatingTurnId"), str)
        and bool(metadata.get("originatingTurnId"))
        and isinstance(metadata.get("workflowRunId"), str)
        and bool(metadata.get("workflowRunId"))
        and metadata.get("validationCode") == "PROJECT_STORY_SLUG_MISMATCH"
        and isinstance(metadata.get("idempotencyKey"), str)
        and bool(metadata.get("idempotencyKey"))
        and metadata.get("dispatch_status")
        in {
            DREAM_AUTO_REPAIR_DISPATCHING,
            DREAM_AUTO_REPAIR_DISPATCHED,
            DREAM_AUTO_REPAIR_FAILED,
        }
    )


def _repair_text(issue: DreamArtifactValidationIssue) -> str:
    if (
        issue.code != "PROJECT_STORY_SLUG_MISMATCH"
        or issue.repairability is not DreamArtifactRepairability.AGENT_REPAIRABLE
        or not isinstance(issue.expected, str)
        or not isinstance(issue.actual, str)
        or _STORY_SLUG.fullmatch(issue.expected) is None
        or _STORY_SLUG.fullmatch(issue.actual) is None
    ):
        raise DreamAutoRepairError(
            "DREAM_AUTO_REPAIR_NOT_ALLOWLISTED",
            "Dream 工作区校验不在自动修正允许范围内，已安全停止。",
        )
    return "\n".join(
        (
            "Dream 工作区同步校验未通过，请修正当前 workspace 后重新完成本轮。",
            "",
            "校验错误：",
            "- 错误代码：PROJECT_STORY_SLUG_MISMATCH",
            "- 规则：workspace canonical project slug 必须等于服务器分配的可信 project slug",
            f"- 期望值：{issue.expected}",
            f"- 当前状态：{issue.actual}",
            "- 失败原因：当前文件生成到了另一套项目目录，无法证明其属于本次 Dream Run",
            "- 修正要求：将本次项目文件整理到服务器指定的 canonical project 路径，并同步修正项目文件中的 project_id/project_slug",
            "- 禁止操作：不得修改 Dream 启动元数据、actor/thread/run 身份、Deck/plugin lock 或伪造绑定信息",
            "- 完成标准：重新执行同一个后置同步校验并全部通过",
        )
    )


def build_dream_auto_repair_message(
    *,
    issue: DreamArtifactValidationIssue,
    workflow_run_id: str,
    thread_id: str,
    originating_message_id: str,
    originating_turn_id: str,
) -> DreamAutoRepairMessage:
    """Build one deterministic message from server-owned bounded facts."""

    for label, value in (
        ("workflow Run", workflow_run_id),
        ("Thread", thread_id),
        ("originating message", originating_message_id),
        ("originating Turn", originating_turn_id),
    ):
        if not isinstance(value, str) or not value.strip():
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_IDENTITY_INVALID",
                f"Dream 自动修正缺少可信 {label} 身份，已安全停止。",
            )
    text = _repair_text(issue)
    digest = hashlib.sha256(
        "\n".join(
            (
                DREAM_AUTO_REPAIR_SCHEMA_VERSION,
                workflow_run_id,
                originating_message_id,
                issue.code,
            )
        ).encode("utf-8")
    ).hexdigest()
    message_id = f"{_MESSAGE_ID_PREFIX}{digest[:40]}"
    metadata = {
        "kind": DREAM_AUTO_REPAIR_METADATA_KIND,
        "schemaVersion": DREAM_AUTO_REPAIR_SCHEMA_VERSION,
        "originatingMessageId": originating_message_id,
        "originatingTurnId": originating_turn_id,
        "workflowRunId": workflow_run_id,
        "repairAttempt": 1,
        "validationCode": issue.code,
        "idempotencyKey": f"dream-auto-repair/v1:{digest}",
        "dispatch_status": DREAM_AUTO_REPAIR_DISPATCHING,
    }
    return DreamAutoRepairMessage(
        id=message_id,
        thread_id=thread_id,
        parts=({"type": "text", "text": text},),
        metadata=metadata,
    )


def persist_dream_auto_repair_message(message: DreamAutoRepairMessage) -> None:
    """Commit the exact user message before any SSE notification."""

    try:
        database.save_chat_message(
            message.thread_id,
            "user",
            message.persistence_parts(),
            message.id,
            dict(message.metadata),
        )
    except Exception as exc:
        raise DreamAutoRepairError(
            "DREAM_AUTO_REPAIR_MESSAGE_PERSIST_FAILED",
            "Dream 自动修正消息无法安全保存，未启动自动修正。",
            cause=exc,
        ) from exc


def _decode_metadata(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_MESSAGE_INVALID",
                "Dream 自动修正消息状态不可验证，已安全停止。",
                cause=exc,
            ) from exc
        if isinstance(value, dict):
            return value
    raise DreamAutoRepairError(
        "DREAM_AUTO_REPAIR_MESSAGE_INVALID",
        "Dream 自动修正消息状态不可验证，已安全停止。",
    )


def settle_dream_auto_repair_message(
    message_id: str,
    *,
    thread_id: str,
    expected_metadata: Mapping[str, Any],
    status: str,
) -> bool:
    """CAS one visible status transition; return false for exact replay."""

    if status not in _FINAL_STATUSES:
        raise ValueError("Dream auto-repair final status is invalid")
    db = database.get_db()
    try:
        db.execute("BEGIN")
        row = db.execute(
            "SELECT thread_id, role, metadata FROM chat_message WHERE id = %s",
            (message_id,),
        ).fetchone()
        if row is None:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_MESSAGE_INVALID",
                "Dream 自动修正消息状态不可验证，已安全停止。",
            )
        stored = _decode_metadata(row["metadata"])
        expected = dict(expected_metadata)
        valid = (
            row["thread_id"] == thread_id
            and row["role"] == "user"
            and dream_auto_repair_metadata_is_valid(stored)
            and all(
                stored.get(field) == expected.get(field)
                for field in (
                    "kind",
                    "schemaVersion",
                    "originatingMessageId",
                    "originatingTurnId",
                    "workflowRunId",
                    "repairAttempt",
                    "validationCode",
                    "idempotencyKey",
                )
            )
        )
        if not valid:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_MESSAGE_INVALID",
                "Dream 自动修正消息状态不可验证，已安全停止。",
            )
        current_status = stored.get("dispatch_status")
        if current_status == status:
            db.commit()
            return False
        valid_transition = (
            current_status == DREAM_AUTO_REPAIR_DISPATCHING
            and status in _FINAL_STATUSES
        ) or (
            current_status == DREAM_AUTO_REPAIR_DISPATCHED
            and status == DREAM_AUTO_REPAIR_FAILED
        )
        if not valid_transition:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_MESSAGE_CONFLICT",
                "Dream 自动修正消息状态发生冲突，已安全停止。",
            )
        updated_metadata = dict(stored)
        updated_metadata["dispatch_status"] = status
        updated = db.execute(
            "UPDATE chat_message SET metadata = %s WHERE id = %s "
            "AND thread_id = %s AND role = 'user' AND metadata = %s",
            (
                json.dumps(
                    updated_metadata,
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                message_id,
                thread_id,
                row["metadata"],
            ),
        )
        if updated.rowcount != 1:
            replay = db.execute(
                "SELECT thread_id, role, metadata FROM chat_message WHERE id = %s",
                (message_id,),
            ).fetchone()
            if replay is not None:
                replayed_metadata = _decode_metadata(replay["metadata"])
                replay_is_same_claim = (
                    replay["thread_id"] == thread_id
                    and replay["role"] == "user"
                    and dream_auto_repair_metadata_is_valid(replayed_metadata)
                    and replayed_metadata.get("dispatch_status") == status
                    and all(
                        replayed_metadata.get(field) == expected.get(field)
                        for field in (
                            "kind",
                            "schemaVersion",
                            "originatingMessageId",
                            "originatingTurnId",
                            "workflowRunId",
                            "repairAttempt",
                            "validationCode",
                            "idempotencyKey",
                        )
                    )
                )
                if replay_is_same_claim:
                    db.commit()
                    return False
            db.rollback()
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_MESSAGE_CONFLICT",
                "Dream 自动修正消息状态发生冲突，已安全停止。",
            )
        db.commit()
        return True
    except DreamAutoRepairError:
        if db.in_transaction:
            db.rollback()
        raise
    except Exception as exc:
        if db.in_transaction:
            db.rollback()
        raise DreamAutoRepairError(
            "DREAM_AUTO_REPAIR_STATUS_PERSIST_FAILED",
            "Dream 自动修正结果无法安全保存，已停止自动修正。",
            cause=exc,
        ) from exc
    finally:
        db.close()


__all__ = [
    "DREAM_AUTO_REPAIR_DISPATCHED",
    "DREAM_AUTO_REPAIR_DISPATCHING",
    "DREAM_AUTO_REPAIR_FAILED",
    "DREAM_AUTO_REPAIR_METADATA_KIND",
    "DREAM_AUTO_REPAIR_SCHEMA_VERSION",
    "DreamAutoRepairError",
    "DreamAutoRepairExhaustedError",
    "DreamAutoRepairMessage",
    "build_dream_auto_repair_message",
    "dream_auto_repair_metadata_is_valid",
    "persist_dream_auto_repair_message",
    "settle_dream_auto_repair_message",
]
