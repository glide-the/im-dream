# [Input] Canonical Dream workbench fixtures, Admin authority DTOs, and the post-turn Hook.
# [Output] Verify deterministic artifact sync plus repairable/non-repairable validation classification.
# [Pos] Story Workspace post-turn Hook contract test in backend/tests.
# [Sync] 2026-09-01: cover allowlisted project-slug repair and fail-closed launch authority.
# [Sync] 2026-09-01: cover pre-write rejection of duplicate canonical roots
#                    and duplicate stage entity identities.
# [Sync] 2026-09-02: cover changed/preexisting EP02 registry activation and Episode-only titles.
# [Sync] 2026-09-04: connect canonical character/scene publication to the
#                    run-private reader and PostgreSQL materializer seam.
# [Sync] 2026-09-06: prove a current same-Deck Agent switch still publishes
#                    canonical character changes while launch provenance stays frozen.
# [Sync] 2026-09-16: replace Dream database mocks with the Registry185-191
#                    authority and artifact persistence provider contract.

"""Automatic root-turn workbench synchronization contract."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.workflow_run import RunStatus, WorkflowRun
from services.admin_data.story_workspace_artifact_data import (
    AdminStoryWorkspaceArtifactProvider,
    StoryWorkspaceArtifactAuthorityDTO,
    StoryWorkspaceEpisodeAuthorityDTO,
)
from services.story_workspace.dream_artifact_turn_hook import (
    DreamArtifactRepairability,
    DreamArtifactTurnHook,
    DreamArtifactTurnHookError,
)
from services.story_workspace.dream_file_service import StoryWorkspaceDreamFileReader
from services.story_workspace.episode_artifact_service import (
    StoryWorkspaceEpisodeAuthority,
)
from services.story_workspace.episode_binding_service import (
    StoryWorkspaceEpisodeBindingContext,
    StoryWorkspaceEpisodeBindingService,
)
from story_workspace.contracts import (
    StoryWorkspaceDreamRunContext,
    StoryWorkspaceDreamStage,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
THREAD_ID = "thread-dream-artifact-hook"
ORIGINAL_MATERIALIZE_STORY_INDEX = DreamArtifactTurnHook._materialize_story_index


def authoritative_run() -> WorkflowRun:
    return WorkflowRun(
        workflow_run_id=RUN_ID,
        deck_plugin_id="plugin-1",
        workflow_definition_ref="workflow-1",
        deck_plugin_binding_id="binding-1",
        binding_revision=3,
        deck_plugin_version="1.2.3",
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
        deck_plugin_manifest_hash="sha256:" + "1" * 64,
        workflow_preflight_id="pf_" + "2" * 32,
        status=RunStatus.PREFLIGHT,
        workspace_id="workspace-1",
        idempotency_key="run-request-1",
        input_hash="sha256:" + "3" * 64,
        semantic_fingerprint="sha256:" + "4" * 64,
        status_version=1,
        created_by="actor-1",
        created_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
        source_voice_thread_id=THREAD_ID,
    )


def context(*, agent_id: str | None = None) -> StoryWorkspaceDreamRunContext:
    return StoryWorkspaceDreamRunContext(
        workflow_run_id=RUN_ID,
        thread_id=THREAD_ID,
        deck_id="deck-1",
        agent_id=agent_id,
        deck_plugin_id="plugin-1",
        deck_plugin_version="1.2.3",
        deck_plugin_binding_id="binding-1",
        binding_revision=3,
        deck_runtime_snapshot_id="snapshot-1",
        runtime_plugin_lock_id="lock-1",
    )


def episode_authority() -> StoryWorkspaceEpisodeAuthority:
    return StoryWorkspaceEpisodeAuthority(
        workflow_run_id=RUN_ID,
        episode_uid="5" * 32,
        story_slug="demo-project",
        episode_code="EP01",
    )


def launched_run() -> WorkflowRun:
    return authoritative_run().model_copy(update={
        "source_message_id": "dream-launch-message",
        "source_message_time": datetime(2026, 8, 13, tzinfo=timezone.utc),
    })


def artifact_authority(
    *,
    run: WorkflowRun | None = None,
    project_story_slug: str = "demo-project",
    agent_id: str | None = None,
) -> StoryWorkspaceArtifactAuthorityDTO:
    selected_run = run or authoritative_run()
    return StoryWorkspaceArtifactAuthorityDTO(
        run=selected_run.model_dump(mode="json"),
        thread_id=selected_run.source_voice_thread_id or THREAD_ID,
        thread_updated_at="2026-08-13T00:00:00Z",
        deck_id="deck-1",
        deck_display_name="Dream Deck",
        launch_agent_id=agent_id,
        goal="雨夜归途",
        project_story_slug=project_story_slug,
        episode_authority=None,
        project_title="雨夜归途",
        confirmation_accepted=False,
        confirmation_dispatched=False,
    )


class _ArtifactProvider(AdminStoryWorkspaceArtifactProvider):
    """In-memory Admin provider; file behavior remains the production path."""

    def __init__(
        self,
        authority: StoryWorkspaceArtifactAuthorityDTO | None = None,
    ) -> None:
        self.authority = authority or artifact_authority()
        self.authority_calls: list[dict] = []
        self.ensure_calls: list[dict] = []
        self.story_workspace_artifact_authority = MagicMock(
            side_effect=self._authority
        )
        self.ensure_story_workspace_episode_authority = MagicMock(
            side_effect=self._ensure
        )
        self.mark_story_workspace_artifact_output_ready = MagicMock(
            return_value=SimpleNamespace(
                workflow_run_id=RUN_ID,
                status="pending_review",
                status_version=1,
                replayed=False,
            )
        )
        self.materialize_story_workspace_artifact_index = MagicMock(
            return_value=SimpleNamespace(
                write_status="same_revision",
                observation=SimpleNamespace(error_code=None),
            )
        )

    def _authority(self, **kwargs):
        self.authority_calls.append(kwargs)
        return self.authority

    def _ensure(self, **kwargs):
        self.ensure_calls.append(kwargs)
        return SimpleNamespace(
            authority=StoryWorkspaceEpisodeAuthorityDTO(
                schema="story-workspace-episode-authority/v1",
                workflow_run_id=kwargs["workflow_run_id"],
                episode_uid="5" * 32,
                story_slug=kwargs["story_slug"],
                episode_code=kwargs["episode_code"],
            ),
            replayed=False,
        )


class DreamArtifactTurnHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.story_index_materialize = patch.object(
            DreamArtifactTurnHook,
            "_materialize_story_index",
            return_value="same_revision",
        )
        self.story_index_materialize_mock = self.story_index_materialize.start()
        self.addCleanup(self.story_index_materialize.stop)
        self.artifact_provider = _ArtifactProvider()
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name) / THREAD_ID
        self.workspace.mkdir()
        (self.workspace / ".dream").mkdir()
        (self.workspace / "assets" / "characters").mkdir(parents=True)
        (self.workspace / "assets" / "scenes").mkdir(parents=True)
        episode = self.workspace / "stories" / "demo-project" / "episodes" / "EP01"
        episode.mkdir(parents=True)

        (self.workspace / "assets" / "characters" / "lead.md").write_text(
            """---
char_id: lead
char_name: 林夏
occupation: 调查记者
relationships:
  - char_id: guide
    relation: 旧友
---
# 林夏

她在雨夜返回旧车站寻找真相。
""",
            encoding="utf-8",
        )
        (self.workspace / "assets" / "scenes" / "station.md").write_text(
            """---
scene_id: station
name: 雨夜车站
type: exterior
---
# 雨夜车站

废弃站台被冷雨和钠灯包围。
""",
            encoding="utf-8",
        )
        (episode.parents[1] / "project.yaml").write_text(
            "project_id: demo-project\nproject_name: 雨夜归途\n",
            encoding="utf-8",
        )
        (episode / "episode-outline.md").write_text(
            "# EP01 大纲\n\n林夏回到车站。\n",
            encoding="utf-8",
        )
        (episode / "script.md").write_text(
            "# EP01 剧本\n\n林夏：我回来了。\n",
            encoding="utf-8",
        )
        (episode / "storyboard.yaml").write_text(
            """---
episode: EP01
total_shots: 2
total_duration_sec: 12.5
---
shots:
  - shot_id: S01
    scene_ref: station
""",
            encoding="utf-8",
        )
        (episode / "review-report.md").write_text(
            "# 审阅\n\n草稿可继续编辑。\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _binding_error(
        self,
        authority: StoryWorkspaceArtifactAuthorityDTO,
    ) -> DreamArtifactTurnHookError:
        hook = DreamArtifactTurnHook()
        provider = _ArtifactProvider(authority)
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=provider,
        )
        with self.assertRaises(DreamArtifactTurnHookError) as raised:
            hook._synchronize_episode_registry(
                ticket,
                authority.workflow_run(),
                launch_authority=authority,
                private_files={
                    "stories/demo-project/episodes/EP01/script.md": b"# EP01\n",
                },
            )
        return raised.exception

    def test_project_story_slug_mismatch_is_agent_repairable(self) -> None:
        error = self._binding_error(
            artifact_authority(project_story_slug="server-project")
        )

        self.assertEqual(error.code, "PROJECT_STORY_SLUG_MISMATCH")
        self.assertIs(
            error.issue.repairability,
            DreamArtifactRepairability.AGENT_REPAIRABLE,
        )
        self.assertEqual(error.issue.expected, "server-project")
        self.assertEqual(error.issue.actual, "demo-project")

    def test_successful_ep02_change_extends_registry_and_activates_ep02(self) -> None:
        hook = DreamArtifactTurnHook()
        authority_dto = artifact_authority()
        provider = _ArtifactProvider(authority_dto)
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=provider,
        )
        binding_service = StoryWorkspaceEpisodeBindingService(self.workspace)
        binding_context = StoryWorkspaceEpisodeBindingContext(
            workflow_run_id=RUN_ID,
            trusted_project_story_slug="demo-project",
            locked_context_story_slug="demo-project",
            run_provenance_story_slug="demo-project",
            episode_uid="5" * 32,
        )
        binding_service.bind_first_episode(binding_context)
        ep02 = self.workspace / "stories" / "demo-project" / "episodes" / "EP02"
        ep02.mkdir()
        (ep02 / "script.md").write_text(
            "# EP02 剧本\n\n只属于 EP02 的内容。\n",
            encoding="utf-8",
        )

        selected = hook._synchronize_episode_registry(
            ticket,
            authority_dto.workflow_run(),
            launch_authority=authority_dto,
            private_files=hook._collect_private_artifact_files(ticket.workspace_root),
        )

        registry = binding_service.read_episode_registry(binding_context)
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected.episode_code, "EP02")
        self.assertEqual(
            [item.episode_code for item in registry.episodes],
            ["EP01", "EP02"],
        )
        self.assertEqual(registry.active_episode_uid, selected.episode_uid)

    def test_single_preexisting_unregistered_ep02_becomes_active(self) -> None:
        binding_service = StoryWorkspaceEpisodeBindingService(self.workspace)
        binding_context = StoryWorkspaceEpisodeBindingContext(
            workflow_run_id=RUN_ID,
            trusted_project_story_slug="demo-project",
            locked_context_story_slug="demo-project",
            run_provenance_story_slug="demo-project",
            episode_uid="5" * 32,
        )
        first = binding_service.bind_first_episode(binding_context)
        ep02 = self.workspace / "stories" / "demo-project" / "episodes" / "EP02"
        ep02.mkdir()
        (ep02 / "script.md").write_text(
            "# EP02 剧本\n\n本轮开始前已经存在的 EP02。\n",
            encoding="utf-8",
        )
        hook = DreamArtifactTurnHook()
        authority_dto = artifact_authority()
        provider = _ArtifactProvider(authority_dto)
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=provider,
        )

        selected = hook._synchronize_episode_registry(
            ticket,
            authority_dto.workflow_run(),
            launch_authority=authority_dto,
            private_files=hook._collect_private_artifact_files(ticket.workspace_root),
        )

        registry = binding_service.read_episode_registry(binding_context)
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(
            [item.episode_code for item in registry.episodes],
            ["EP01", "EP02"],
        )
        self.assertEqual(registry.revision, 3)
        self.assertEqual(registry.episodes[0].episode_uid, first.episode_uid)
        self.assertEqual(selected.episode_code, "EP02")
        self.assertEqual(registry.active_episode_uid, selected.episode_uid)

    def test_actor_thread_run_deck_and_plugin_authority_are_not_repairable(self) -> None:
        cases = {
            "actor": artifact_authority(
                run=launched_run().model_copy(update={"created_by": "actor-forged"})
            ),
            "run": artifact_authority(
                run=launched_run().model_copy(
                    update={"workflow_run_id": "run_" + "f" * 32}
                )
            ),
            "thread": artifact_authority(
                run=launched_run().model_copy(
                    update={"source_voice_thread_id": "thread-forged"}
                )
            ),
            "deck": artifact_authority().model_copy(
                update={"deck_id": "deck-forged"}
            ),
            "plugin_lock": artifact_authority(
                run=launched_run().model_copy(
                    update={"runtime_plugin_lock_id": "lock-forged"}
                )
            ),
        }
        for label, authority_dto in cases.items():
            with self.subTest(authority=label):
                provider = _ArtifactProvider(authority_dto)
                ticket = DreamArtifactTurnHook().before_main_turn(
                    context=context(),
                    actor_id="actor-1",
                    cwd=str(self.workspace),
                    artifact_provider=provider,
                )
                with self.assertRaises(DreamArtifactTurnHookError) as raised:
                    DreamArtifactTurnHook._load_artifact_authority(ticket)
                self.assertEqual(
                    raised.exception.code,
                    "DREAM_LAUNCH_AUTHORITY_INVALID",
                )
                self.assertIs(
                    raised.exception.issue.repairability,
                    DreamArtifactRepairability.NON_REPAIRABLE,
                )

    def test_current_agent_switch_still_publishes_character_stage(self) -> None:
        character = self.workspace / "assets" / "characters" / "lead.md"
        character.write_text(
            """---
char_id: lead
char_name: 林夏
occupation: 调查记者
personality:
  core_traits: [清明内求]
---
# 林夏

她在雨夜返回旧车站寻找真相。
""",
            encoding="utf-8",
        )
        hook = DreamArtifactTurnHook()
        provider = _ArtifactProvider(
            artifact_authority(run=launched_run(), agent_id="voice-screenwriter")
        )
        ticket = hook.before_main_turn(
            context=context(agent_id="voice-character-designer"),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=provider,
        )

        result = hook.after_main_turn(ticket)

        self.assertIn("characters", result.changed_stages)
        stage = StoryWorkspaceDreamFileReader(self.workspace).read_stage(
            launched_run(),
            stage=StoryWorkspaceDreamStage.CHARACTERS,
        )
        self.assertIsNotNone(stage)
        assert stage is not None
        self.assertEqual(stage.revision, 1)
        self.assertIn("清明内求", stage.items[0].content or "")

    def test_multiple_canonical_project_roots_are_repairable_before_projection_write(self) -> None:
        duplicate_episode = (
            self.workspace
            / "stories"
            / "stale-project"
            / "episodes"
            / "EP01"
        )
        duplicate_episode.mkdir(parents=True)
        (duplicate_episode.parents[1] / "project.yaml").write_text(
            "project_id: stale-project\nproject_name: 旧项目副本\n",
            encoding="utf-8",
        )
        (duplicate_episode / "storyboard.yaml").write_text(
            "episode: EP01\ntotal_shots: 1\n",
            encoding="utf-8",
        )
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )

        with (
            patch.object(hook, "_synchronize_episode_registry") as bind,
            self.assertRaises(DreamArtifactTurnHookError) as raised,
        ):
            hook.after_main_turn(ticket)

        self.assertEqual(
            raised.exception.code,
            "DREAM_CANONICAL_PROJECT_AMBIGUOUS",
        )
        self.assertIs(
            raised.exception.issue.repairability,
            DreamArtifactRepairability.AGENT_REPAIRABLE,
        )
        bind.assert_not_called()
        run_file = (
            self.workspace
            / ".dream"
            / "runtime"
            / "runs"
            / RUN_ID
            / "run.json"
        )
        self.assertFalse(run_file.exists())

    def test_auto_repair_cleanup_scope_uses_fresh_admin_authority(self) -> None:
        stale = self.workspace / "stories" / "stale-project"
        stale.mkdir(parents=True)
        (stale / "project.yaml").write_text(
            "project_id: stale-project\nproject_slug: stale-project\n",
            encoding="utf-8",
        )
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )

        cleanup = hook.resolve_auto_repair_project_cleanup_scope(
            ticket,
            validation_code="DREAM_CANONICAL_PROJECT_AMBIGUOUS",
        )

        self.assertEqual(cleanup, ("demo-project", ("stale-project",)))
        self.artifact_provider.story_workspace_artifact_authority.assert_called_once_with(
            actor_id="actor-1",
            thread_id=THREAD_ID,
            workflow_run_id=RUN_ID,
        )

    def test_auto_repair_cleanup_scope_rejects_changed_admin_authority(self) -> None:
        stale = self.workspace / "stories" / "stale-project"
        stale.mkdir(parents=True)
        (stale / "project.yaml").write_text(
            "project_id: stale-project\nproject_slug: stale-project\n",
            encoding="utf-8",
        )
        provider = _ArtifactProvider(
            artifact_authority(
                run=launched_run().model_copy(
                    update={"created_by": "actor-forged"}
                )
            )
        )
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=provider,
        )

        with self.assertRaises(DreamArtifactTurnHookError) as raised:
            hook.resolve_auto_repair_project_cleanup_scope(
                ticket,
                validation_code="PROJECT_STORY_SLUG_MISMATCH",
            )

        self.assertEqual(raised.exception.code, "DREAM_LAUNCH_AUTHORITY_INVALID")
        self.assertIs(
            raised.exception.issue.repairability,
            DreamArtifactRepairability.NON_REPAIRABLE,
        )

    def test_duplicate_stage_entity_ids_are_agent_repairable(self) -> None:
        (self.workspace / "assets" / "characters" / "lead-copy.md").write_text(
            "---\nchar_id: lead\nchar_name: 林夏副本\n---\n",
            encoding="utf-8",
        )

        with self.assertRaises(DreamArtifactTurnHookError) as raised:
            DreamArtifactTurnHook._collect_stage_projections(
                self.workspace.resolve()
            )

        self.assertEqual(
            raised.exception.code,
            "DREAM_STAGE_ENTITY_ID_DUPLICATE",
        )
        self.assertEqual(raised.exception.issue.expected, "characters")
        self.assertEqual(
            raised.exception.issue.actual,
            "duplicate_entity_id",
        )
        self.assertIs(
            raised.exception.issue.repairability,
            DreamArtifactRepairability.AGENT_REPAIRABLE,
        )

    def test_invalid_workspace_stage_schema_is_agent_repairable(self) -> None:
        (self.workspace / "assets" / "characters" / "invalid-id.md").write_text(
            "---\nchar_id: " + ("a" * 129) + "\nchar_name: 越界身份\n---\n",
            encoding="utf-8",
        )

        with self.assertRaises(DreamArtifactTurnHookError) as raised:
            DreamArtifactTurnHook._collect_stage_projections(
                self.workspace.resolve()
            )

        self.assertEqual(
            raised.exception.code,
            "DREAM_STAGE_SCHEMA_INVALID",
        )
        self.assertEqual(raised.exception.issue.expected, "characters")
        self.assertEqual(raised.exception.issue.actual, "schema_invalid")
        self.assertIs(
            raised.exception.issue.repairability,
            DreamArtifactRepairability.AGENT_REPAIRABLE,
        )

    def test_successful_root_turn_projects_page_stages_and_private_artifacts(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        ):
            result = hook.after_main_turn(ticket)

        self.assertEqual(
            result.changed_stages,
            ("characters", "scenes", "storyboards"),
        )
        self.assertTrue(result.private_artifact_changed)
        self.assertTrue(result.episode_bound)
        self.assertEqual(result.story_index_status, "same_revision")
        self.assertEqual(result.changed_source_files, ())
        projection = StoryWorkspaceDreamFileReader(self.workspace).read(
            authoritative_run(),
            thread_id=THREAD_ID,
        )
        self.assertTrue(projection.can_confirm)
        self.assertEqual(projection.stages["characters"].items[0].display_name, "林夏")
        self.assertEqual(projection.stages["scenes"].items[0].display_name, "雨夜车站")
        self.assertEqual(projection.stages["storyboards"].items[0].entity_id, "EP01")
        self.assertEqual(projection.stages["storyboards"].items[0].display_name, "EP01")

        artifact = self.workspace / ".dream" / "runtime" / "runs" / RUN_ID / "artifact"
        private_episode = artifact / "stories" / "demo-project" / "episodes" / "EP01"
        self.assertEqual(
            (private_episode / "script.md").read_text(encoding="utf-8"),
            "# EP01 剧本\n\n林夏：我回来了。\n",
        )
        manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "dream-artifact-manifest/v1")
        self.assertEqual(manifest["workflow_run_id"], RUN_ID)
        self.assertEqual(
            {entry["path"] for entry in manifest["files"]},
            set(result.private_files),
        )
        self.story_index_materialize_mock.assert_called_once_with(
            ticket,
            authoritative_run(),
            episode_authority=True,
        )

    def test_repeated_root_turn_is_idempotent_and_changed_file_republishes(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        ):
            first = hook.after_main_turn(ticket)
            second = hook.after_main_turn(ticket)

        self.assertTrue(first.private_artifact_changed)
        self.assertEqual(second.changed_stages, ())
        self.assertFalse(second.private_artifact_changed)
        reader = StoryWorkspaceDreamFileReader(self.workspace)
        self.assertEqual(reader.read_stage(authoritative_run(), stage="characters").revision, 1)

        script = self.workspace / "stories" / "demo-project" / "episodes" / "EP01" / "script.md"
        script.write_text("# EP01 剧本\n\n林夏：继续。\n", encoding="utf-8")
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        ):
            third = hook.after_main_turn(ticket)
        self.assertEqual(third.changed_stages, ())
        self.assertTrue(third.private_artifact_changed)
        self.assertEqual(
            third.changed_source_files,
            ("stories/demo-project/episodes/EP01/script.md",),
        )
        private_script = (
            self.workspace
            / ".dream"
            / "runtime"
            / "runs"
            / RUN_ID
            / "artifact"
            / "stories"
            / "demo-project"
            / "episodes"
            / "EP01"
            / "script.md"
        )
        self.assertIn("继续", private_script.read_text(encoding="utf-8"))

    def test_removed_skill_sources_delete_stale_stage_and_new_sources_rebuild_it(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )
        patches = (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        )
        with patches[0], patches[1], patches[2]:
            hook.after_main_turn(ticket)

        character = self.workspace / "assets" / "characters" / "lead.md"
        character.unlink()
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        ):
            removed = hook.after_main_turn(ticket)

        self.assertIn("characters", removed.changed_stages)
        reader = StoryWorkspaceDreamFileReader(self.workspace)
        self.assertIsNone(reader.read_stage(authoritative_run(), stage="characters"))

        character.write_text(
            "---\nchar_id: patient\nchar_name: 隔壁的病友\n---\n\n新的角色事实。\n",
            encoding="utf-8",
        )
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        ):
            rebuilt = hook.after_main_turn(ticket)

        self.assertIn("characters", rebuilt.changed_stages)
        stage = reader.read_stage(authoritative_run(), stage="characters")
        assert stage is not None
        self.assertEqual(stage.items[0].entity_id, "patient")
        self.assertEqual(stage.items[0].display_name, "隔壁的病友")

    def test_asset_crud_reconciles_characters_scenes_and_storyboard(self) -> None:
        """One complete natural-language asset journey maps file facts only."""

        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )

        def synchronize():
            with (
                patch.object(
                    hook,
                    "_load_artifact_authority",
                    return_value=artifact_authority(run=authoritative_run()),
                ),
                patch.object(hook, "_record_output_ready"),
                patch.object(
                    hook,
                    "_synchronize_episode_registry",
                    return_value=True,
                ),
            ):
                return hook.after_main_turn(ticket)

        synchronize()
        reader = StoryWorkspaceDreamFileReader(self.workspace)
        character = self.workspace / "assets" / "characters" / "guide.md"
        scene = self.workspace / "assets" / "scenes" / "fireplace.md"
        storyboard = (
            self.workspace
            / "stories"
            / "demo-project"
            / "episodes"
            / "EP01"
            / "storyboard.yaml"
        )

        character.write_text(
            "---\nchar_id: guide\nchar_name: 阿酷\n---\n\n短发的安全员。\n",
            encoding="utf-8",
        )
        scene.write_text(
            "---\nscene_id: fireplace\nscene_name: 火塘\n---\n\n暖橙色火光。\n",
            encoding="utf-8",
        )
        storyboard_payload = {
            "episode": "EP01",
            "total_shots": 1,
            "total_duration_sec": 0,
            "shots": [
                {
                    "shot_id": "S01",
                    "scene_ref": "station",
                }
            ],
        }
        storyboard_payload["shots"].append(
            {
                "shot_id": "shot-qa-asset",
                "scene_ref": "fireplace",
                "characters": ["guide"],
                "shot_type": "medium",
                "visual": "阿酷站在火塘旁",
                "camera": {"movement": "static"},
                "timing": {"duration_sec": 4},
            }
        )
        storyboard_payload["total_shots"] = len(storyboard_payload["shots"])
        storyboard_payload["total_duration_sec"] = 4
        storyboard.write_text(
            yaml.safe_dump(storyboard_payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        added = synchronize()
        self.assertEqual(
            set(added.changed_stages),
            {"characters", "scenes", "storyboards"},
        )
        character_stage = reader.read_stage(authoritative_run(), stage="characters")
        scene_stage = reader.read_stage(authoritative_run(), stage="scenes")
        storyboard_stage = reader.read_stage(authoritative_run(), stage="storyboards")
        assert character_stage is not None
        assert scene_stage is not None
        assert storyboard_stage is not None
        self.assertEqual(
            {item.entity_id for item in character_stage.items},
            {"lead", "guide"},
        )
        self.assertEqual(
            {item.entity_id for item in scene_stage.items},
            {"station", "fireplace"},
        )

        character.write_text(
            "---\nchar_id: guide\nchar_name: 阿酷（安全员）\n---\n\n短发，穿黑色冲锋衣。\n",
            encoding="utf-8",
        )
        scene.write_text(
            "---\nscene_id: fireplace\nscene_name: 村子火塘\n---\n\n暖橙色火光与木椅。\n",
            encoding="utf-8",
        )
        storyboard_payload["shots"][-1]["visual"] = "阿酷穿黑色冲锋衣站在火塘旁"
        storyboard.write_text(
            yaml.safe_dump(storyboard_payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

        updated = synchronize()
        self.assertEqual(
            set(updated.changed_stages),
            {"characters", "scenes", "storyboards"},
        )
        character_stage = reader.read_stage(authoritative_run(), stage="characters")
        scene_stage = reader.read_stage(authoritative_run(), stage="scenes")
        assert character_stage is not None
        assert scene_stage is not None
        self.assertEqual(character_stage.revision, 3)
        self.assertEqual(scene_stage.revision, 3)
        self.assertIn(
            "阿酷（安全员）",
            {item.display_name for item in character_stage.items},
        )
        self.assertIn(
            "村子火塘",
            {item.display_name for item in scene_stage.items},
        )

        # Remove the referencing shot first, then its temporary character and
        # scene. This mirrors the contract's no-dangling-reference cleanup.
        storyboard_payload["shots"] = [
            shot
            for shot in storyboard_payload["shots"]
            if shot.get("shot_id") != "shot-qa-asset"
        ]
        storyboard_payload["total_shots"] = len(storyboard_payload["shots"])
        storyboard_payload["total_duration_sec"] = 0
        storyboard.write_text(
            yaml.safe_dump(storyboard_payload, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        character.unlink()
        scene.unlink()

        deleted = synchronize()
        self.assertEqual(
            set(deleted.changed_stages),
            {"characters", "scenes", "storyboards"},
        )
        character_stage = reader.read_stage(authoritative_run(), stage="characters")
        scene_stage = reader.read_stage(authoritative_run(), stage="scenes")
        assert character_stage is not None
        assert scene_stage is not None
        self.assertEqual(
            {item.entity_id for item in character_stage.items},
            {"lead"},
        )
        self.assertEqual(
            {item.entity_id for item in scene_stage.items},
            {"station"},
        )
        final_storyboard = yaml.safe_load(storyboard.read_text("utf-8"))
        self.assertFalse(
            any(
                shot.get("shot_id") == "shot-qa-asset"
                for shot in final_storyboard["shots"]
            )
        )

    def test_project_title_edit_republishes_canonical_project_file(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        ):
            hook.after_main_turn(ticket)

        project = self.workspace / "stories" / "demo-project" / "project.yaml"
        project.write_text(
            "project_id: demo-project\nproject_name: 隔壁的病友\n",
            encoding="utf-8",
        )
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True),
        ):
            result = hook.after_main_turn(ticket)

        self.assertTrue(result.private_artifact_changed)
        self.assertIn(
            "stories/demo-project/project.yaml",
            result.changed_source_files,
        )
        private_project = (
            self.workspace
            / ".dream"
            / "runtime"
            / "runs"
            / RUN_ID
            / "artifact"
            / "stories"
            / "demo-project"
            / "project.yaml"
        )
        self.assertIn("隔壁的病友", private_project.read_text(encoding="utf-8"))

    def test_any_successful_dream_turn_attempts_idempotent_episode_binding(self) -> None:
        hook = DreamArtifactTurnHook()
        ticket = hook.before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )
        with (
            patch.object(hook, "_load_artifact_authority", return_value=artifact_authority(run=authoritative_run())),
            patch.object(hook, "_record_output_ready"),
            patch.object(hook, "_synchronize_episode_registry", return_value=True) as bind,
        ):
            result = hook.after_main_turn(ticket)
        bind.assert_called_once()
        self.assertTrue(result.episode_bound)
        self.story_index_materialize_mock.assert_called_once_with(
            ticket,
            authoritative_run(),
            episode_authority=True,
        )

    def test_story_index_materialization_uses_current_episode_surface(self) -> None:
        ticket = DreamArtifactTurnHook().before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )
        surface = object()
        projected = SimpleNamespace(
            source_project_id="demo-project",
            title="雨夜归途",
            episode_count=1,
            artifact_manifest_revision="sha256:" + "1" * 64,
            script_revision="sha256:" + "2" * 64,
            script_size_bytes=20,
        )
        self.artifact_provider.materialize_story_workspace_artifact_index.return_value = (
            SimpleNamespace(
                write_status="updated",
                observation=SimpleNamespace(error_code=None),
            )
        )
        with (
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "StoryWorkspaceEpisodeArtifactService"
            ) as artifact_service,
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "ArtifactStoryIndexProjector"
            ) as projector,
        ):
            artifact_service.return_value.read_surface.return_value = surface
            projector.return_value.project.return_value = projected
            status = ORIGINAL_MATERIALIZE_STORY_INDEX(
                ticket,
                authoritative_run(),
                episode_authority=episode_authority(),
            )

        self.assertEqual(status, "updated")
        artifact_service.return_value.read_surface.assert_called_once_with(
            RUN_ID,
            episode_authority=episode_authority(),
        )
        projector.return_value.project.assert_called_once_with(
            workspace_root=self.workspace.resolve(),
            workflow_run=authoritative_run(),
            actor_id="actor-1",
            thread_id=THREAD_ID,
            episode_authority=episode_authority(),
            refreshed_surface=surface,
        )
        call = (
            self.artifact_provider
            .materialize_story_workspace_artifact_index.call_args
        )
        self.assertEqual(call.kwargs["actor_id"], "actor-1")
        self.assertEqual(call.kwargs["thread_id"], THREAD_ID)
        self.assertEqual(call.kwargs["workflow_run_id"], RUN_ID)
        self.assertEqual(
            call.kwargs["projection"].artifact_manifest_revision,
            "sha256:" + "1" * 64,
        )

    def test_story_index_waits_for_script_without_calling_admin_write(self) -> None:
        from services.story_workspace.artifact_story_index_projector import (
            ArtifactStoryProjectionError,
        )

        ticket = DreamArtifactTurnHook().before_main_turn(
            context=context(),
            actor_id="actor-1",
            cwd=str(self.workspace),
            artifact_provider=self.artifact_provider,
        )
        self.artifact_provider.materialize_story_workspace_artifact_index.reset_mock()
        with (
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "StoryWorkspaceEpisodeArtifactService"
            ) as artifact_service,
            patch(
                "services.story_workspace.dream_artifact_turn_hook."
                "ArtifactStoryIndexProjector"
            ) as projector,
        ):
            artifact_service.return_value.read_surface.return_value = object()
            projector.return_value.project.side_effect = ArtifactStoryProjectionError(
                "artifact_missing",
                retryable=True,
            )
            status = ORIGINAL_MATERIALIZE_STORY_INDEX(
                ticket,
                authoritative_run(),
                episode_authority=episode_authority(),
            )

        self.assertEqual(status, "not_ready")
        self.artifact_provider.materialize_story_workspace_artifact_index.assert_not_called()

    def test_historical_unicode_and_header_only_assets_form_page_projection(self) -> None:
        (self.workspace / "assets" / "characters" / "凌波.yaml").write_text(
            """# 角色：凌波
id: lingbo
name: 凌波

## 核心特质
谨慎且有策略。
""",
            encoding="utf-8",
        )
        (self.workspace / "assets" / "scenes" / "studio.md").write_text(
            """---
scene_id: studio
scene_name: 创作工作室
location: 城市中心
""",
            encoding="utf-8",
        )

        projections = DreamArtifactTurnHook._collect_stage_projections(
            self.workspace.resolve()
        )
        by_stage = {projection.stage.value: projection for projection in projections}
        characters = {
            item["entity_id"]: item for item in by_stage["characters"].items
        }
        scenes = {item["entity_id"]: item for item in by_stage["scenes"].items}

        self.assertEqual(characters["lingbo"]["display_name"], "凌波")
        self.assertEqual(
            characters["lingbo"]["source_file"],
            "assets/characters/凌波.yaml",
        )
        self.assertEqual(scenes["studio"]["display_name"], "创作工作室")

    def test_character_projection_keeps_compact_summary_and_complete_document(self) -> None:
        character = self.workspace / "assets" / "characters" / "lao-tou.md"
        source = """---
char_id: lao-tou
char_name: 老头（庖丁）
---
# 老头（庖丁）（lao-tou）

身份：夏都王宫掌厨，实为商地出身的故人。

外形：满头白发，围裙满是油渍，佝偻但有精气神。

人物关系：
- 对伊尹：识破其手法来历，暗中协助、传递商地情报。
- 对夏桀：隐忍多年，潜伏于御膳房。

动机：等待拨乱反正的一天。
"""
        character.write_text(source, encoding="utf-8")

        projections = DreamArtifactTurnHook._collect_stage_projections(
            self.workspace.resolve()
        )
        characters = next(
            projection
            for projection in projections
            if projection.stage is StoryWorkspaceDreamStage.CHARACTERS
        )
        lao_tou = next(
            item for item in characters.items if item["entity_id"] == "lao-tou"
        )

        self.assertEqual(
            lao_tou["summary"],
            "身份：夏都王宫掌厨，实为商地出身的故人。",
        )
        self.assertEqual(lao_tou["content"], source.strip())
        self.assertIn("外形：满头白发", str(lao_tou["content"]))
        self.assertIn("人物关系：", str(lao_tou["content"]))
        self.assertIn("动机：等待拨乱反正的一天。", str(lao_tou["content"]))


if __name__ == "__main__":
    unittest.main()
