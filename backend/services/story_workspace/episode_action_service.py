"""Evidence-derived Episode actions dispatched through the Dream message seam."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from typing import Any, Callable, Mapping

try:
    from services.story_workspace.dream_agent_message_service import (
        STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        StoryWorkspaceDreamAgentMessageService,
        StoryWorkspaceDreamAgentPendingDispatch,
    )
    from story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeAction,
        StoryWorkspaceEpisodeActionAccepted,
        StoryWorkspaceEpisodeActionContinueCommand,
        StoryWorkspaceEpisodeActionDiagnostic,
        StoryWorkspaceEpisodeActionResolution,
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeBindingRecoveryCommand,
        StoryWorkspaceEpisodeReviewScope,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.services.story_workspace.dream_agent_message_service import (
        STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        StoryWorkspaceDreamAgentMessageService,
        StoryWorkspaceDreamAgentPendingDispatch,
    )
    from backend.story_workspace.contracts import (
        StoryWorkspaceDreamAgentMessageCommand,
        StoryWorkspaceDreamRunContext,
        StoryWorkspaceEpisodeAction,
        StoryWorkspaceEpisodeActionAccepted,
        StoryWorkspaceEpisodeActionContinueCommand,
        StoryWorkspaceEpisodeActionDiagnostic,
        StoryWorkspaceEpisodeActionResolution,
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeBindingRecoveryCommand,
        StoryWorkspaceEpisodeReviewScope,
    )


_ACTION_FACTS_SCHEMA = "story-workspace-episode-action-facts/v1"
_REVISION = re.compile(r"^sha256:[0-9a-f]{64}$")
_ACTION_LABELS = {
    StoryWorkspaceEpisodeAction.PLAN_EPISODE: "规划第一集",
    StoryWorkspaceEpisodeAction.WRITE_SCRIPT: "创作第一集剧本",
    StoryWorkspaceEpisodeAction.REVIEW_SCRIPT: "审阅第一集剧本",
    StoryWorkspaceEpisodeAction.REFRESH_ASSETS: "核对并完善角色与场景资产",
    StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD: "生成或更新第一集分镜",
    StoryWorkspaceEpisodeAction.GENERATE_PROMPTS: "生成第一集镜头提示词",
    StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN: "审阅第一集完整创作链路",
    StoryWorkspaceEpisodeAction.VALIDATE_EPISODE: "校验第一集完整产物",
    StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE: "准备第一集渲染指引",
    StoryWorkspaceEpisodeAction.NONE_IN_SCOPE: "本期工作流已无待推进步骤",
}
_VENDOR_FIRST_EPISODE_FLOW = (
    (StoryWorkspaceEpisodeAction.PLAN_EPISODE, "/drama-plan"),
    (StoryWorkspaceEpisodeAction.WRITE_SCRIPT, "/drama-script (EP01)"),
    (StoryWorkspaceEpisodeAction.REVIEW_SCRIPT, "script-reviewer 审查"),
    (StoryWorkspaceEpisodeAction.REFRESH_ASSETS, "/drama-asset"),
    (StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD, "/drama-storyboard (EP01)"),
    (StoryWorkspaceEpisodeAction.GENERATE_PROMPTS, "/drama-prompt (EP01)"),
    (StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN, "[审查报告: APPROVED]"),
    (StoryWorkspaceEpisodeAction.VALIDATE_EPISODE, "validate_commit.sh"),
    (StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE, "/drama-render"),
)


def story_workspace_episode_vendor_workflow(
) -> tuple[tuple[StoryWorkspaceEpisodeAction, str], ...]:
    """Return the server-private README evidence mapping used by resolver tests."""

    return _VENDOR_FIRST_EPISODE_FLOW


class StoryWorkspaceEpisodeActionError(RuntimeError):
    """An allowlisted action failure with an optional latest public surface."""

    def __init__(
        self,
        code: str,
        status_code: int,
        *,
        latest_surface: object | None = None,
        resolution: StoryWorkspaceEpisodeActionResolution | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.latest_surface = latest_surface
        self.resolution = resolution


@dataclass(frozen=True)
class StoryWorkspaceEpisodeActionFacts:
    """Optional explicit producer facts frozen in the trusted launch source."""

    episode_uid: str
    assets_revision: str | None = None
    storyboard_script_revision: str | None = None
    storyboard_assets_revision: str | None = None
    prompts_storyboard_revision: str | None = None
    full_chain_review_input_revision: str | None = None
    validated_input_revision: str | None = None
    render_input_revision: str | None = None

    def __post_init__(self) -> None:
        if re.fullmatch(r"[0-9a-f]{32}", self.episode_uid) is None:
            raise ValueError("Episode action facts require an opaque Episode identity")
        for revision in (
            self.assets_revision,
            self.storyboard_script_revision,
            self.storyboard_assets_revision,
            self.prompts_storyboard_revision,
            self.full_chain_review_input_revision,
            self.validated_input_revision,
            self.render_input_revision,
        ):
            if revision is not None and _REVISION.fullmatch(revision) is None:
                raise ValueError("Episode action facts require opaque revisions")

    @classmethod
    def empty(cls, episode_uid: str) -> "StoryWorkspaceEpisodeActionFacts":
        return cls(episode_uid=episode_uid)

    @classmethod
    def parse(
        cls,
        source_metadata: object,
        *,
        episode_uid: str,
    ) -> "StoryWorkspaceEpisodeActionFacts":
        """Fail ambiguous producer metadata to an empty, non-authoritative fact set."""

        if not isinstance(source_metadata, Mapping):
            return cls.empty(episode_uid)
        value = source_metadata.get("story_workspace_episode_action_facts")
        expected = {
            "schema",
            "episode_uid",
            "assets_revision",
            "storyboard_script_revision",
            "storyboard_assets_revision",
            "prompts_storyboard_revision",
            "full_chain_review_input_revision",
            "validated_input_revision",
            "render_input_revision",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            return cls.empty(episode_uid)
        if value.get("schema") != _ACTION_FACTS_SCHEMA or value.get("episode_uid") != episode_uid:
            return cls.empty(episode_uid)
        revisions = {
            key: value.get(key)
            for key in expected
            if key not in {"schema", "episode_uid"}
        }
        if any(
            revision is not None
            and (not isinstance(revision, str) or _REVISION.fullmatch(revision) is None)
            for revision in revisions.values()
        ):
            return cls.empty(episode_uid)
        return cls(episode_uid=episode_uid, **revisions)


class StoryWorkspaceEpisodeNextActionResolver:
    """Derive one capability from canonical availability and explicit revisions."""

    @staticmethod
    def _artifact_map(surface: object) -> dict[str, object]:
        artifacts = getattr(surface, "artifacts", None)
        if not isinstance(artifacts, list):
            return {}
        return {
            item.relative_key: item
            for item in artifacts
            if isinstance(getattr(item, "relative_key", None), str)
        }

    @staticmethod
    def _availability(item: object | None) -> object | None:
        return getattr(item, "availability", None)

    @classmethod
    def _available(cls, item: object | None) -> bool:
        return cls._availability(item) is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE

    @classmethod
    def _missing_diagnostic(
        cls,
        item: object | None,
    ) -> StoryWorkspaceEpisodeActionDiagnostic:
        return (
            StoryWorkspaceEpisodeActionDiagnostic.READY
            if cls._availability(item)
            is StoryWorkspaceEpisodeArtifactAvailability.NOT_GENERATED
            else StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION
        )

    @staticmethod
    def _resolution(
        action: StoryWorkspaceEpisodeAction,
        diagnostic: StoryWorkspaceEpisodeActionDiagnostic,
    ) -> StoryWorkspaceEpisodeActionResolution:
        return StoryWorkspaceEpisodeActionResolution(
            action=action,
            diagnostic=diagnostic,
            canDispatch=action is not StoryWorkspaceEpisodeAction.NONE_IN_SCOPE,
        )

    @staticmethod
    def _revision(item: object | None) -> str | None:
        revision = getattr(item, "content_revision", None)
        return revision if isinstance(revision, str) else None

    @staticmethod
    def _input_revision(
        artifacts: Mapping[str, object],
        keys: tuple[str, ...],
    ) -> str:
        payload = [
            [
                key,
                getattr(artifacts.get(key), "availability", None).value
                if getattr(artifacts.get(key), "availability", None) is not None
                else None,
                getattr(artifacts.get(key), "content_revision", None),
            ]
            for key in keys
        ]
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    @classmethod
    def full_chain_input_revision(cls, surface: object) -> str:
        return cls._input_revision(
            cls._artifact_map(surface),
            ("episode-outline.md", "script.md", "storyboard.yaml", "prompts/"),
        )

    @classmethod
    def validation_input_revision(cls, surface: object) -> str:
        return cls._input_revision(
            cls._artifact_map(surface),
            (
                "episode-outline.md",
                "script.md",
                "storyboard.yaml",
                "prompts/",
                "review-report.md",
            ),
        )

    @staticmethod
    def _review(surface: object) -> object | None:
        auxiliary = getattr(surface, "auxiliary", None)
        return getattr(auxiliary, "review", None)

    @staticmethod
    def _reviewed_revision(
        review: object | None,
        key: str,
    ) -> str | None:
        revisions = getattr(review, "source_revisions", None)
        if not isinstance(revisions, list):
            return None
        matches = [
            getattr(item, "source_revision", None)
            for item in revisions
            if getattr(item, "source_artifact", None) == key
        ]
        return matches[0] if len(matches) == 1 and isinstance(matches[0], str) else None

    def resolve(
        self,
        surface: object,
        facts: StoryWorkspaceEpisodeActionFacts,
    ) -> StoryWorkspaceEpisodeActionResolution:
        artifacts = self._artifact_map(surface)
        outline = artifacts.get("episode-outline.md")
        script = artifacts.get("script.md")
        storyboard = artifacts.get("storyboard.yaml")
        prompts = artifacts.get("prompts/")
        renders = artifacts.get("renders/")
        report = artifacts.get("review-report.md")

        if not self._available(outline):
            return self._resolution(
                StoryWorkspaceEpisodeAction.PLAN_EPISODE,
                self._missing_diagnostic(outline),
            )
        if not self._available(script):
            return self._resolution(
                StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
                self._missing_diagnostic(script),
            )

        review = self._review(surface)
        review_scope = getattr(review, "scope", None)
        script_revision = self._revision(script)
        reviewed_script_revision = self._reviewed_revision(review, "script.md")
        script_review_is_current = (
            review_scope
            in {
                StoryWorkspaceEpisodeReviewScope.SCRIPT,
                StoryWorkspaceEpisodeReviewScope.FULL_CHAIN,
            }
            and script_revision is not None
            and reviewed_script_revision == script_revision
        )
        if not script_review_is_current:
            return self._resolution(
                StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
                (
                    StoryWorkspaceEpisodeActionDiagnostic.READY
                    if not self._available(report)
                    else StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION
                ),
            )

        if facts.assets_revision is None:
            return self._resolution(
                StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
                StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
            )
        if not self._available(storyboard):
            return self._resolution(
                StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
                self._missing_diagnostic(storyboard),
            )
        if (
            facts.storyboard_script_revision != script_revision
            or facts.storyboard_assets_revision != facts.assets_revision
        ):
            return self._resolution(
                StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
                StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
            )

        storyboard_revision = self._revision(storyboard)
        if not self._available(prompts):
            return self._resolution(
                StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
                self._missing_diagnostic(prompts),
            )
        if facts.prompts_storyboard_revision != storyboard_revision:
            return self._resolution(
                StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
                StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
            )

        full_chain_revision = self.full_chain_input_revision(surface)
        if (
            review_scope is not StoryWorkspaceEpisodeReviewScope.FULL_CHAIN
            or facts.full_chain_review_input_revision != full_chain_revision
        ):
            return self._resolution(
                StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
                (
                    StoryWorkspaceEpisodeActionDiagnostic.READY
                    if review_scope is StoryWorkspaceEpisodeReviewScope.SCRIPT
                    else StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION
                ),
            )

        validation_revision = self.validation_input_revision(surface)
        if facts.validated_input_revision != validation_revision:
            return self._resolution(
                StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
                StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
            )
        if not self._available(renders):
            return self._resolution(
                StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
                self._missing_diagnostic(renders),
            )
        if facts.render_input_revision != validation_revision:
            return self._resolution(
                StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
                StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
            )
        return self._resolution(
            StoryWorkspaceEpisodeAction.NONE_IN_SCOPE,
            StoryWorkspaceEpisodeActionDiagnostic.READY,
        )


class StoryWorkspaceEpisodeActionService:
    """Build controlled envelopes, then reuse the durable Dream message claim."""

    def __init__(
        self,
        db: sqlite3.Connection,
        *,
        thread_factory: object | None = None,
        db_factory: Callable[[], sqlite3.Connection] | None = None,
        resolver: StoryWorkspaceEpisodeNextActionResolver | None = None,
    ) -> None:
        self._db = db
        self._message_service = StoryWorkspaceDreamAgentMessageService(
            db,
            thread_factory=thread_factory,
            db_factory=db_factory,
        )
        self._resolver = resolver or StoryWorkspaceEpisodeNextActionResolver()

    def _has_existing_key(
        self,
        *,
        run_id: str,
        thread_id: str,
        actor_id: str,
        key: str,
    ) -> bool:
        rows = self._db.execute(
            "SELECT metadata FROM chat_message WHERE thread_id = ? AND role = 'user'",
            (thread_id,),
        ).fetchall()
        for row in rows:
            try:
                metadata = json.loads(row["metadata"] or "{}")
            except (TypeError, ValueError):
                continue
            if (
                isinstance(metadata, dict)
                and metadata.get("kind") == STORY_WORKSPACE_DREAM_AGENT_USER_KIND
                and metadata.get("story_workspace_run_id") == run_id
                and str(metadata.get("actor_id") or "") == actor_id
                and metadata.get("idempotency_key") == key
            ):
                return True
        return False

    def _claim(
        self,
        *,
        run_id: str,
        actor_id: str,
        context: StoryWorkspaceDreamRunContext,
        key: str,
        capability: StoryWorkspaceEpisodeAction | str,
        episode_id: str | None,
        text: str,
    ) -> tuple[
        StoryWorkspaceEpisodeActionAccepted,
        StoryWorkspaceDreamAgentPendingDispatch | None,
    ]:
        replayed = self._has_existing_key(
            run_id=run_id,
            thread_id=context.thread_id,
            actor_id=actor_id,
            key=key,
        )
        accepted, pending = self._message_service.claim_message(
            run_id=run_id,
            thread_id=context.thread_id,
            actor_id=actor_id,
            context=context,
            command=StoryWorkspaceDreamAgentMessageCommand(
                text=text,
                idempotencyKey=key,
            ),
        )
        return StoryWorkspaceEpisodeActionAccepted(
            runId=run_id,
            episodeId=episode_id,
            capability=capability,
            messageId=accepted.message_id,
            replayed=replayed,
        ), pending

    @staticmethod
    def _recover_text() -> str:
        return (
            "请恢复第一集关联。"
            "请仅根据当前 Dream 运行上下文核对规范项目标识，"
            "有充分证据时恢复 EP01 关联；证据不足时说明仍需确认。"
        )

    @staticmethod
    def _continue_text(
        command: StoryWorkspaceEpisodeActionContinueCommand,
        *,
        manifest_revision: str,
    ) -> str:
        label = _ACTION_LABELS[command.action]
        lines = [
            "请继续推进第一集创作。",
            f"目标能力：{label}",
            f"第一集标识：{command.episode_id}",
            f"内容快照：{manifest_revision}",
            "执行前请核对上游显式版本事实，不要假定步骤已经完成。",
        ]
        if command.user_guidance is not None:
            lines.append(f"用户补充：{command.user_guidance}")
        return "\n".join(lines)

    def recover_binding(
        self,
        *,
        run_id: str,
        actor_id: str,
        context: StoryWorkspaceDreamRunContext,
        command: StoryWorkspaceEpisodeBindingRecoveryCommand,
    ) -> tuple[
        StoryWorkspaceEpisodeActionAccepted,
        StoryWorkspaceDreamAgentPendingDispatch | None,
    ]:
        return self._claim(
            run_id=run_id,
            actor_id=actor_id,
            context=context,
            key=command.idempotency_key,
            capability="recover_first_episode_binding",
            episode_id=None,
            text=self._recover_text(),
        )

    def continue_episode(
        self,
        *,
        run_id: str,
        actor_id: str,
        context: StoryWorkspaceDreamRunContext,
        surface: object,
        action_facts: StoryWorkspaceEpisodeActionFacts,
        if_match: str,
        command: StoryWorkspaceEpisodeActionContinueCommand,
    ) -> tuple[
        StoryWorkspaceEpisodeActionAccepted,
        StoryWorkspaceDreamAgentPendingDispatch | None,
    ]:
        manifest_revision = getattr(surface, "manifest_revision", None)
        replay_text = self._continue_text(
            command,
            manifest_revision=if_match[1:-1] if len(if_match) > 2 else if_match,
        )
        if self._has_existing_key(
            run_id=run_id,
            thread_id=context.thread_id,
            actor_id=actor_id,
            key=command.idempotency_key,
        ):
            return self._claim(
                run_id=run_id,
                actor_id=actor_id,
                context=context,
                key=command.idempotency_key,
                capability=command.action,
                episode_id=command.episode_id,
                text=replay_text,
            )
        if (
            not isinstance(manifest_revision, str)
            or if_match != f'"{manifest_revision}"'
        ):
            raise StoryWorkspaceEpisodeActionError(
                "BINDING_REVISION_CONFLICT",
                409,
                latest_surface=surface,
            )
        if getattr(surface, "opaque_episode_id", None) != command.episode_id:
            raise StoryWorkspaceEpisodeActionError(
                "WORKFLOW_PERMISSION_DENIED",
                404,
            )
        if action_facts.episode_uid != command.episode_id:
            raise StoryWorkspaceEpisodeActionError(
                "WORKFLOW_PERMISSION_DENIED",
                404,
            )
        resolution = self._resolver.resolve(surface, action_facts)
        if not resolution.can_dispatch or resolution.action is not command.action:
            raise StoryWorkspaceEpisodeActionError(
                "BINDING_REVISION_CONFLICT",
                409,
                latest_surface=surface,
                resolution=resolution,
            )
        text = self._continue_text(
            command,
            manifest_revision=manifest_revision,
        )
        return self._claim(
            run_id=run_id,
            actor_id=actor_id,
            context=context,
            key=command.idempotency_key,
            capability=command.action,
            episode_id=command.episode_id,
            text=text,
        )


__all__ = [
    "StoryWorkspaceEpisodeActionError",
    "StoryWorkspaceEpisodeActionFacts",
    "StoryWorkspaceEpisodeActionService",
    "StoryWorkspaceEpisodeNextActionResolver",
    "story_workspace_episode_vendor_workflow",
]
