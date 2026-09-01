# [Input] Structured DreamArtifactValidationIssue, canonical chat_message persistence, and server-owned Dream Turn identity.
# [Output] One stable visible auto-repair user message plus bounded dispatch-status settlement helpers.
# [Pos] Dream application service between the post-turn Hook and ClaudeAgentService; it never runs the Agent.
# [Sync] 2026-09-01: initial persistence-first, one-attempt auto-repair message contract.
# [Sync] 2026-09-01: add bounded canonical-root/stage-schema repair templates,
#                    require move/merge cleanup, and expose a safe final reason
#                    when the single repair attempt is exhausted.

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
_VALIDATION_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_STAGE_NAMES = frozenset({"characters", "scenes", "storyboards"})
_AUTO_REPAIR_VALIDATION_CODES = frozenset(
    {
        "PROJECT_STORY_SLUG_MISMATCH",
        "DREAM_CANONICAL_PROJECT_AMBIGUOUS",
        "DREAM_STAGE_ENTITY_ID_DUPLICATE",
        "DREAM_STAGE_SCHEMA_INVALID",
    }
)
_EXHAUSTED_PUBLIC_DETAILS = {
    "PROJECT_STORY_SLUG_MISMATCH": "workspace project slug 仍与可信绑定不一致。",
    "DREAM_CANONICAL_PROJECT_AMBIGUOUS": (
        "workspace 仍存在多个 canonical 项目目录。"
    ),
    "DREAM_STAGE_ENTITY_ID_DUPLICATE": (
        "workspace stage 中仍存在重复 entity_id。"
    ),
    "DREAM_STAGE_SCHEMA_INVALID": "workspace stage 仍不符合结构合同。",
    "DREAM_LAUNCH_AUTHORITY_INVALID": "Dream 可信启动身份未通过校验。",
    "DREAM_ARTIFACT_SYNC_FAILED": "Dream 工作区同步仍未完成。",
}
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
        safe_code = (
            validation_code
            if isinstance(validation_code, str)
            and _VALIDATION_CODE.fullmatch(validation_code) is not None
            and validation_code in _EXHAUSTED_PUBLIC_DETAILS
            else "DREAM_ARTIFACT_SYNC_FAILED"
        )
        detail = _EXHAUSTED_PUBLIC_DETAILS.get(
            safe_code,
            "Dream 工作区最终校验仍未通过。",
        )
        super().__init__(
            "DREAM_WORKBENCH_AUTO_REPAIR_FAILED",
            (
                "Dream 工作区自动修正后仍未通过校验。"
                f"最终错误：{safe_code}；{detail}"
                "已停止自动修正，不会发起第三轮。"
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
        and metadata.get("validationCode") in _AUTO_REPAIR_VALIDATION_CODES
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
    if issue.repairability is not DreamArtifactRepairability.AGENT_REPAIRABLE:
        raise DreamAutoRepairError(
            "DREAM_AUTO_REPAIR_NOT_ALLOWLISTED",
            "Dream 工作区校验不在自动修正允许范围内，已安全停止。",
        )
    common_prefix = (
        "Dream 工作区同步校验未通过，请修正当前 workspace 后重新完成本轮。",
        "",
        "校验错误：",
    )
    common_suffix = (
        "- 禁止操作：不得修改 Dream 启动元数据、actor/thread/run 身份、Deck/plugin lock 或伪造绑定信息",
        "- 完成标准：重新执行同一个后置同步校验并全部通过",
    )
    if issue.code == "PROJECT_STORY_SLUG_MISMATCH":
        if (
            not isinstance(issue.expected, str)
            or not isinstance(issue.actual, str)
            or _STORY_SLUG.fullmatch(issue.expected) is None
            or _STORY_SLUG.fullmatch(issue.actual) is None
        ):
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_NOT_ALLOWLISTED",
                "Dream 工作区校验不在自动修正允许范围内，已安全停止。",
            )
        details = (
            "- 错误代码：PROJECT_STORY_SLUG_MISMATCH",
            "- 规则：workspace canonical project slug 必须等于服务器分配的可信 project slug",
            f"- 期望值：{issue.expected}",
            f"- 当前状态：{issue.actual}",
            "- 失败原因：当前文件生成到了另一套项目目录，无法证明其属于本次 Dream Run",
            "- 修正要求：将旧项目内容移动或合并到服务器指定的 canonical project 路径，同步修正 project_id/project_slug；确认内容完整后移除旧 slug 的重复项目根",
            "- 清理要求：不得只复制目录并同时保留两套 project.yaml 或同一 Episode；stories 下最终只能保留本次 Run 的唯一 canonical 项目",
        )
    elif issue.code == "DREAM_CANONICAL_PROJECT_AMBIGUOUS":
        if issue.expected is not None or issue.actual is not None:
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_NOT_ALLOWLISTED",
                "Dream 工作区校验不在自动修正允许范围内，已安全停止。",
            )
        details = (
            "- 错误代码：DREAM_CANONICAL_PROJECT_AMBIGUOUS",
            "- 规则：一次 Dream Run 只能解析到一个 canonical 项目目录",
            "- 失败原因：stories 下存在多套带 project.yaml 的项目根，无法确定哪套文件属于本次 Run",
            "- 修正要求：以服务器上下文指定的 canonical 项目路径为准，先合并或移动本次内容，核对完整后移除其余重复项目根",
            "- 清理要求：不得通过伪造新 slug、改写可信绑定或把同一 Episode 改成虚假 entity_id 来绕过唯一性校验",
        )
    elif issue.code in {
        "DREAM_STAGE_ENTITY_ID_DUPLICATE",
        "DREAM_STAGE_SCHEMA_INVALID",
    }:
        if (
            issue.expected not in _STAGE_NAMES
            or issue.actual
            not in {"duplicate_entity_id", "schema_invalid"}
            or (
                issue.code == "DREAM_STAGE_ENTITY_ID_DUPLICATE"
                and issue.actual != "duplicate_entity_id"
            )
            or (
                issue.code == "DREAM_STAGE_SCHEMA_INVALID"
                and issue.actual != "schema_invalid"
            )
        ):
            raise DreamAutoRepairError(
                "DREAM_AUTO_REPAIR_NOT_ALLOWLISTED",
                "Dream 工作区校验不在自动修正允许范围内，已安全停止。",
            )
        duplicate = issue.code == "DREAM_STAGE_ENTITY_ID_DUPLICATE"
        details = (
            f"- 错误代码：{issue.code}",
            f"- 规则：{issue.expected} stage 的 source_file 与 entity_id 必须满足 Dream 工作台结构合同",
            (
                "- 失败原因：多个工作区源文件被解析成了同一个 entity_id"
                if duplicate
                else "- 失败原因：工作区源文件生成的 stage 字段、引用或大小不符合合同"
            ),
            "- 修正要求：根据 source_file 合并重复实体并保留唯一 canonical 来源；若重复来自旧项目根，迁移内容后移除旧根",
            "- 清理要求：不得仅篡改 entity_id 制造表面唯一，也不得删除尚未合并的用户内容",
        )
    else:
        raise DreamAutoRepairError(
            "DREAM_AUTO_REPAIR_NOT_ALLOWLISTED",
            "Dream 工作区校验不在自动修正允许范围内，已安全停止。",
        )
    return "\n".join((*common_prefix, *details, *common_suffix))


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
