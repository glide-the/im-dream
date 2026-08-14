# [Input] Versioned Dream workbench/asset Markdown, server-resolved Run context, and one server-owned Thread workspace.
# [Output] Initialized/refreshed `.dream` Agent contracts plus a bounded per-turn context block with actual paths.
# [Pos] Story Workspace domain context contract; not an Agent runtime, Hook, or protocol.
# [Sync] 2026-08-14: deploy workbench and asset-collaboration contracts and require both actual-path Reads every Dream turn.

"""Materialize and render the canonical Dream workbench context.

The static contract lives beside this module as reviewed Markdown.  The Dream
surface initializer copies it into the host-owned ``.dream`` directory, and
the service refreshes server-trusted facts during every Dream context assembly.
The actual validated file path is injected into the internal Agent message;
the public Claude Agent request schema remains unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from story_workspace.contracts import StoryWorkspaceDreamRunContext


DREAM_WORKBENCH_CONTEXT_RELATIVE_PATH = Path(".dream") / "WORKBENCH.md"
DREAM_WORKBENCH_CONTEXT_SOURCE_PATH = Path(__file__).with_name(
    "dream_workbench_context.md"
)
DREAM_ASSET_COLLABORATION_RELATIVE_PATH = (
    Path(".dream") / "ASSET-COLLABORATION.md"
)
DREAM_ASSET_COLLABORATION_SOURCE_PATH = Path(__file__).with_name(
    "dream_asset_collaboration.md"
)
_STORY_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EPISODE_CODE = re.compile(r"^EP[0-9]{2}$")
_CONTEXT_FILE_MAX_BYTES = 128 * 1024


class DreamWorkbenchContextError(RuntimeError):
    """The host could not safely materialize Dream workbench context."""


@dataclass(frozen=True)
class DreamWorkbenchTurnContext:
    """Bounded server facts injected into one canonical Chat/Dream turn."""

    instruction: str
    workspace_file: str
    asset_collaboration_file: str
    project_slug: str | None
    episode_codes: tuple[str, ...]


def _load_reviewed_contract(source: Path, *, label: str) -> str:
    """Load one bounded, regular UTF-8 Agent contract."""

    try:
        metadata = source.lstat()
    except OSError as exc:
        raise DreamWorkbenchContextError(
            f"Dream {label} source contract is unavailable"
        ) from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise DreamWorkbenchContextError(
            f"Dream {label} source contract is unsafe"
        )
    if metadata.st_size > _CONTEXT_FILE_MAX_BYTES:
        raise DreamWorkbenchContextError(
            f"Dream {label} source contract is too large"
        )
    try:
        content = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DreamWorkbenchContextError(
            f"Dream {label} source contract cannot be read"
        ) from exc
    if not content.strip():
        raise DreamWorkbenchContextError(
            f"Dream {label} source contract is blank"
        )
    return content.rstrip() + "\n"


def load_dream_workbench_contract() -> str:
    """Load the reviewed workbench location/lifecycle contract."""

    return _load_reviewed_contract(
        DREAM_WORKBENCH_CONTEXT_SOURCE_PATH,
        label="workbench",
    )


def load_dream_asset_collaboration_contract() -> str:
    """Load the reviewed character/scene/storyboard mutation contract."""

    return _load_reviewed_contract(
        DREAM_ASSET_COLLABORATION_SOURCE_PATH,
        label="asset collaboration",
    )


class DreamWorkbenchContext:
    """Deploy the workbench contract and render current server-owned facts."""

    def initialize_surface(self, dream_root: str | Path) -> str:
        """Install the static contract once as part of Dream surface init."""

        candidate = Path(dream_root)
        try:
            visible = candidate.lstat()
            resolved = candidate.resolve(strict=True)
            metadata = resolved.stat(follow_symlinks=False)
        except (OSError, RuntimeError) as exc:
            raise DreamWorkbenchContextError(
                "Dream surface is unavailable during context initialization"
            ) from exc
        if stat.S_ISLNK(visible.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise DreamWorkbenchContextError("Dream surface is unsafe")

        workbench = resolved / DREAM_WORKBENCH_CONTEXT_RELATIVE_PATH.name
        asset_collaboration = (
            resolved / DREAM_ASSET_COLLABORATION_RELATIVE_PATH.name
        )
        self._initialize_contract_file(
            resolved,
            target=workbench,
            payload=load_dream_workbench_contract().encode("utf-8"),
            label="workbench context",
        )
        self._initialize_contract_file(
            resolved,
            target=asset_collaboration,
            payload=load_dream_asset_collaboration_contract().encode("utf-8"),
            label="asset collaboration context",
        )
        return str(workbench)

    @classmethod
    def _initialize_contract_file(
        cls,
        dream_root: Path,
        *,
        target: Path,
        payload: bytes,
        label: str,
    ) -> None:
        try:
            target_metadata = target.lstat()
        except FileNotFoundError:
            target_metadata = None
        except OSError as exc:
            raise DreamWorkbenchContextError(
                f"Dream {label} cannot be inspected"
            ) from exc
        if target_metadata is not None:
            if stat.S_ISLNK(target_metadata.st_mode) or not stat.S_ISREG(
                target_metadata.st_mode
            ):
                raise DreamWorkbenchContextError(
                    f"Dream {label} file is unsafe"
                )
            return
        cls._replace_context_file(
            dream_root,
            target_name=target.name,
            temporary_prefix=target.name,
            payload=payload,
            label=label,
        )

    @staticmethod
    def _safe_workspace(workspace_root: str | Path, thread_id: str) -> Path:
        candidate = Path(workspace_root)
        try:
            visible = candidate.lstat()
            resolved = candidate.resolve(strict=True)
            metadata = resolved.stat(follow_symlinks=False)
        except (OSError, RuntimeError) as exc:
            raise DreamWorkbenchContextError("Dream workspace is unavailable") from exc
        if (
            stat.S_ISLNK(visible.st_mode)
            or not stat.S_ISDIR(metadata.st_mode)
            or resolved.name != thread_id
        ):
            raise DreamWorkbenchContextError("Dream workspace does not match thread")
        return resolved

    @staticmethod
    def _discover_projects(workspace: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
        stories = workspace / "stories"
        if not stories.exists():
            return ()
        if stories.is_symlink() or not stories.is_dir():
            raise DreamWorkbenchContextError("canonical stories directory is unsafe")
        projects: list[tuple[str, tuple[str, ...]]] = []
        try:
            story_entries = sorted(stories.iterdir())
        except OSError as exc:
            raise DreamWorkbenchContextError(
                "canonical stories directory cannot be inspected"
            ) from exc
        for story in story_entries:
            if (
                story.is_symlink()
                or not story.is_dir()
                or _STORY_SLUG.fullmatch(story.name) is None
            ):
                continue
            project_file = story / "project.yaml"
            try:
                project_metadata = project_file.lstat()
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise DreamWorkbenchContextError(
                    "canonical project file cannot be inspected"
                ) from exc
            if stat.S_ISLNK(project_metadata.st_mode) or not stat.S_ISREG(
                project_metadata.st_mode
            ):
                raise DreamWorkbenchContextError(
                    "canonical project file is unsafe"
                )
            episodes_dir = story / "episodes"
            episodes: tuple[str, ...] = ()
            if episodes_dir.exists():
                if episodes_dir.is_symlink() or not episodes_dir.is_dir():
                    raise DreamWorkbenchContextError(
                        "canonical Episode directory is unsafe"
                    )
                try:
                    episodes = tuple(
                        entry.name
                        for entry in sorted(episodes_dir.iterdir())
                        if not entry.is_symlink()
                        and entry.is_dir()
                        and _EPISODE_CODE.fullmatch(entry.name) is not None
                    )
                except OSError as exc:
                    raise DreamWorkbenchContextError(
                        "canonical Episode directory cannot be inspected"
                    ) from exc
            projects.append((story.name, episodes))
        if len(projects) > 1:
            raise DreamWorkbenchContextError(
                "Dream workspace has multiple canonical projects"
            )
        return tuple(projects)

    @staticmethod
    def _replace_context_file(
        dream_root: Path,
        *,
        target_name: str,
        temporary_prefix: str,
        payload: bytes,
        label: str,
    ) -> None:
        if len(payload) > _CONTEXT_FILE_MAX_BYTES:
            raise DreamWorkbenchContextError(f"Dream {label} is too large")
        target = dream_root / target_name
        try:
            target_metadata = target.lstat()
        except FileNotFoundError:
            target_metadata = None
        except OSError as exc:
            raise DreamWorkbenchContextError(
                f"Dream {label} cannot be inspected"
            ) from exc
        if target_metadata is not None:
            if stat.S_ISLNK(target_metadata.st_mode) or not stat.S_ISREG(
                target_metadata.st_mode
            ):
                raise DreamWorkbenchContextError(
                    f"Dream {label} file is unsafe"
                )
            if target_metadata.st_size > _CONTEXT_FILE_MAX_BYTES:
                raise DreamWorkbenchContextError(
                    f"Dream {label} file is too large"
                )
            try:
                if target.read_bytes() == payload:
                    return
            except OSError as exc:
                raise DreamWorkbenchContextError(
                    f"Dream {label} cannot be read"
                ) from exc
        temporary = dream_root / f".{temporary_prefix}.{uuid4().hex}.tmp"
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            directory = os.open(dream_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError as exc:
            raise DreamWorkbenchContextError(
                f"Dream {label} cannot be committed"
            ) from exc
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def refresh_for_turn(
        self,
        *,
        context: StoryWorkspaceDreamRunContext,
        workspace_root: str | Path,
    ) -> DreamWorkbenchTurnContext:
        workspace = self._safe_workspace(workspace_root, context.thread_id)
        dream_root = workspace / ".dream"
        try:
            visible = dream_root.lstat()
            resolved_dream = dream_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise DreamWorkbenchContextError(
                "Dream surface must be initialized before context materialization"
            ) from exc
        if (
            stat.S_ISLNK(visible.st_mode)
            or not resolved_dream.is_dir()
            or resolved_dream.parent != workspace
        ):
            raise DreamWorkbenchContextError("Dream surface is unsafe")

        projects = self._discover_projects(workspace)
        project_slug = projects[0][0] if projects else None
        episode_codes = projects[0][1] if projects else ()
        context_file = resolved_dream / DREAM_WORKBENCH_CONTEXT_RELATIVE_PATH.name
        asset_collaboration_file = (
            resolved_dream / DREAM_ASSET_COLLABORATION_RELATIVE_PATH.name
        )
        canonical_project = (
            workspace / "stories" / project_slug / "project.yaml"
            if project_slug is not None
            else None
        )
        server_facts = {
            "workflow_run_id": context.workflow_run_id,
            "thread_id": context.thread_id,
            "workspace_root": str(workspace),
            "workbench_context_path": str(context_file),
            "asset_collaboration_path": str(asset_collaboration_file),
            "project_slug": project_slug,
            "canonical_project_path": (
                str(canonical_project) if canonical_project is not None else None
            ),
            "episode_codes": list(episode_codes),
        }
        payload = (
            load_dream_workbench_contract()
            + "\n```json\n"
            + json.dumps(
                server_facts,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
            + "\n```\n"
        ).encode("utf-8")
        self._replace_context_file(
            resolved_dream,
            target_name=DREAM_WORKBENCH_CONTEXT_RELATIVE_PATH.name,
            temporary_prefix="WORKBENCH",
            payload=payload,
            label="workbench context",
        )
        self._replace_context_file(
            resolved_dream,
            target_name=DREAM_ASSET_COLLABORATION_RELATIVE_PATH.name,
            temporary_prefix="ASSET-COLLABORATION",
            payload=load_dream_asset_collaboration_contract().encode("utf-8"),
            label="asset collaboration context",
        )

        project_line = (
            f"唯一 canonical project 是 `stories/{project_slug}/project.yaml`。"
            if project_slug is not None
            else "当前尚未发现 canonical project；初始化时必须先创建唯一 project.yaml。"
        )
        instruction = (
            "<story_workspace_dream_workbench>\n"
            "当前请求属于 Dream 工作区。宿主已确认或刷新本轮工作台上下文文件。\n"
            f"在处理用户请求前，必须使用 Read 工具读取并确认 `{context_file}` 和 "
            f"`{asset_collaboration_file}`；"
            "不能只依赖上一轮记忆。\n"
            f"当前 workflow_run_id 是 `{context.workflow_run_id}`，thread_id 是 `{context.thread_id}`。\n"
            f"{project_line}\n"
            "如果该文件无法读取或其中的 run/thread/project 与本指令不一致，停止修改并报告"
            "工作区上下文不可用，不得猜测或创建另一套 Project。\n"
            "用户提出标题或项目属性修改时，直接编辑 canonical `project.yaml`，不要只返回 JSON、"
            "建议或 Chat 标题。用户提出人物、场景或分镜增删改时，必须按资产协作合同使用"
            "内建文件工具修改 canonical 文件；普通 Chat 的 proposal JSON 规则不适用于本轮。\n"
            "成功根 turn 后宿主 Hook 会按最新文件事实同步页面；不要写 `.dream/**`。\n"
            "</story_workspace_dream_workbench>"
        )
        return DreamWorkbenchTurnContext(
            instruction=instruction,
            workspace_file=str(context_file),
            asset_collaboration_file=str(asset_collaboration_file),
            project_slug=project_slug,
            episode_codes=episode_codes,
        )


__all__ = [
    "DREAM_ASSET_COLLABORATION_RELATIVE_PATH",
    "DREAM_ASSET_COLLABORATION_SOURCE_PATH",
    "DREAM_WORKBENCH_CONTEXT_RELATIVE_PATH",
    "DREAM_WORKBENCH_CONTEXT_SOURCE_PATH",
    "DreamWorkbenchContext",
    "DreamWorkbenchContextError",
    "DreamWorkbenchTurnContext",
    "load_dream_workbench_contract",
    "load_dream_asset_collaboration_contract",
]
