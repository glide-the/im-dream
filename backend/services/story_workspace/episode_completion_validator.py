"""Postcondition validation for server-owned Episode workflow completions."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from services.story_workspace.episode_action_service import (
        StoryWorkspaceEpisodeNextActionResolver,
    )
    from story_workspace.contracts import (
        StoryWorkspaceEpisodeAction,
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeReviewScope,
        StoryWorkspaceEpisodeWorkflowFile,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.services.story_workspace.episode_action_service import (
        StoryWorkspaceEpisodeNextActionResolver,
    )
    from backend.story_workspace.contracts import (
        StoryWorkspaceEpisodeAction,
        StoryWorkspaceEpisodeArtifactAvailability,
        StoryWorkspaceEpisodeReviewScope,
        StoryWorkspaceEpisodeWorkflowFile,
    )


@dataclass(frozen=True)
class StoryWorkspaceEpisodeCompletionContractError(RuntimeError):
    """A safe public reason for rejecting a completion handshake."""

    reason: str
    public_message: str

    def __str__(self) -> str:
        return self.reason


class StoryWorkspaceEpisodeCompletionValidator:
    """Validate canonical outputs without trusting the Agent's success claim."""

    @staticmethod
    def _reject(reason: str, public_message: str) -> None:
        raise StoryWorkspaceEpisodeCompletionContractError(
            reason=reason,
            public_message=public_message,
        )

    @classmethod
    def validate_before_record(
        cls,
        *,
        action: StoryWorkspaceEpisodeAction,
        surface: object,
        alias_report_present: bool,
    ) -> None:
        if action is not StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN:
            return
        artifacts = StoryWorkspaceEpisodeNextActionResolver._artifact_map(  # noqa: SLF001
            surface
        )
        report_artifact = artifacts.get("review-report.md")
        auxiliary = getattr(surface, "auxiliary", None)
        review = getattr(auxiliary, "review", None)
        if (
            getattr(report_artifact, "availability", None)
            is not StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
            or review is None
        ):
            cls._reject(
                "canonical_review_report_required",
                "完整链路审阅必须更新当前 Episode 的规范 review-report.md。",
            )
        if (
            getattr(review, "scope", None)
            is not StoryWorkspaceEpisodeReviewScope.FULL_CHAIN
        ):
            cls._reject(
                (
                    "canonical_review_report_required"
                    if alias_report_present
                    else "full_chain_scope_required"
                ),
                (
                    "检测到非规范审阅报告；请将完整链路结果写入 review-report.md，"
                    "并声明 scope: full-chain。"
                    if alias_report_present
                    else "review-report.md 必须声明 scope: full-chain。"
                ),
            )
        if getattr(review, "overall_verdict", None) != "APPROVED":
            cls._reject(
                "approved_verdict_required",
                "完整链路审阅尚未通过；overall_verdict 必须为 APPROVED。",
            )

        prompt_page = getattr(auxiliary, "prompts", None)
        associations = getattr(auxiliary, "associations", None)
        coverage = getattr(associations, "shot_prompt_coverage", None)
        prompt_items = getattr(prompt_page, "items", None)
        if (
            not isinstance(prompt_items, list)
            or getattr(prompt_page, "next_cursor", None) is not None
            or getattr(prompt_page, "total", None) != len(prompt_items)
            or getattr(associations, "orphan_prompts", None) != []
            or not isinstance(getattr(coverage, "total", None), int)
            or getattr(coverage, "total", 0) <= 0
            or getattr(coverage, "linked", None) != getattr(coverage, "total", None)
        ):
            cls._reject(
                "complete_prompt_coverage_required",
                "分镜与 Prompt 尚未完整关联；必须覆盖全部 shot 且不存在孤立 Prompt。",
            )

        current_revisions = {
            key: getattr(artifacts.get(key), "content_revision", None)
            for key in (
                "episode-outline.md",
                "script.md",
                "storyboard.yaml",
            )
        }
        for item in prompt_items:
            source = getattr(item, "source_artifact", None)
            revision = getattr(item, "source_revision", None)
            if not isinstance(source, str) or not isinstance(revision, str):
                cls._reject(
                    "complete_prompt_coverage_required",
                    "Prompt 包缺少可验证的规范来源。",
                )
            existing = current_revisions.get(source)
            if existing is not None and existing != revision:
                cls._reject(
                    "current_source_revisions_required",
                    "Prompt 包包含冲突的来源 revision。",
                )
            current_revisions[source] = revision
        if any(revision is None for revision in current_revisions.values()):
            cls._reject(
                "current_source_revisions_required",
                "完整链路审阅缺少当前 canonical source revisions。",
            )
        reviewed_artifacts = getattr(review, "reviewed_artifacts", None)
        if not isinstance(reviewed_artifacts, list) or set(reviewed_artifacts) != set(
            current_revisions
        ):
            cls._reject(
                "reviewed_artifacts_required",
                "reviewed_files 必须覆盖当前 outline、script、storyboard 与全部 Prompt 文件。",
            )
        reviewed_revisions = {
            getattr(item, "source_artifact", None): getattr(
                item,
                "source_revision",
                None,
            )
            for item in getattr(review, "source_revisions", [])
        }
        if reviewed_revisions != current_revisions:
            cls._reject(
                "current_source_revisions_required",
                "source_revisions 必须与当前 canonical inputs 完全一致。",
            )
        if not StoryWorkspaceEpisodeNextActionResolver.full_chain_review_is_current(
            surface
        ):
            cls._reject(
                "full_chain_review_contract_invalid",
                "完整链路审阅未满足规范输出合同。",
            )

    @classmethod
    def validate_transition_ready(
        cls,
        *,
        action: StoryWorkspaceEpisodeAction,
        surface: object,
        facts: StoryWorkspaceEpisodeWorkflowFile,
    ) -> None:
        if action is not StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN:
            return
        current_action = StoryWorkspaceEpisodeNextActionResolver.project(
            surface,
            facts,
        ).next_action
        if (
            current_action.action is not StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN
            or not current_action.can_dispatch
        ):
            cls._reject(
                "workflow_transition_not_ready",
                "当前 Episode 的上游完成事实尚未满足完整链路审阅条件。",
            )

    @classmethod
    def validate_after_record(
        cls,
        *,
        action: StoryWorkspaceEpisodeAction,
        surface: object,
        facts: StoryWorkspaceEpisodeWorkflowFile,
    ) -> None:
        if action is not StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN:
            return
        next_action = StoryWorkspaceEpisodeNextActionResolver.project(
            surface,
            facts,
        ).next_action
        if next_action.action is not StoryWorkspaceEpisodeAction.VALIDATE_EPISODE:
            cls._reject(
                "workflow_transition_not_ready",
                "完整链路审阅已写入，但服务端复核尚未进入“校验并提交”阶段。",
            )


__all__ = [
    "StoryWorkspaceEpisodeCompletionContractError",
    "StoryWorkspaceEpisodeCompletionValidator",
]
