"""Server-owned current/next Episode workflow action projection."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re

from services.story_workspace.episode_action_service import (
    StoryWorkspaceEpisodeNextActionResolver,
)
from story_workspace.contracts import (
    StoryWorkspaceAssetContextCanonicalInput,
    StoryWorkspaceEpisodeAction,
    StoryWorkspaceEpisodeActionAvailability,
    StoryWorkspaceEpisodeActionDispatchState,
    StoryWorkspaceEpisodeActionOptionV2,
    StoryWorkspaceEpisodeActionProjectionV2,
    StoryWorkspaceEpisodeActionTarget,
    StoryWorkspaceEpisodeArtifactAvailability,
    StoryWorkspaceEpisodeArtifactCanonicalInput,
    StoryWorkspaceEpisodeRelation,
    StoryWorkspaceEpisodeRegistryFile,
    StoryWorkspaceEpisodeWorkflowFile,
    StoryWorkspaceProjectArtifactCanonicalInput,
    StoryWorkspaceWorkflowFactCanonicalInput,
)


_VENDOR_ACTIONS = (
    StoryWorkspaceEpisodeAction.PLAN_EPISODE,
    StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
    StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
    StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
    StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
    StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
    StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
    StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
    StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
)


@dataclass(frozen=True)
class StoryWorkspaceEpisodeDescriptor:
    """Trusted path-free identity for one projected Episode."""

    episode_number: int
    display_label: str
    relation: str
    opaque_episode_id: str | None = None
    candidate_id: str | None = None

    def __post_init__(self) -> None:
        if self.episode_number < 1:
            raise ValueError("Episode numbers must be positive")
        if self.display_label != f"EP{self.episode_number:02d}":
            raise ValueError("Episode labels must be server-formatted")
        if self.relation not in {"current", "next"}:
            raise ValueError("Episode relation must stay within current/next")
        if (self.opaque_episode_id is None) == (self.candidate_id is None):
            raise ValueError("Episode descriptors require one opaque identity")
        if self.opaque_episode_id is not None and re.fullmatch(
            r"[0-9a-f]{32}", self.opaque_episode_id
        ) is None:
            raise ValueError("bound Episode identities must be opaque")
        if self.candidate_id is not None and re.fullmatch(
            r"episode_candidate_[0-9a-f]{64}", self.candidate_id
        ) is None:
            raise ValueError("next Episode candidates must be opaque")
        if self.relation == "current" and self.opaque_episode_id is None:
            raise ValueError("the current Episode must already be bound")


@dataclass(frozen=True)
class StoryWorkspaceEpisodeActionSnapshot:
    """Minimal trusted facts consumed by the pure option projector."""

    run_id: str
    current_episode: StoryWorkspaceEpisodeDescriptor
    current_action: StoryWorkspaceEpisodeAction
    current_can_dispatch: bool
    current_input_revision: str
    storyboard_current: bool
    storyboard_can_regenerate: bool
    validation_current: bool
    render_guide_current: bool
    next_episode: StoryWorkspaceEpisodeDescriptor | None
    next_entry_action: StoryWorkspaceEpisodeAction | None
    next_entry_can_dispatch: bool
    project_has_next_episode: bool
    next_input_revision: str | None = None

    def __post_init__(self) -> None:
        if re.fullmatch(r"run_[0-9a-f]{32}", self.run_id) is None:
            raise ValueError("action snapshots require a trusted run identity")
        if re.fullmatch(r"sha256:[0-9a-f]{64}", self.current_input_revision) is None:
            raise ValueError("action snapshots require an opaque input revision")
        if self.current_episode.relation != "current":
            raise ValueError("current_episode must use the current relation")
        if self.project_has_next_episode != (self.next_episode is not None):
            raise ValueError("next Episode availability must match its descriptor")
        if (self.next_episode is None) != (self.next_entry_action is None):
            raise ValueError("next Episode descriptors require one entry action")
        if (self.next_episode is None) != (self.next_input_revision is None):
            raise ValueError("next Episode descriptors require an input revision")
        if self.next_input_revision is not None and re.fullmatch(
            r"sha256:[0-9a-f]{64}", self.next_input_revision
        ) is None:
            raise ValueError("next Episode actions require an opaque input revision")
        if self.next_episode is not None and self.next_episode.relation != "next":
            raise ValueError("next_episode must use the next relation")
        if self.next_entry_action not in {
            None,
            StoryWorkspaceEpisodeAction.PLAN_EPISODE,
            StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
        }:
            raise ValueError("next Episode entry must be plan or script")


@dataclass(frozen=True)
class StoryWorkspaceEpisodeRegistryActionContext:
    """Server-derived current/next descriptors without exposing registry paths."""

    current_episode: StoryWorkspaceEpisodeDescriptor
    next_episode: StoryWorkspaceEpisodeDescriptor | None
    registry_revision: int

    @classmethod
    def build(
        cls,
        registry: StoryWorkspaceEpisodeRegistryFile,
        *,
        total_episodes: int,
    ) -> "StoryWorkspaceEpisodeRegistryActionContext":
        if (
            isinstance(total_episodes, bool)
            or not isinstance(total_episodes, int)
            or total_episodes < 1
            or total_episodes > 99
        ):
            raise ValueError("trusted total Episode count is invalid")
        if len(registry.episodes) > total_episodes:
            raise ValueError("Episode registry exceeds the trusted project plan")
        active = next(
            episode
            for episode in registry.episodes
            if episode.episode_uid == registry.active_episode_uid
        )
        current = StoryWorkspaceEpisodeDescriptor(
            opaque_episode_id=active.episode_uid,
            episode_number=active.episode_number,
            display_label=active.episode_code,
            relation="current",
        )
        next_number = active.episode_number + 1
        if next_number > total_episodes:
            return cls(
                current_episode=current,
                next_episode=None,
                registry_revision=registry.revision,
            )
        bound_next = next(
            (
                episode
                for episode in registry.episodes
                if episode.episode_number == next_number
            ),
            None,
        )
        if bound_next is not None:
            next_episode = StoryWorkspaceEpisodeDescriptor(
                opaque_episode_id=bound_next.episode_uid,
                episode_number=bound_next.episode_number,
                display_label=bound_next.episode_code,
                relation="next",
            )
        else:
            payload = {
                "episode_number": next_number,
                "registry_revision": registry.revision,
                "run_id": registry.workflow_run_id,
                "story_slug": registry.story_slug,
            }
            candidate_hash = hashlib.sha256(
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    allow_nan=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            next_episode = StoryWorkspaceEpisodeDescriptor(
                candidate_id=f"episode_candidate_{candidate_hash}",
                episode_number=next_number,
                display_label=f"EP{next_number:02d}",
                relation="next",
            )
        return cls(
            current_episode=current,
            next_episode=next_episode,
            registry_revision=registry.revision,
        )


class StoryWorkspaceNextEpisodeActionPlanner:
    """Attach the bounded next Episode entry only after trusted fact checks."""

    def __init__(
        self,
        resolver: StoryWorkspaceEpisodeNextActionResolver | None = None,
    ) -> None:
        self._resolver = resolver or StoryWorkspaceEpisodeNextActionResolver()

    @staticmethod
    def _combined_revision(
        snapshot: StoryWorkspaceEpisodeActionSnapshot,
        descriptor: StoryWorkspaceEpisodeDescriptor,
        entry_revision: str,
    ) -> str:
        payload = {
            "current_input_revision": snapshot.current_input_revision,
            "entry_revision": entry_revision,
            "target": descriptor.opaque_episode_id or descriptor.candidate_id,
        }
        return "sha256:" + hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

    def attach(
        self,
        snapshot: StoryWorkspaceEpisodeActionSnapshot,
        *,
        context: StoryWorkspaceEpisodeRegistryActionContext,
        next_surface: object | None = None,
        next_facts: StoryWorkspaceEpisodeWorkflowFile | None = None,
    ) -> StoryWorkspaceEpisodeActionSnapshot:
        if snapshot.current_episode != context.current_episode:
            raise ValueError("current action snapshot and Episode registry disagree")
        descriptor = context.next_episode
        if descriptor is None:
            if next_surface is not None or next_facts is not None:
                raise ValueError("terminal Episode cannot accept next Episode facts")
            return snapshot
        if (next_surface is None) != (next_facts is None):
            raise ValueError("next Episode surface and facts must be supplied together")
        if next_surface is None or next_facts is None:
            next_action = StoryWorkspaceEpisodeAction.PLAN_EPISODE
            next_can_dispatch = snapshot.validation_current
            entry_revision = "sha256:" + hashlib.sha256(
                f"candidate:{context.registry_revision}".encode("ascii")
            ).hexdigest()
        else:
            if descriptor.opaque_episode_id is None:
                raise ValueError("candidate Episode cannot own artifact facts")
            StoryWorkspaceCurrentEpisodeActionSnapshotBuilder._assert_identity(
                next_surface,
                next_facts,
                replace(descriptor, relation="current"),
            )
            workflow = self._resolver.project(next_surface, next_facts)
            next_action = workflow.next_action.action
            if next_action not in {
                StoryWorkspaceEpisodeAction.PLAN_EPISODE,
                StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
            }:
                raise ValueError("next Episode exceeds the two-step entry horizon")
            next_can_dispatch = (
                snapshot.validation_current and workflow.next_action.can_dispatch
            )
            entry_revision = self._resolver.action_input_revision(
                next_action,
                next_surface,
                next_facts,
            )
        return replace(
            snapshot,
            next_episode=descriptor,
            next_entry_action=next_action,
            next_entry_can_dispatch=next_can_dispatch,
            project_has_next_episode=True,
            next_input_revision=self._combined_revision(
                snapshot,
                descriptor,
                entry_revision,
            ),
        )


class StoryWorkspaceCurrentEpisodeActionSnapshotBuilder:
    """Bridge canonical manifest/facts into the path-free OptionV2 snapshot."""

    def __init__(
        self,
        resolver: StoryWorkspaceEpisodeNextActionResolver | None = None,
    ) -> None:
        self._resolver = resolver or StoryWorkspaceEpisodeNextActionResolver()

    @staticmethod
    def _assert_identity(
        surface: object,
        facts: StoryWorkspaceEpisodeWorkflowFile,
        current_episode: StoryWorkspaceEpisodeDescriptor,
    ) -> None:
        if current_episode.opaque_episode_id is None:
            raise ValueError("current Episode must have a bound opaque identity")
        if (
            getattr(surface, "run_id", None) != facts.workflow_run_id
            or getattr(surface, "opaque_episode_id", None) != facts.episode_uid
            or current_episode.opaque_episode_id != facts.episode_uid
        ):
            raise ValueError("surface, workflow facts, and Episode binding disagree")

    def build(
        self,
        *,
        surface: object,
        facts: StoryWorkspaceEpisodeWorkflowFile,
        current_episode: StoryWorkspaceEpisodeDescriptor,
    ) -> StoryWorkspaceEpisodeActionSnapshot:
        """Resolve the current action and safe storyboard re-entry from revisions."""

        self._assert_identity(surface, facts, current_episode)
        workflow = self._resolver.project(surface, facts)
        current_action = workflow.next_action.action
        artifacts = self._resolver._artifact_map(surface)  # noqa: SLF001
        storyboard = artifacts.get("storyboard.yaml")
        storyboard_available = (
            getattr(storyboard, "availability", None)
            is StoryWorkspaceEpisodeArtifactAvailability.AVAILABLE
        )
        assets_current = self._resolver._completion_is_current(  # noqa: SLF001
            StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
            surface,
            facts,
        )
        if current_action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE:
            at_or_after_storyboard = True
        else:
            at_or_after_storyboard = _VENDOR_ACTIONS.index(
                current_action
            ) >= _VENDOR_ACTIONS.index(
                StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD
            )
        storyboard_current = storyboard_available and self._resolver._completion_is_current(  # noqa: SLF001
            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
            surface,
            facts,
        )
        validation_current = self._resolver._completion_is_current(  # noqa: SLF001
            StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
            surface,
            facts,
        )
        render_current = self._resolver._completion_is_current(  # noqa: SLF001
            StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
            surface,
            facts,
        )
        return StoryWorkspaceEpisodeActionSnapshot(
            run_id=facts.workflow_run_id,
            current_episode=current_episode,
            current_action=current_action,
            current_can_dispatch=workflow.next_action.can_dispatch,
            current_input_revision=self._resolver.action_input_revision(
                current_action,
                surface,
                facts,
            ),
            storyboard_current=storyboard_current,
            storyboard_can_regenerate=(
                storyboard_available and assets_current and at_or_after_storyboard
            ),
            validation_current=validation_current,
            render_guide_current=render_current,
            next_episode=None,
            next_entry_action=None,
            next_entry_can_dispatch=False,
            project_has_next_episode=False,
            next_input_revision=None,
        )


class StoryWorkspaceMultiEpisodeActionProjector:
    """Build a bounded ordered option list without reading paths or messages."""

    @staticmethod
    def _target(
        descriptor: StoryWorkspaceEpisodeDescriptor,
    ) -> StoryWorkspaceEpisodeActionTarget:
        return StoryWorkspaceEpisodeActionTarget(
            opaqueEpisodeId=descriptor.opaque_episode_id,
            candidateId=descriptor.candidate_id,
            displayLabel=descriptor.display_label,
            relation=descriptor.relation,
        )

    @staticmethod
    def _action_id(
        snapshot: StoryWorkspaceEpisodeActionSnapshot,
        descriptor: StoryWorkspaceEpisodeDescriptor,
        action: StoryWorkspaceEpisodeAction,
        *,
        intent: str,
    ) -> str:
        payload = {
            "action": action.value,
            "input_revision": (
                snapshot.next_input_revision
                if descriptor.relation == "next"
                else snapshot.current_input_revision
            ),
            "intent": intent,
            "relation": descriptor.relation,
            "run_id": snapshot.run_id,
            "target": descriptor.opaque_episode_id or descriptor.candidate_id,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "episode_action_" + hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _label(
        action: StoryWorkspaceEpisodeAction,
        descriptor: StoryWorkspaceEpisodeDescriptor,
        *,
        intent: str,
    ) -> str:
        episode = descriptor.display_label
        labels = {
            StoryWorkspaceEpisodeAction.PLAN_EPISODE: f"开始 {episode} 分集规划",
            StoryWorkspaceEpisodeAction.WRITE_SCRIPT: f"创作 {episode} 剧本",
            StoryWorkspaceEpisodeAction.REVIEW_SCRIPT: f"审阅 {episode} 剧本",
            StoryWorkspaceEpisodeAction.REFRESH_ASSETS: f"核对 {episode} 资产引用",
            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD: (
                f"基于最新剧本更新 {episode} 详细分镜"
                if intent == "update"
                else f"生成 {episode} 详细分镜"
            ),
            StoryWorkspaceEpisodeAction.GENERATE_PROMPTS: f"生成 {episode} Prompt 包",
            StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN: f"审阅 {episode} 完整产物",
            StoryWorkspaceEpisodeAction.VALIDATE_EPISODE: f"校验并提交 {episode}",
            StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE: (
                f"准备 {episode} 渲染与配音指引"
            ),
        }
        return labels[action]

    @staticmethod
    def _description(
        action: StoryWorkspaceEpisodeAction,
        descriptor: StoryWorkspaceEpisodeDescriptor,
        *,
        intent: str,
    ) -> str:
        episode = descriptor.display_label
        descriptions = {
            StoryWorkspaceEpisodeAction.PLAN_EPISODE: (
                f"在当前项目规划中建立或更新 {episode} 分集 outline。"
            ),
            StoryWorkspaceEpisodeAction.WRITE_SCRIPT: (
                f"使用已批准的 {episode} outline 和可信项目上下文创作本集剧本。"
            ),
            StoryWorkspaceEpisodeAction.REVIEW_SCRIPT: (
                f"审阅当前 {episode} script revision 并生成剧本级报告。"
            ),
            StoryWorkspaceEpisodeAction.REFRESH_ASSETS: (
                f"按已审阅剧本核对 {episode} 的角色、场景与道具引用。"
            ),
            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD: (
                f"重建 {episode} 详细分镜；Prompt、完整审阅与校验将需要更新。"
                if intent == "update"
                else f"使用已审阅剧本与最新资产引用生成 {episode} 详细分镜。"
            ),
            StoryWorkspaceEpisodeAction.GENERATE_PROMPTS: (
                f"从 {episode} 当前详细分镜生成逐镜头 Prompt 包。"
            ),
            StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN: (
                f"审查 {episode} 当前 outline、script、storyboard 与 Prompt revisions。"
            ),
            StoryWorkspaceEpisodeAction.VALIDATE_EPISODE: (
                f"按当前完整链路审阅与 canonical revisions 校验 {episode}。"
            ),
            StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE: (
                f"基于已校验的 {episode} 分镜与 Prompt 准备渲染和配音指引。"
            ),
        }
        return descriptions[action]

    @staticmethod
    def _display_command(
        action: StoryWorkspaceEpisodeAction,
        descriptor: StoryWorkspaceEpisodeDescriptor,
    ) -> str:
        episode = descriptor.display_label
        commands = {
            StoryWorkspaceEpisodeAction.PLAN_EPISODE: "/drama-plan",
            StoryWorkspaceEpisodeAction.WRITE_SCRIPT: f"/drama-script ({episode})",
            StoryWorkspaceEpisodeAction.REVIEW_SCRIPT: f"script-reviewer · {episode} 剧本",
            StoryWorkspaceEpisodeAction.REFRESH_ASSETS: "/drama-asset",
            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD: (
                f"/drama-storyboard ({episode})"
            ),
            StoryWorkspaceEpisodeAction.GENERATE_PROMPTS: f"/drama-prompt ({episode})",
            StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN: (
                f"script-reviewer · {episode} 完整链路"
            ),
            StoryWorkspaceEpisodeAction.VALIDATE_EPISODE: f"校验并提交 · {episode}",
            StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE: (
                f"/drama-render + /drama-voice · {episode}"
            ),
        }
        return commands[action]

    @staticmethod
    def _episode_input(
        artifact: str,
        label: str,
        *,
        revision: str | None,
        requirement: str,
        available: bool,
    ) -> StoryWorkspaceEpisodeArtifactCanonicalInput:
        return StoryWorkspaceEpisodeArtifactCanonicalInput(
            artifact=artifact,
            label=label,
            availability="available" if available else "not_generated",
            publicRevision=revision if available else None,
            requirement=requirement,
        )

    @staticmethod
    def _project_input(
        artifact: str,
        label: str,
    ) -> StoryWorkspaceProjectArtifactCanonicalInput:
        return StoryWorkspaceProjectArtifactCanonicalInput(
            artifact=artifact,
            label=label,
            availability="available",
            publicRevision=None,
            requirement="context",
        )

    @classmethod
    def _canonical_inputs(
        cls,
        action: StoryWorkspaceEpisodeAction,
        descriptor: StoryWorkspaceEpisodeDescriptor,
        *,
        revision: str,
        executable: bool,
    ) -> list[object]:
        episode = descriptor.display_label
        project_context = [
            cls._project_input("worldbuilding", "世界观"),
            cls._project_input("character_arc_ledger", "角色弧与连续性台账"),
            StoryWorkspaceAssetContextCanonicalInput(
                label="角色、场景与道具资产",
                availability="current",
                publicRevision=None,
            ),
        ]
        episode_input = lambda artifact, label, requirement="required": cls._episode_input(  # noqa: E731
            artifact,
            label,
            revision=revision,
            requirement=requirement,
            available=executable,
        )
        if action is StoryWorkspaceEpisodeAction.PLAN_EPISODE:
            values: list[object] = [
                cls._project_input("project_definition", "项目定义"),
                cls._project_input("master_outline", "全剧主线"),
                *project_context,
            ]
            if descriptor.relation == "next":
                values.append(StoryWorkspaceWorkflowFactCanonicalInput(
                    fact="prior_episode_validation",
                    label="上一 Episode 校验事实",
                    availability="current" if executable else "missing",
                    publicRevision=revision if executable else None,
                    revisionKind="facts",
                ))
            return values
        if action is StoryWorkspaceEpisodeAction.WRITE_SCRIPT:
            return [episode_input("episode_outline", f"{episode} 分集 outline"), *project_context]
        if action is StoryWorkspaceEpisodeAction.REVIEW_SCRIPT:
            return [
                episode_input("script", f"{episode} 剧本"),
                episode_input("episode_outline", f"{episode} 分集 outline", "context"),
            ]
        if action is StoryWorkspaceEpisodeAction.REFRESH_ASSETS:
            return [
                episode_input("script", f"{episode} 剧本"),
                episode_input("review_report", f"{episode} 剧本审阅"),
                project_context[-1],
            ]
        if action is StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD:
            return [
                episode_input("script", f"{episode} 剧本"),
                episode_input("review_report", f"{episode} 剧本审阅"),
                StoryWorkspaceWorkflowFactCanonicalInput(
                    fact="refresh_assets_completion",
                    label=f"{episode} 资产核对事实",
                    availability="current" if executable else "missing",
                    publicRevision=revision if executable else None,
                    revisionKind="input",
                ),
                project_context[-1],
            ]
        if action is StoryWorkspaceEpisodeAction.GENERATE_PROMPTS:
            return [
                episode_input("storyboard", f"{episode} 详细分镜"),
                episode_input("script", f"{episode} 剧本情绪上下文", "context"),
                project_context[-1],
            ]
        if action is StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN:
            return [
                episode_input("episode_outline", f"{episode} 分集 outline"),
                episode_input("script", f"{episode} 剧本"),
                episode_input("storyboard", f"{episode} 详细分镜"),
                episode_input("prompts", f"{episode} Prompt 包"),
            ]
        if action is StoryWorkspaceEpisodeAction.VALIDATE_EPISODE:
            return [
                episode_input("episode_outline", f"{episode} 分集 outline"),
                episode_input("script", f"{episode} 剧本"),
                episode_input("storyboard", f"{episode} 详细分镜"),
                episode_input("prompts", f"{episode} Prompt 包"),
                episode_input("review_report", f"{episode} 完整链路审阅"),
                StoryWorkspaceWorkflowFactCanonicalInput(
                    fact="full_chain_review",
                    label=f"{episode} 完整链路审阅事实",
                    availability="current" if executable else "missing",
                    publicRevision=revision if executable else None,
                    revisionKind="input",
                ),
            ]
        return [
            episode_input("storyboard", f"{episode} 详细分镜"),
            episode_input("prompts", f"{episode} Prompt 包"),
            episode_input("review_report", f"{episode} 完整链路审阅"),
            StoryWorkspaceWorkflowFactCanonicalInput(
                fact="validation",
                label=f"{episode} 校验事实",
                availability="current" if executable else "missing",
                publicRevision=revision if executable else None,
                revisionKind="facts",
            ),
        ]

    @staticmethod
    def _consequences(
        action: StoryWorkspaceEpisodeAction,
        *,
        intent: str,
    ) -> list[str]:
        if action is StoryWorkspaceEpisodeAction.PLAN_EPISODE:
            return ["剧本及后续产物可能需要更新"]
        if action is StoryWorkspaceEpisodeAction.WRITE_SCRIPT:
            return ["剧本审阅、详细分镜、Prompt 与校验需要更新"]
        if action is StoryWorkspaceEpisodeAction.REVIEW_SCRIPT:
            return ["资产核对与下游产物将使用新的审阅 revision"]
        if action is StoryWorkspaceEpisodeAction.REFRESH_ASSETS:
            return ["详细分镜及下游产物可能需要更新"]
        if action is StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD:
            return (
                ["Prompt 包", "完整产物审阅", "校验提交"]
                if intent == "update"
                else ["Prompt 包与后续审阅尚待生成"]
            )
        if action is StoryWorkspaceEpisodeAction.GENERATE_PROMPTS:
            return ["完整产物审阅与校验需要更新"]
        if action is StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN:
            return ["校验提交需要更新"]
        return []

    @classmethod
    def _option(
        cls,
        snapshot: StoryWorkspaceEpisodeActionSnapshot,
        descriptor: StoryWorkspaceEpisodeDescriptor,
        action: StoryWorkspaceEpisodeAction,
        *,
        availability: StoryWorkspaceEpisodeActionAvailability,
        recommended: bool,
        can_dispatch: bool,
        disabled_reason: str | None,
        intent: str = "advance",
    ) -> StoryWorkspaceEpisodeActionOptionV2:
        return StoryWorkspaceEpisodeActionOptionV2(
            actionId=cls._action_id(snapshot, descriptor, action, intent=intent),
            action=action,
            targetEpisode=cls._target(descriptor),
            label=cls._label(action, descriptor, intent=intent),
            description=cls._description(action, descriptor, intent=intent),
            displayCommand=cls._display_command(action, descriptor),
            availability=availability,
            isRecommended=recommended,
            canDispatch=can_dispatch,
            disabledReason=disabled_reason,
            canonicalInputs=cls._canonical_inputs(
                action,
                descriptor,
                revision=(
                    snapshot.next_input_revision
                    if descriptor.relation == "next"
                    else snapshot.current_input_revision
                ),
                executable=availability is StoryWorkspaceEpisodeActionAvailability.EXECUTABLE,
            ),
            consequences=cls._consequences(action, intent=intent),
            dispatchState=StoryWorkspaceEpisodeActionDispatchState.IDLE,
        )

    @classmethod
    def _current_regeneration(
        cls,
        snapshot: StoryWorkspaceEpisodeActionSnapshot,
    ) -> StoryWorkspaceEpisodeActionOptionV2:
        return cls._option(
            snapshot,
            snapshot.current_episode,
            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
            availability=StoryWorkspaceEpisodeActionAvailability.EXECUTABLE,
            recommended=False,
            can_dispatch=True,
            disabled_reason=None,
            intent="update",
        )

    @classmethod
    def project(
        cls,
        snapshot: StoryWorkspaceEpisodeActionSnapshot,
    ) -> StoryWorkspaceEpisodeActionProjectionV2:
        if (
            snapshot.current_action is StoryWorkspaceEpisodeAction.NONE_IN_SCOPE
            and not snapshot.project_has_next_episode
        ):
            return StoryWorkspaceEpisodeActionProjectionV2()

        options: list[StoryWorkspaceEpisodeActionOptionV2] = []
        next_episode = snapshot.next_episode
        next_action = snapshot.next_entry_action

        if snapshot.validation_current:
            if next_episode is None or next_action is None:
                if snapshot.render_guide_current:
                    return StoryWorkspaceEpisodeActionProjectionV2()
                options.append(cls._option(
                    snapshot,
                    snapshot.current_episode,
                    StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
                    availability=StoryWorkspaceEpisodeActionAvailability.EXECUTABLE,
                    recommended=True,
                    can_dispatch=snapshot.current_can_dispatch,
                    disabled_reason=(
                        None if snapshot.current_can_dispatch else "当前依赖尚未满足"
                    ),
                ))
                if snapshot.storyboard_can_regenerate:
                    options.append(cls._current_regeneration(snapshot))
            else:
                options.append(cls._option(
                    snapshot,
                    next_episode,
                    next_action,
                    availability=StoryWorkspaceEpisodeActionAvailability.EXECUTABLE,
                    recommended=True,
                    can_dispatch=snapshot.next_entry_can_dispatch,
                    disabled_reason=(
                        None if snapshot.next_entry_can_dispatch else "当前依赖尚未满足"
                    ),
                ))
                if snapshot.storyboard_can_regenerate:
                    options.append(cls._current_regeneration(snapshot))
                if not snapshot.render_guide_current:
                    options.append(cls._option(
                        snapshot,
                        snapshot.current_episode,
                        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
                        availability=StoryWorkspaceEpisodeActionAvailability.EXECUTABLE,
                        recommended=False,
                        can_dispatch=True,
                        disabled_reason=None,
                    ))
                successor = {
                    StoryWorkspaceEpisodeAction.PLAN_EPISODE: StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
                    StoryWorkspaceEpisodeAction.WRITE_SCRIPT: StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
                }[next_action]
                options.append(cls._option(
                    snapshot,
                    next_episode,
                    successor,
                    availability=StoryWorkspaceEpisodeActionAvailability.PREVIEW,
                    recommended=False,
                    can_dispatch=False,
                    disabled_reason=f"先完成 {cls._label(next_action, next_episode, intent='advance')}",
                ))
        else:
            start = _VENDOR_ACTIONS.index(snapshot.current_action)
            for offset, action in enumerate(_VENDOR_ACTIONS[start:]):
                if offset == 0:
                    options.append(cls._option(
                        snapshot,
                        snapshot.current_episode,
                        action,
                        availability=StoryWorkspaceEpisodeActionAvailability.EXECUTABLE,
                        recommended=True,
                        can_dispatch=snapshot.current_can_dispatch,
                        disabled_reason=(
                            None if snapshot.current_can_dispatch else "当前依赖尚未满足"
                        ),
                        intent=(
                            "update"
                            if action is StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD
                            and snapshot.storyboard_current
                            else "advance"
                        ),
                    ))
                    if (
                        snapshot.storyboard_can_regenerate
                        and action is not StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD
                        and start > _VENDOR_ACTIONS.index(
                            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD
                        )
                    ):
                        options.append(cls._current_regeneration(snapshot))
                    continue
                options.append(cls._option(
                    snapshot,
                    snapshot.current_episode,
                    action,
                    availability=StoryWorkspaceEpisodeActionAvailability.PREVIEW,
                    recommended=False,
                    can_dispatch=False,
                    disabled_reason=f"完成当前 {snapshot.current_episode.display_label} 步骤后可用",
                ))
            if snapshot.storyboard_current and next_episode is not None and next_action is not None:
                options.append(cls._option(
                    snapshot,
                    next_episode,
                    next_action,
                    availability=StoryWorkspaceEpisodeActionAvailability.BLOCKED,
                    recommended=False,
                    can_dispatch=False,
                    disabled_reason=(
                        f"完成 {snapshot.current_episode.display_label} 完整产物校验后可用"
                    ),
                ))
                successor = {
                    StoryWorkspaceEpisodeAction.PLAN_EPISODE: StoryWorkspaceEpisodeAction.WRITE_SCRIPT,
                    StoryWorkspaceEpisodeAction.WRITE_SCRIPT: StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
                }[next_action]
                options.append(cls._option(
                    snapshot,
                    next_episode,
                    successor,
                    availability=StoryWorkspaceEpisodeActionAvailability.PREVIEW,
                    recommended=False,
                    can_dispatch=False,
                    disabled_reason=f"先完成 {cls._label(next_action, next_episode, intent='advance')}",
                ))

        return StoryWorkspaceEpisodeActionProjectionV2(
            recommendedActionId=options[0].action_id if options else None,
            actionOptions=options,
        )


__all__ = [
    "StoryWorkspaceCurrentEpisodeActionSnapshotBuilder",
    "StoryWorkspaceEpisodeActionSnapshot",
    "StoryWorkspaceEpisodeDescriptor",
    "StoryWorkspaceEpisodeRegistryActionContext",
    "StoryWorkspaceMultiEpisodeActionProjector",
    "StoryWorkspaceNextEpisodeActionPlanner",
]
