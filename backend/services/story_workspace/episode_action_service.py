"""Evidence-derived Episode actions dispatched through the Dream message seam."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from typing import Any, Callable, Mapping
from uuid import uuid4

from pydantic import ValidationError

try:
    from services.story_workspace.dream_agent_message_service import (
        STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        StoryWorkspaceDreamAgentMessageService,
        StoryWorkspaceDreamAgentPendingDispatch,
    )
    from services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingService,
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
        StoryWorkspaceEpisodeWorkflowCompletion,
        StoryWorkspaceEpisodeWorkflowFile,
        StoryWorkspaceEpisodeWorkflowProjection,
    )
except ModuleNotFoundError:  # Support repository-root package imports.
    from backend.services.story_workspace.dream_agent_message_service import (
        STORY_WORKSPACE_DREAM_AGENT_USER_KIND,
        StoryWorkspaceDreamAgentMessageService,
        StoryWorkspaceDreamAgentPendingDispatch,
    )
    from backend.services.story_workspace.episode_binding_service import (
        StoryWorkspaceEpisodeBindingService,
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
        StoryWorkspaceEpisodeWorkflowCompletion,
        StoryWorkspaceEpisodeWorkflowFile,
        StoryWorkspaceEpisodeWorkflowProjection,
    )


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

@dataclass(frozen=True)
class StoryWorkspaceEpisodeVendorStep:
    """Server-private README evidence and the reviewed product boundary."""

    ordinal: int
    evidence: str
    action: StoryWorkspaceEpisodeAction | None
    boundary: str


_VENDOR_FIRST_EPISODE_FLOW = (
    StoryWorkspaceEpisodeVendorStep(1, "/drama-init", None, "initial_creation"),
    StoryWorkspaceEpisodeVendorStep(
        2, "/drama-plan", StoryWorkspaceEpisodeAction.PLAN_EPISODE, "episode_execution"
    ),
    StoryWorkspaceEpisodeVendorStep(
        3, "/drama-script (EP01)", StoryWorkspaceEpisodeAction.WRITE_SCRIPT, "episode_execution"
    ),
    StoryWorkspaceEpisodeVendorStep(
        4, "script-reviewer 审查", StoryWorkspaceEpisodeAction.REVIEW_SCRIPT, "episode_execution"
    ),
    StoryWorkspaceEpisodeVendorStep(
        5, "/drama-asset", StoryWorkspaceEpisodeAction.REFRESH_ASSETS, "episode_execution"
    ),
    StoryWorkspaceEpisodeVendorStep(
        6,
        "/drama-storyboard (EP01)",
        StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        7, "/drama-prompt (EP01)", StoryWorkspaceEpisodeAction.GENERATE_PROMPTS, "episode_execution"
    ),
    StoryWorkspaceEpisodeVendorStep(
        8,
        "[审查报告: APPROVED]",
        StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
        "episode_execution",
    ),
    StoryWorkspaceEpisodeVendorStep(
        9, "validate_commit.sh", StoryWorkspaceEpisodeAction.VALIDATE_EPISODE, "episode_execution"
    ),
    StoryWorkspaceEpisodeVendorStep(
        10,
        "/drama-render + /drama-voice",
        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
        "render_guide_only",
    ),
    StoryWorkspaceEpisodeVendorStep(11, "/drama-edit", None, "out_of_scope"),
    StoryWorkspaceEpisodeVendorStep(12, "/drama-promote", None, "out_of_scope"),
)


def story_workspace_episode_vendor_workflow(
) -> tuple[StoryWorkspaceEpisodeVendorStep, ...]:
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
    """In-memory compatibility input; never loaded from launch metadata."""

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

class StoryWorkspaceEpisodeWorkflowFactError(RuntimeError):
    """A workflow fact file failed validation, containment, or CAS."""


class StoryWorkspaceEpisodeWorkflowFactConflict(
    StoryWorkspaceEpisodeWorkflowFactError
):
    """The caller did not write against the latest technical fact revision."""


class StoryWorkspaceEpisodeWorkflowFactService:
    """Read and CAS-write run-scoped technical completion evidence."""

    _MAX_BYTES = 64 * 1024

    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        self._binding_service = StoryWorkspaceEpisodeBindingService(workspace_root)

    @staticmethod
    def _default(
        workflow_run_id: str,
        episode_uid: str,
    ) -> StoryWorkspaceEpisodeWorkflowFile:
        return StoryWorkspaceEpisodeWorkflowFile(
            workflow_run_id=workflow_run_id,
            episode_uid=episode_uid,
            revision=0,
            completions=[],
            updated_at=datetime.now(UTC),
        )

    @classmethod
    def _read_from_run(
        cls,
        run_descriptor: int,
        *,
        workflow_run_id: str,
        episode_uid: str,
    ) -> StoryWorkspaceEpisodeWorkflowFile:
        try:
            descriptor = os.open(
                "episode-workflow.json",
                os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                dir_fd=run_descriptor,
            )
        except FileNotFoundError:
            return cls._default(workflow_run_id, episode_uid)
        except OSError as exc:
            raise StoryWorkspaceEpisodeWorkflowFactError(
                "workflow facts cannot be opened safely"
            ) from exc
        try:
            pinned = os.fstat(descriptor)
            visible = os.stat(
                "episode-workflow.json",
                dir_fd=run_descriptor,
                follow_symlinks=False,
            )
            if (
                not stat.S_ISREG(pinned.st_mode)
                or stat.S_ISLNK(visible.st_mode)
                or not stat.S_ISREG(visible.st_mode)
                or (pinned.st_dev, pinned.st_ino) != (visible.st_dev, visible.st_ino)
                or pinned.st_size > cls._MAX_BYTES
            ):
                raise StoryWorkspaceEpisodeWorkflowFactError(
                    "workflow facts file is unsafe"
                )
            payload = bytearray()
            while len(payload) <= cls._MAX_BYTES:
                chunk = os.read(descriptor, min(8192, cls._MAX_BYTES + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
            if len(payload) > cls._MAX_BYTES:
                raise StoryWorkspaceEpisodeWorkflowFactError(
                    "workflow facts exceed the size limit"
                )
        except OSError as exc:
            raise StoryWorkspaceEpisodeWorkflowFactError(
                "workflow facts cannot be read safely"
            ) from exc
        finally:
            os.close(descriptor)
        try:
            facts = StoryWorkspaceEpisodeWorkflowFile.model_validate_json(payload)
        except (ValidationError, ValueError) as exc:
            raise StoryWorkspaceEpisodeWorkflowFactError(
                "workflow facts violate dream-episode-workflow/v1"
            ) from exc
        if (
            facts.workflow_run_id != workflow_run_id
            or facts.episode_uid != episode_uid
        ):
            raise StoryWorkspaceEpisodeWorkflowFactError(
                "workflow facts identity does not match the authorized Episode"
            )
        return facts

    def read(
        self,
        workflow_run_id: str,
        episode_uid: str,
    ) -> StoryWorkspaceEpisodeWorkflowFile:
        with self._binding_service._locked_run_directory(  # noqa: SLF001
            workflow_run_id
        ) as run_descriptor:
            return self._read_from_run(
                run_descriptor,
                workflow_run_id=workflow_run_id,
                episode_uid=episode_uid,
            )

    @staticmethod
    def _same_completion(
        completion: StoryWorkspaceEpisodeWorkflowCompletion,
        *,
        action: StoryWorkspaceEpisodeAction,
        input_revision: str,
        manifest_revision: str,
        message_id: str,
    ) -> bool:
        return (
            completion.action is action
            and completion.input_revision == input_revision
            and completion.manifest_revision == manifest_revision
            and completion.message_id == message_id
        )

    @staticmethod
    def _write(
        run_descriptor: int,
        facts: StoryWorkspaceEpisodeWorkflowFile,
    ) -> None:
        temporary_name = f".episode-workflow.{uuid4().hex}.tmp"
        descriptor = -1
        try:
            descriptor = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | os.O_NOFOLLOW
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=run_descriptor,
            )
            payload = (facts.model_dump_json() + "\n").encode("utf-8")
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short workflow facts write")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            os.replace(
                temporary_name,
                "episode-workflow.json",
                src_dir_fd=run_descriptor,
                dst_dir_fd=run_descriptor,
            )
            os.fsync(run_descriptor)
        except OSError as exc:
            raise StoryWorkspaceEpisodeWorkflowFactError(
                "workflow facts cannot be committed safely"
            ) from exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary_name, dir_fd=run_descriptor)
            except OSError:
                pass

    def record_completion(
        self,
        *,
        workflow_run_id: str,
        episode_uid: str,
        action: StoryWorkspaceEpisodeAction,
        input_revision: str,
        manifest_revision: str,
        message_id: str,
        expected_revision: int,
    ) -> StoryWorkspaceEpisodeWorkflowFile:
        completion = StoryWorkspaceEpisodeWorkflowCompletion(
            action=action,
            input_revision=input_revision,
            manifest_revision=manifest_revision,
            message_id=message_id,
            recorded_at=datetime.now(UTC),
        )
        with self._binding_service._locked_run_directory(  # noqa: SLF001
            workflow_run_id
        ) as run_descriptor:
            current = self._read_from_run(
                run_descriptor,
                workflow_run_id=workflow_run_id,
                episode_uid=episode_uid,
            )
            existing = next(
                (item for item in current.completions if item.action is action),
                None,
            )
            if existing is not None and self._same_completion(
                existing,
                action=action,
                input_revision=input_revision,
                manifest_revision=manifest_revision,
                message_id=message_id,
            ):
                return current
            if current.revision != expected_revision:
                raise StoryWorkspaceEpisodeWorkflowFactConflict(
                    "workflow facts revision changed"
                )
            completions = [
                item for item in current.completions if item.action is not action
            ]
            completions.append(completion)
            completions.sort(key=lambda item: item.action.value)
            updated = StoryWorkspaceEpisodeWorkflowFile(
                workflow_run_id=workflow_run_id,
                episode_uid=episode_uid,
                revision=current.revision + 1,
                completions=completions,
                updated_at=completion.recorded_at,
            )
            self._write(run_descriptor, updated)
            return updated


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
        *,
        can_dispatch: bool | None = None,
    ) -> StoryWorkspaceEpisodeActionResolution:
        return StoryWorkspaceEpisodeActionResolution(
            action=action,
            diagnostic=diagnostic,
            canDispatch=(
                action is not StoryWorkspaceEpisodeAction.NONE_IN_SCOPE
                if can_dispatch is None
                else can_dispatch
            ),
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

    @classmethod
    def action_input_revision(
        cls,
        action: StoryWorkspaceEpisodeAction,
        surface: object,
        facts: StoryWorkspaceEpisodeWorkflowFile,
    ) -> str:
        """Hash only canonical inputs and earlier technical completion facts."""

        artifacts = cls._artifact_map(surface)
        keys = {
            StoryWorkspaceEpisodeAction.PLAN_EPISODE: (),
            StoryWorkspaceEpisodeAction.WRITE_SCRIPT: ("episode-outline.md",),
            StoryWorkspaceEpisodeAction.REVIEW_SCRIPT: ("script.md",),
            StoryWorkspaceEpisodeAction.REFRESH_ASSETS: (
                "script.md",
                "review-report.md",
            ),
            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD: (
                "script.md",
                "review-report.md",
            ),
            StoryWorkspaceEpisodeAction.GENERATE_PROMPTS: ("storyboard.yaml",),
            StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN: (
                "episode-outline.md",
                "script.md",
                "storyboard.yaml",
                "prompts/",
            ),
            StoryWorkspaceEpisodeAction.VALIDATE_EPISODE: (
                "episode-outline.md",
                "script.md",
                "storyboard.yaml",
                "prompts/",
                "review-report.md",
            ),
            StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE: (
                "episode-outline.md",
                "script.md",
                "storyboard.yaml",
                "prompts/",
                "review-report.md",
            ),
            StoryWorkspaceEpisodeAction.NONE_IN_SCOPE: (),
        }[action]
        earlier = {
            StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD: (
                StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
            ),
            StoryWorkspaceEpisodeAction.VALIDATE_EPISODE: (
                StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
            ),
            StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE: (
                StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
            ),
        }.get(action, ())
        completion_map = {item.action: item for item in facts.completions}
        payload = {
            "action": action.value,
            "artifacts": [
                [
                    key,
                    getattr(artifacts.get(key), "availability", None).value
                    if getattr(artifacts.get(key), "availability", None) is not None
                    else None,
                    getattr(artifacts.get(key), "content_revision", None),
                ]
                for key in keys
            ],
            "earlier": [
                [
                    item.value,
                    getattr(completion_map.get(item), "input_revision", None),
                    getattr(completion_map.get(item), "manifest_revision", None),
                ]
                for item in earlier
            ],
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _completion_is_current(
        cls,
        action: StoryWorkspaceEpisodeAction,
        surface: object,
        facts: StoryWorkspaceEpisodeWorkflowFile,
    ) -> bool:
        completion = next(
            (item for item in facts.completions if item.action is action),
            None,
        )
        return (
            completion is not None
            and completion.input_revision
            == cls.action_input_revision(action, surface, facts)
        )

    @classmethod
    def project(
        cls,
        surface: object,
        facts: StoryWorkspaceEpisodeWorkflowFile,
    ) -> StoryWorkspaceEpisodeWorkflowProjection:
        """Derive navigation without making completion facts creative owners."""

        artifacts = cls._artifact_map(surface)
        outline = artifacts.get("episode-outline.md")
        script = artifacts.get("script.md")
        storyboard = artifacts.get("storyboard.yaml")
        prompts = artifacts.get("prompts/")
        renders = artifacts.get("renders/")
        report = artifacts.get("review-report.md")
        order = [
            step.action
            for step in _VENDOR_FIRST_EPISODE_FLOW
            if step.action is not None
        ]
        review = cls._review(surface)
        invalid_actions = (
            (outline, StoryWorkspaceEpisodeAction.PLAN_EPISODE),
            (script, StoryWorkspaceEpisodeAction.WRITE_SCRIPT),
            (
                report,
                (
                    StoryWorkspaceEpisodeAction.REVIEW_SCRIPT
                    if getattr(review, "scope", None)
                    is StoryWorkspaceEpisodeReviewScope.SCRIPT
                    else StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN
                ),
            ),
            (storyboard, StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD),
            (prompts, StoryWorkspaceEpisodeAction.GENERATE_PROMPTS),
            (renders, StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE),
        )
        invalid_action = next(
            (
                action
                for item, action in invalid_actions
                if cls._availability(item)
                is StoryWorkspaceEpisodeArtifactAvailability.INVALID
            ),
            None,
        )
        if invalid_action is not None:
            later_available = any(
                cls._available(artifacts.get(key))
                for key in ("storyboard.yaml", "prompts/", "renders/")
            )
            return StoryWorkspaceEpisodeWorkflowProjection(
                factsRevision=facts.revision,
                nextAction=cls._resolution(
                    invalid_action,
                    StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                    can_dispatch=False,
                ),
                prerequisites=order[: order.index(invalid_action)],
                legacyPartial=(
                    later_available
                    and (not cls._available(outline) or not cls._available(script))
                ),
            )

        def blocked_or_ready(
            action: StoryWorkspaceEpisodeAction,
            item: object | None,
        ) -> StoryWorkspaceEpisodeActionResolution:
            invalid = (
                cls._availability(item)
                is StoryWorkspaceEpisodeArtifactAvailability.INVALID
            )
            return cls._resolution(
                action,
                (
                    StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION
                    if invalid
                    else StoryWorkspaceEpisodeActionDiagnostic.READY
                ),
                can_dispatch=not invalid,
            )

        if not cls._available(outline):
            resolution = blocked_or_ready(StoryWorkspaceEpisodeAction.PLAN_EPISODE, outline)
        elif not cls._available(script):
            resolution = blocked_or_ready(StoryWorkspaceEpisodeAction.WRITE_SCRIPT, script)
        else:
            script_revision = cls._revision(script)
            script_review_current = (
                getattr(review, "scope", None)
                in {
                    StoryWorkspaceEpisodeReviewScope.SCRIPT,
                    StoryWorkspaceEpisodeReviewScope.FULL_CHAIN,
                }
                and cls._reviewed_revision(review, "script.md") == script_revision
                and (
                    getattr(review, "scope", None)
                    is StoryWorkspaceEpisodeReviewScope.FULL_CHAIN
                    or getattr(review, "overall_verdict", None) == "APPROVED"
                )
            )
            if not script_review_current:
                resolution = blocked_or_ready(
                    StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
                    report,
                )
                if cls._available(report):
                    resolution = cls._resolution(
                        StoryWorkspaceEpisodeAction.REVIEW_SCRIPT,
                        StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                        can_dispatch=(
                            getattr(review, "scope", None)
                            is StoryWorkspaceEpisodeReviewScope.SCRIPT
                        ),
                    )
            elif not cls._completion_is_current(
                StoryWorkspaceEpisodeAction.REFRESH_ASSETS, surface, facts
            ):
                resolution = cls._resolution(
                    StoryWorkspaceEpisodeAction.REFRESH_ASSETS,
                    StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                )
            elif not cls._available(storyboard):
                resolution = blocked_or_ready(
                    StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
                    storyboard,
                )
            elif not cls._completion_is_current(
                StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD, surface, facts
            ):
                resolution = cls._resolution(
                    StoryWorkspaceEpisodeAction.REGENERATE_STORYBOARD,
                    StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                )
            elif not cls._available(prompts):
                resolution = blocked_or_ready(
                    StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
                    prompts,
                )
            elif not cls._completion_is_current(
                StoryWorkspaceEpisodeAction.GENERATE_PROMPTS, surface, facts
            ):
                resolution = cls._resolution(
                    StoryWorkspaceEpisodeAction.GENERATE_PROMPTS,
                    StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                )
            else:
                full_chain_current = (
                    getattr(review, "scope", None)
                    is StoryWorkspaceEpisodeReviewScope.FULL_CHAIN
                    and getattr(review, "overall_verdict", None) == "APPROVED"
                    and cls._reviewed_revision(review, "script.md")
                    == cls._revision(script)
                    and cls._reviewed_revision(review, "storyboard.yaml")
                    == cls._revision(storyboard)
                )
                if not full_chain_current:
                    invalid = (
                        cls._availability(report)
                        is StoryWorkspaceEpisodeArtifactAvailability.INVALID
                    )
                    resolution = cls._resolution(
                        StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
                        (
                            StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION
                            if cls._available(report) or invalid
                            else StoryWorkspaceEpisodeActionDiagnostic.READY
                        ),
                        can_dispatch=not invalid,
                    )
                elif not cls._completion_is_current(
                    StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN, surface, facts
                ):
                    resolution = cls._resolution(
                        StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
                        StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                    )
                elif not cls._completion_is_current(
                    StoryWorkspaceEpisodeAction.VALIDATE_EPISODE, surface, facts
                ):
                    resolution = cls._resolution(
                        StoryWorkspaceEpisodeAction.VALIDATE_EPISODE,
                        StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                    )
                elif not cls._available(renders):
                    resolution = blocked_or_ready(
                        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
                        renders,
                    )
                elif not cls._completion_is_current(
                    StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
                    surface,
                    facts,
                ):
                    resolution = cls._resolution(
                        StoryWorkspaceEpisodeAction.PREPARE_RENDER_GUIDE,
                        StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION,
                    )
                else:
                    resolution = cls._resolution(
                        StoryWorkspaceEpisodeAction.NONE_IN_SCOPE,
                        StoryWorkspaceEpisodeActionDiagnostic.READY,
                    )

        next_index = (
            order.index(resolution.action)
            if resolution.action in order
            else len(order)
        )
        later_available = any(
            cls._available(artifacts.get(key))
            for key in ("storyboard.yaml", "prompts/", "renders/")
        )
        legacy_partial = (
            later_available
            and (not cls._available(outline) or not cls._available(script))
        )
        return StoryWorkspaceEpisodeWorkflowProjection(
            factsRevision=facts.revision,
            nextAction=resolution,
            prerequisites=order[:next_index],
            legacyPartial=legacy_partial,
        )

    @staticmethod
    def surface_etag(
        manifest_revision: str,
        workflow: StoryWorkspaceEpisodeWorkflowProjection,
    ) -> str:
        payload = [
            manifest_revision,
            workflow.model_dump(mode="json", by_alias=True),
        ]
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

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
                can_dispatch=(
                    self._availability(outline)
                    is not StoryWorkspaceEpisodeArtifactAvailability.INVALID
                ),
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
            or getattr(review, "overall_verdict", None) != "APPROVED"
            or facts.full_chain_review_input_revision != full_chain_revision
        ):
            invalid_report = (
                self._availability(report)
                is StoryWorkspaceEpisodeArtifactAvailability.INVALID
            )
            return self._resolution(
                StoryWorkspaceEpisodeAction.REVIEW_FULL_CHAIN,
                (
                    StoryWorkspaceEpisodeActionDiagnostic.READY
                    if review_scope is StoryWorkspaceEpisodeReviewScope.SCRIPT
                    else StoryWorkspaceEpisodeActionDiagnostic.NEEDS_CONFIRMATION
                ),
                can_dispatch=not invalid_report,
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
        workflow_revision: str | None,
        manifest_revision: str | None,
        facts_revision: int | None,
        input_revision: str | None,
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
        provenance = {
            "schema": "story-workspace-episode-action/v1",
            "action": (
                capability.value
                if isinstance(capability, StoryWorkspaceEpisodeAction)
                else capability
            ),
            "episode_uid": episode_id,
            "input_revision": input_revision,
            "expected_facts_revision": facts_revision,
            "expected_manifest_revision": manifest_revision,
            "expected_workflow_revision": workflow_revision,
        }
        row = self._db.execute(
            "SELECT metadata FROM chat_message WHERE id = ?",
            (accepted.message_id,),
        ).fetchone()
        if row is None:
            raise StoryWorkspaceEpisodeActionError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                503,
            )
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except (TypeError, ValueError) as exc:
            raise StoryWorkspaceEpisodeActionError(
                "DECK_RUNTIME_CONFIG_UNAVAILABLE",
                503,
            ) from exc
        existing = metadata.get("story_workspace_episode_action")
        if existing is not None and existing != provenance:
            raise StoryWorkspaceEpisodeActionError("IDEMPOTENCY_CONFLICT", 409)
        if existing is None:
            previous = row["metadata"]
            metadata["story_workspace_episode_action"] = provenance
            updated = self._db.execute(
                "UPDATE chat_message SET metadata = ? WHERE id = ? AND metadata = ?",
                (
                    json.dumps(
                        metadata,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    accepted.message_id,
                    previous,
                ),
            )
            if updated.rowcount != 1:
                self._db.rollback()
                raced = self._db.execute(
                    "SELECT metadata FROM chat_message WHERE id = ?",
                    (accepted.message_id,),
                ).fetchone()
                try:
                    raced_metadata = json.loads(raced["metadata"] or "{}")
                except (TypeError, ValueError, KeyError) as exc:
                    raise StoryWorkspaceEpisodeActionError(
                        "DREAM_AGENT_MESSAGE_BUSY",
                        409,
                    ) from exc
                if raced_metadata.get("story_workspace_episode_action") != provenance:
                    raise StoryWorkspaceEpisodeActionError(
                        "DREAM_AGENT_MESSAGE_BUSY",
                        409,
                    )
            else:
                self._db.commit()
            if pending is not None:
                pending.metadata["story_workspace_episode_action"] = provenance
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
            workflow_revision=None,
            manifest_revision=None,
            facts_revision=None,
            input_revision=None,
            text=self._recover_text(),
        )

    def continue_episode(
        self,
        *,
        run_id: str,
        actor_id: str,
        context: StoryWorkspaceDreamRunContext,
        surface: object,
        action_facts: StoryWorkspaceEpisodeActionFacts
        | StoryWorkspaceEpisodeWorkflowFile,
        if_match: str,
        command: StoryWorkspaceEpisodeActionContinueCommand,
    ) -> tuple[
        StoryWorkspaceEpisodeActionAccepted,
        StoryWorkspaceDreamAgentPendingDispatch | None,
    ]:
        manifest_revision = getattr(surface, "manifest_revision", None)
        surface_revision = getattr(surface, "etag", None) or manifest_revision
        action_input_revision = (
            self._resolver.action_input_revision(
                command.action,
                surface,
                action_facts,
            )
            if isinstance(action_facts, StoryWorkspaceEpisodeWorkflowFile)
            else None
        )
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
                workflow_revision=surface_revision,
                manifest_revision=manifest_revision,
                facts_revision=(
                    action_facts.revision
                    if isinstance(action_facts, StoryWorkspaceEpisodeWorkflowFile)
                    else None
                ),
                input_revision=action_input_revision,
                text=replay_text,
            )
        if (
            not isinstance(surface_revision, str)
            or if_match != f'"{surface_revision}"'
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
        resolution = (
            self._resolver.project(surface, action_facts).next_action
            if isinstance(action_facts, StoryWorkspaceEpisodeWorkflowFile)
            else self._resolver.resolve(surface, action_facts)
        )
        if not resolution.can_dispatch or resolution.action is not command.action:
            raise StoryWorkspaceEpisodeActionError(
                "BINDING_REVISION_CONFLICT",
                409,
                latest_surface=surface,
                resolution=resolution,
            )
        text = self._continue_text(
            command,
            manifest_revision=surface_revision,
        )
        return self._claim(
            run_id=run_id,
            actor_id=actor_id,
            context=context,
            key=command.idempotency_key,
            capability=command.action,
            episode_id=command.episode_id,
            workflow_revision=surface_revision,
            manifest_revision=manifest_revision,
            facts_revision=(
                action_facts.revision
                if isinstance(action_facts, StoryWorkspaceEpisodeWorkflowFile)
                else None
            ),
            input_revision=action_input_revision,
            text=text,
        )


__all__ = [
    "StoryWorkspaceEpisodeActionError",
    "StoryWorkspaceEpisodeActionFacts",
    "StoryWorkspaceEpisodeActionService",
    "StoryWorkspaceEpisodeNextActionResolver",
    "StoryWorkspaceEpisodeVendorStep",
    "StoryWorkspaceEpisodeWorkflowFactConflict",
    "StoryWorkspaceEpisodeWorkflowFactError",
    "StoryWorkspaceEpisodeWorkflowFactService",
    "story_workspace_episode_vendor_workflow",
]
