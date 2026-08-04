"""Dream runtime file protocol contract and filesystem safety tests."""

from __future__ import annotations

import json
import multiprocessing
import os
import shutil
import stat
import tempfile
import unittest
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from models.workflow_run import RunStatus, WorkflowRun
import services.story_workspace.dream_file_service as dream_files
from services.story_workspace.dream_file_service import (
    StoryWorkspaceDreamFileConflict,
    StoryWorkspaceDreamFileError,
    StoryWorkspaceDreamFileReader,
    StoryWorkspaceDreamFileWriter,
    StoryWorkspaceDreamPathError,
)
from story_workspace.contracts import (
    STORY_WORKSPACE_DREAM_FILE_MAX_BYTES,
    STORY_WORKSPACE_DREAM_ITEMS_MAX,
    StoryWorkspaceDreamConfirmationCommand,
    StoryWorkspaceDreamEdit,
    StoryWorkspaceDreamFilesResponse,
    StoryWorkspaceDreamRunFile,
    StoryWorkspaceDreamSource,
    StoryWorkspaceDreamSourceResponse,
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageFile,
    StoryWorkspaceDreamStageResponse,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
OTHER_RUN_ID = "run_fedcba9876543210fedcba9876543210"


def cross_process_stage_update(
    workspace: str,
    workflow_run: WorkflowRun,
    ready: object,
    start: object,
    results: object,
    summary: str,
) -> None:
    """Spawn-safe worker used to verify the process-level CAS lock."""

    writer = StoryWorkspaceDreamFileWriter(workspace)
    ready.put(True)  # type: ignore[attr-defined]
    start.wait(5)  # type: ignore[attr-defined]
    try:
        writer.write_stage(
            workflow_run,
            stage=StoryWorkspaceDreamStage.CHARACTERS,
            source_files=["assets/characters/lead.md"],
            items=[{
                "entity_id": "entity-1",
                "display_name": "Entity",
                "summary": summary,
                "source_file": "assets/characters/lead.md",
                "relations": [],
            }],
            expected_revision=1,
        )
    except StoryWorkspaceDreamFileConflict:
        results.put("conflict")  # type: ignore[attr-defined]
    except Exception as exc:
        results.put(  # type: ignore[attr-defined]
            f"error:{type(exc).__name__}:{exc}"
        )
    else:
        results.put("written")  # type: ignore[attr-defined]


def authoritative_run(run_id: str = RUN_ID, **overrides: object) -> WorkflowRun:
    values: dict[str, object] = {
        "workflow_run_id": run_id,
        "deck_plugin_id": "plugin-1",
        "workflow_definition_ref": "workflow-1",
        "deck_plugin_binding_id": "binding-1",
        "binding_revision": 3,
        "deck_plugin_version": "1.2.3",
        "deck_runtime_snapshot_id": "snapshot-1",
        "runtime_plugin_lock_id": "lock-1",
        "deck_plugin_manifest_hash": "sha256:" + "1" * 64,
        "workflow_preflight_id": "pf_" + "2" * 32,
        "status": RunStatus.PREFLIGHT,
        "workspace_id": "workspace-1",
        "idempotency_key": "run-request-1",
        "input_hash": "sha256:" + "3" * 64,
        "semantic_fingerprint": "sha256:" + "4" * 64,
        "status_version": 1,
        "created_by": "actor-1",
        "created_at": datetime(2026, 8, 4, tzinfo=timezone.utc),
        "source_voice_thread_id": "thread-1",
    }
    values.update(overrides)
    return WorkflowRun(**values)


class StoryWorkspaceDreamFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary_directory.name)
        self.dream = self.workspace / ".dream"
        self.dream.mkdir()
        (self.dream / "README.md").write_text("static-readme\n", encoding="utf-8")
        (self.dream / "workspace.json").write_text(
            '{"schema_version":"dream-surface/v1"}\n', encoding="utf-8"
        )
        (self.workspace / "assets" / "characters").mkdir(parents=True)
        (self.workspace / "assets" / "characters" / "lead.md").write_text(
            "# Lead\n", encoding="utf-8"
        )
        (self.workspace / "assets" / "scenes").mkdir(parents=True)
        (self.workspace / "assets" / "scenes" / "opening.md").write_text(
            "# Opening\n", encoding="utf-8"
        )
        storyboard = self.workspace / "stories" / "demo" / "episodes" / "EP01"
        storyboard.mkdir(parents=True)
        (storyboard / "storyboard.yaml").write_text("shots: []\n", encoding="utf-8")
        self.run = authoritative_run()
        self.writer = StoryWorkspaceDreamFileWriter(self.workspace)
        self.reader = StoryWorkspaceDreamFileReader(self.workspace)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def item(source_file: str, summary: str = "summary") -> dict[str, object]:
        return {
            "entity_id": "entity-1",
            "display_name": "Entity",
            "summary": summary,
            "source_file": source_file,
            "relations": [],
        }

    def initialize_run(self) -> StoryWorkspaceDreamRunFile:
        return self.writer.write_run(
            self.run, thread_id="thread-1", expected_revision=0
        )

    @staticmethod
    def tree_snapshot(root: Path) -> list[tuple[str, str, bytes | None]]:
        snapshot: list[tuple[str, str, bytes | None]] = []
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                snapshot.append((relative, "symlink", os.readlink(path).encode()))
            elif path.is_dir():
                snapshot.append((relative, "dir", None))
            else:
                snapshot.append((relative, "file", path.read_bytes()))
        return snapshot

    def test_static_only_and_run_without_json_are_read_only_waiting_states(
        self,
    ) -> None:
        before = self.tree_snapshot(self.workspace)
        waiting = self.reader.read(self.run, thread_id="thread-1")
        self.assertEqual(waiting.run_revision, 0)
        self.assertEqual(waiting.stages, {})
        self.assertFalse(waiting.can_confirm)
        self.assertEqual(self.tree_snapshot(self.workspace), before)
        self.assertFalse((self.dream / "runtime").exists())

        run_directory = self.dream / "runtime" / "runs" / RUN_ID
        run_directory.mkdir(parents=True)
        before = self.tree_snapshot(self.workspace)
        waiting = self.reader.read(self.run, thread_id="thread-1")
        self.assertEqual(waiting.run_revision, 0)
        self.assertEqual(waiting.stages, {})
        self.assertFalse(waiting.can_confirm)
        self.assertEqual(self.tree_snapshot(self.workspace), before)

    def test_storage_validation_rejects_camel_case_and_mixed_keys(self) -> None:
        canonical_source = {
            "deck_plugin_binding_id": "binding-1",
            "binding_revision": 3,
            "deck_plugin_version": "1.2.3",
            "deck_runtime_snapshot_id": "snapshot-1",
            "runtime_plugin_lock_id": "lock-1",
        }
        canonical_run = {
            "schema_version": "dream-run/v1",
            "workflow_run_id": RUN_ID,
            "thread_id": "thread-1",
            "source": canonical_source,
            "projection_entry": (
                f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
            ),
            "required_stages": ["characters", "scenes", "storyboards"],
            "revision": 1,
        }
        for invalid in (
            {**canonical_run, "threadId": canonical_run["thread_id"]},
            {
                "schemaVersion": "dream-run/v1",
                "workflowRunId": RUN_ID,
                "threadId": "thread-1",
                "source": {
                    "deckPluginBindingId": "binding-1",
                    "bindingRevision": 3,
                    "deckPluginVersion": "1.2.3",
                    "deckRuntimeSnapshotId": "snapshot-1",
                    "runtimePluginLockId": "lock-1",
                },
                "projectionEntry": (
                    f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
                ),
                "requiredStages": ["characters", "scenes", "storyboards"],
                "revision": 1,
            },
        ):
            with self.subTest(keys=sorted(invalid)):
                with self.assertRaises(ValidationError):
                    StoryWorkspaceDreamRunFile.model_validate(invalid)

        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamStageFile.model_validate({
                "schemaVersion": "dream-stage/v1",
                "workflowRunId": RUN_ID,
                "stage": "characters",
                "revision": 1,
                "sourceFiles": ["assets/characters/lead.md"],
                "page": {
                    "title": "人物",
                    "entryRoute": f"/story-workspace/characters?run={RUN_ID}",
                },
                "items": [{
                    "entityId": "entity-1",
                    "displayName": "Entity",
                    "summary": "summary",
                    "sourceFile": "assets/characters/lead.md",
                    "relations": [],
                }],
            })

    def test_only_real_workflow_run_is_a_trusted_host_source(self) -> None:
        fake = SimpleNamespace(
            workflow_run_id=RUN_ID,
            deck_plugin_binding_id="binding-1",
            binding_revision=3,
            deck_plugin_version="1.2.3",
            deck_runtime_snapshot_id="snapshot-1",
            runtime_plugin_lock_id="lock-1",
        )
        with self.assertRaises(StoryWorkspaceDreamFileError):
            self.writer.write_run(
                fake,
                thread_id="thread-1",
                expected_revision=0,
            )
        self.assertFalse((self.dream / "runtime").exists())

    def test_response_rejects_stage_key_and_nested_stage_mismatch(self) -> None:
        source = StoryWorkspaceDreamSource(
            deck_plugin_binding_id="binding-1",
            binding_revision=3,
            deck_plugin_version="1.2.3",
            deck_runtime_snapshot_id="snapshot-1",
            runtime_plugin_lock_id="lock-1",
        )
        nested = StoryWorkspaceDreamStageResponse(
            stage=StoryWorkspaceDreamStage.SCENES,
            revision=1,
            source_files=["assets/scenes/opening.md"],
            page={
                "title": "场景",
                "entry_route": f"/story-workspace/scenes?run={RUN_ID}",
            },
            items=[],
        )
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamFilesResponse(
                story_workspace_run_id=RUN_ID,
                thread_id="thread-1",
                source=StoryWorkspaceDreamSourceResponse.model_validate(
                    source.model_dump()
                ),
                required_stages=list(StoryWorkspaceDreamStage),
                run_revision=1,
                stages={StoryWorkspaceDreamStage.CHARACTERS: nested},
                can_confirm=False,
            )

    def test_response_rejects_stage_route_for_a_different_outer_run(self) -> None:
        source = StoryWorkspaceDreamSourceResponse(
            deck_plugin_binding_id="binding-1",
            binding_revision=3,
            deck_plugin_version="1.2.3",
            deck_runtime_snapshot_id="snapshot-1",
            runtime_plugin_lock_id="lock-1",
        )
        stage = StoryWorkspaceDreamStageResponse(
            stage=StoryWorkspaceDreamStage.CHARACTERS,
            revision=1,
            source_files=["assets/characters/lead.md"],
            page={
                "title": "人物",
                "entry_route": (
                    f"/story-workspace/characters?run={OTHER_RUN_ID}"
                ),
            },
            items=[self.item("assets/characters/lead.md")],
        )
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamFilesResponse(
                story_workspace_run_id=RUN_ID,
                thread_id="thread-1",
                source=source,
                required_stages=list(StoryWorkspaceDreamStage),
                run_revision=1,
                stages={StoryWorkspaceDreamStage.CHARACTERS: stage},
                can_confirm=False,
            )

    def test_stage_file_rejects_duplicate_entity_ids(self) -> None:
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamStageFile(
                workflow_run_id=RUN_ID,
                stage="characters",
                revision=1,
                source_files=["assets/characters/lead.md"],
                page={
                    "title": "人物",
                    "entry_route": f"/story-workspace/characters?run={RUN_ID}",
                },
                items=[
                    self.item("assets/characters/lead.md", "one"),
                    self.item("assets/characters/lead.md", "two"),
                ],
            )

    def write_stage(
        self,
        stage: StoryWorkspaceDreamStage,
        source_file: str,
        *,
        expected_revision: int = 0,
        summary: str = "summary",
    ) -> StoryWorkspaceDreamStageFile:
        return self.writer.write_stage(
            self.run,
            stage=stage,
            source_files=[source_file],
            items=[self.item(source_file, summary)],
            expected_revision=expected_revision,
        )

    def test_storage_models_are_snake_case_and_wire_models_are_camel_case(self) -> None:
        run_file = StoryWorkspaceDreamRunFile(
            workflow_run_id=RUN_ID,
            thread_id="thread-1",
            source={
                "deck_plugin_binding_id": "binding-1",
                "binding_revision": 3,
                "deck_plugin_version": "1.2.3",
                "deck_runtime_snapshot_id": "snapshot-1",
                "runtime_plugin_lock_id": "lock-1",
            },
            projection_entry=f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files",
            revision=1,
        )
        stored = run_file.model_dump(mode="json")
        self.assertIn("workflow_run_id", stored)
        self.assertIn("deck_plugin_binding_id", stored["source"])
        self.assertNotIn("storyWorkspaceRunId", stored)

        response = StoryWorkspaceDreamFilesResponse(
            story_workspace_run_id=RUN_ID,
            thread_id="thread-1",
            source=StoryWorkspaceDreamSourceResponse.model_validate(
                run_file.source.model_dump()
            ),
            required_stages=list(StoryWorkspaceDreamStage),
            run_revision=1,
            stages={
                StoryWorkspaceDreamStage.CHARACTERS: (
                    StoryWorkspaceDreamStageResponse(
                        stage=StoryWorkspaceDreamStage.CHARACTERS,
                        revision=1,
                        source_files=["assets/characters/lead.md"],
                        page={
                            "title": "人物",
                            "entry_route": (
                                f"/story-workspace/characters?run={RUN_ID}"
                            ),
                        },
                        items=[self.item("assets/characters/lead.md")],
                    )
                )
            },
            can_confirm=False,
        )
        wire = response.model_dump(mode="json", by_alias=True)
        self.assertEqual(wire["storyWorkspaceRunId"], RUN_ID)
        self.assertEqual(wire["threadId"], "thread-1")
        self.assertIn("deckPluginBindingId", wire["source"])
        self.assertIn("requiredStages", wire)
        self.assertEqual(wire["confirmationLabel"], "确认并继续")
        character_wire = wire["stages"]["characters"]
        self.assertIn("sourceFiles", character_wire)
        self.assertIn("entryRoute", character_wire["page"])
        self.assertIn("entityId", character_wire["items"][0])
        self.assertNotIn("entity_id", character_wire["items"][0])

        command = StoryWorkspaceDreamConfirmationCommand.model_validate(
            {
                "storyWorkspaceRunId": RUN_ID,
                "threadId": "thread-1",
                "baseRevisions": {
                    "characters": 1,
                    "scenes": 2,
                    "storyboards": 3,
                },
                "edits": [{
                    "stage": "characters",
                    "entityId": "entity-1",
                    "fields": {"summary": "updated"},
                }],
                "idempotencyKey": "swc_12345678-1234-1234-1234-123456789abc",
            }
        )
        self.assertEqual(command.edits[0].entity_id, "entity-1")
        self.assertEqual(
            command.model_dump(mode="json", by_alias=True)["baseRevisions"][
                "characters"
            ],
            1,
        )
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamEdit(
                stage="characters", entity_id="entity-1", fields={}
            )

    def test_first_write_replay_conflict_and_monotonic_run_revision(self) -> None:
        first = self.initialize_run()
        self.assertEqual(first.revision, 1)
        run_path = self.dream / "runtime" / "runs" / RUN_ID / "run.json"
        raw = json.loads(run_path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], "dream-run/v1")
        self.assertEqual(raw["workflow_run_id"], RUN_ID)
        self.assertNotIn("storyWorkspaceRunId", raw)

        with self.assertRaises(StoryWorkspaceDreamFileConflict) as raised:
            self.initialize_run()
        self.assertEqual(raised.exception.current_revision, 1)

        second = self.writer.write_run(
            self.run, thread_id="thread-1", expected_revision=1
        )
        self.assertEqual(second.revision, 2)
        self.assertEqual(
            self.reader.read_run(self.run, thread_id="thread-1").revision, 2
        )

    def test_missing_stages_are_waiting_and_all_three_enable_confirmation(self) -> None:
        self.initialize_run()
        waiting = self.reader.read(self.run, thread_id="thread-1")
        self.assertIsInstance(waiting, StoryWorkspaceDreamFilesResponse)
        self.assertEqual(waiting.stages, {})
        self.assertFalse(waiting.can_confirm)

        stage_sources = {
            StoryWorkspaceDreamStage.CHARACTERS: "assets/characters/lead.md",
            StoryWorkspaceDreamStage.SCENES: "assets/scenes/opening.md",
            StoryWorkspaceDreamStage.STORYBOARDS: (
                "stories/demo/episodes/EP01/storyboard.yaml"
            ),
        }
        expected: set[StoryWorkspaceDreamStage] = set()
        for stage, source_file in stage_sources.items():
            written = self.write_stage(stage, source_file)
            self.assertEqual(written.revision, 1)
            expected.add(stage)
            partial = self.reader.read(self.run, thread_id="thread-1")
            self.assertEqual(set(partial.stages), expected)

        complete = self.reader.read(self.run, thread_id="thread-1")
        self.assertEqual(set(complete.stages), set(StoryWorkspaceDreamStage))
        self.assertTrue(complete.can_confirm)

    def test_stage_revision_conflict_and_increment(self) -> None:
        self.initialize_run()
        first = self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS, "assets/characters/lead.md"
        )
        self.assertEqual(first.revision, 1)
        with self.assertRaises(StoryWorkspaceDreamFileConflict):
            self.write_stage(
                StoryWorkspaceDreamStage.CHARACTERS, "assets/characters/lead.md"
            )
        second = self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
            expected_revision=1,
            summary="new",
        )
        self.assertEqual(second.revision, 2)

    def test_invalid_stage_filename_and_run_mismatch_fail_closed(self) -> None:
        self.initialize_run()
        with self.assertRaises((ValueError, StoryWorkspaceDreamFileError)):
            self.writer.write_stage(
                self.run,
                stage="shots",
                source_files=["assets/characters/lead.md"],
                items=[self.item("assets/characters/lead.md")],
                expected_revision=0,
            )
        with self.assertRaises(StoryWorkspaceDreamPathError):
            self.writer.write_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
                filename="scenes.json",
                source_files=["assets/characters/lead.md"],
                items=[self.item("assets/characters/lead.md")],
                expected_revision=0,
            )
        with self.assertRaises(StoryWorkspaceDreamPathError):
            self.reader.read_stage_file(self.run, filename="run.json")

        stage_path = (
            self.dream
            / "runtime"
            / "runs"
            / RUN_ID
            / "stages"
            / "characters.json"
        )
        stage_path.parent.mkdir()
        stage_path.write_text(json.dumps({
            "schema_version": "dream-stage/v1",
            "workflow_run_id": OTHER_RUN_ID,
            "stage": "characters",
            "revision": 1,
            "source_files": ["assets/characters/lead.md"],
            "page": {
                "title": "人物",
                "entry_route": f"/story-workspace/characters?run={OTHER_RUN_ID}",
            },
            "items": [self.item("assets/characters/lead.md")],
        }), encoding="utf-8")
        with self.assertRaises(StoryWorkspaceDreamFileError):
            self.reader.read(self.run, thread_id="thread-1")

    def test_unsafe_source_paths_and_symlink_escape_are_rejected(self) -> None:
        self.initialize_run()
        outside_descriptor, outside_name = tempfile.mkstemp(
            prefix="dream-outside-",
            suffix=".txt",
            dir=Path(self.temporary_directory.name).parent,
        )
        os.close(outside_descriptor)
        outside = Path(outside_name)
        outside.write_text("outside", encoding="utf-8")
        link = self.workspace / "assets" / "characters" / "escape.md"
        try:
            link.symlink_to(outside)
            for unsafe in (
                "../outside.txt",
                str(outside.resolve()),
                "assets\\characters\\lead.md",
                "assets/characters/escape.md",
            ):
                with self.subTest(path=unsafe):
                    with self.assertRaises(StoryWorkspaceDreamPathError):
                        self.writer.write_stage(
                            self.run,
                            stage=StoryWorkspaceDreamStage.CHARACTERS,
                            source_files=[unsafe],
                            items=[self.item(unsafe)],
                            expected_revision=0,
                        )
        finally:
            outside.unlink(missing_ok=True)

    def test_source_directory_swap_to_internal_symlink_is_rejected(self) -> None:
        self.initialize_run()
        assets = self.workspace / "assets"
        displaced_assets = self.workspace / "assets-original"
        replacement_assets = self.workspace / "replacement-assets"
        (replacement_assets / "characters").mkdir(parents=True)
        (replacement_assets / "characters" / "lead.md").write_text(
            "replacement source\n",
            encoding="utf-8",
        )
        original_validate = self.writer._validate_source_files
        replaced = False

        def replace_before_source_access(stage_file, *args):
            nonlocal replaced
            if not replaced:
                replaced = True
                assets.rename(displaced_assets)
                assets.symlink_to(replacement_assets, target_is_directory=True)
            return original_validate(stage_file, *args)

        with patch.object(
            self.writer,
            "_validate_source_files",
            side_effect=replace_before_source_access,
        ):
            with self.assertRaises(StoryWorkspaceDreamPathError):
                self.writer.write_stage(
                    self.run,
                    stage=StoryWorkspaceDreamStage.CHARACTERS,
                    source_files=["assets/characters/lead.md"],
                    items=[self.item("assets/characters/lead.md")],
                    expected_revision=0,
                )

        stage_file = (
            self.dream / "runtime" / "runs" / RUN_ID / "stages" / "characters.json"
        )
        self.assertFalse(stage_file.exists())

    def test_protocol_directory_symlink_escape_is_rejected(self) -> None:
        outside = self.workspace / "outside-runtime"
        outside.mkdir()
        (self.dream / "runtime").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(StoryWorkspaceDreamPathError):
            self.initialize_run()
        self.assertEqual(list(outside.iterdir()), [])

    def test_writer_never_changes_static_dream_files(self) -> None:
        before = {
            name: (self.dream / name).read_bytes()
            for name in ("README.md", "workspace.json")
        }
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS, "assets/characters/lead.md"
        )
        after = {
            name: (self.dream / name).read_bytes()
            for name in ("README.md", "workspace.json")
        }
        self.assertEqual(after, before)

    def test_malformed_oversized_and_item_overflow_files_fail_closed(self) -> None:
        self.initialize_run()
        stages = self.dream / "runtime" / "runs" / RUN_ID / "stages"
        stages.mkdir()
        characters = stages / "characters.json"
        characters.write_text("{not-json", encoding="utf-8")
        with self.assertRaises(StoryWorkspaceDreamFileError):
            self.reader.read(self.run, thread_id="thread-1")

        characters.write_bytes(b" " * (STORY_WORKSPACE_DREAM_FILE_MAX_BYTES + 1))
        with self.assertRaises(StoryWorkspaceDreamFileError):
            self.reader.read(self.run, thread_id="thread-1")

        characters.unlink()
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamStageFile(
                workflow_run_id=RUN_ID,
                stage="characters",
                revision=1,
                source_files=["assets/characters/lead.md"],
                page={
                    "title": "人物",
                    "entry_route": f"/story-workspace/characters?run={RUN_ID}",
                },
                items=[self.item("assets/characters/lead.md")
                       for _ in range(STORY_WORKSPACE_DREAM_ITEMS_MAX + 1)],
            )
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamRunFile(
                workflow_run_id=RUN_ID,
                thread_id="thread-1",
                source={
                    "deck_plugin_binding_id": "binding-1",
                    "binding_revision": True,
                    "deck_plugin_version": "1.2.3",
                    "deck_runtime_snapshot_id": "snapshot-1",
                    "runtime_plugin_lock_id": "lock-1",
                },
                projection_entry=(
                    f"/api/story-workspace/workflow-runs/{RUN_ID}/dream-files"
                ),
                revision=1,
            )
        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamConfirmationCommand.model_validate({
                "storyWorkspaceRunId": RUN_ID,
                "threadId": "thread-1",
                "baseRevisions": {
                    "characters": True,
                    "scenes": 1,
                    "storyboards": 1,
                },
                "edits": [],
                "idempotencyKey": "swc_strict",
            })

    def test_write_exception_preserves_old_file_and_cleans_temporary_file(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS, "assets/characters/lead.md"
        )
        stage_directory = self.dream / "runtime" / "runs" / RUN_ID / "stages"
        target = stage_directory / "characters.json"
        before = target.read_bytes()

        with patch(
            "services.story_workspace.dream_file_service.os.replace",
            side_effect=OSError("injected replace failure"),
        ):
            with self.assertRaises(dream_files.StoryWorkspaceDreamIOError):
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="must-not-land",
                )

        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(list(stage_directory.glob("*.tmp")), [])

        real_replace = os.replace
        call_count = 0

        def replace_then_raise(*args: object, **kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            real_replace(*args, **kwargs)
            if call_count == 1:
                raise OSError("injected post-replace failure")

        with patch(
            "services.story_workspace.dream_file_service.os.replace",
            side_effect=replace_then_raise,
        ):
            with self.assertRaises(dream_files.StoryWorkspaceDreamIOError):
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="also-must-not-land",
                )

        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(list(stage_directory.glob("*.tmp")), [])

    def test_same_expected_revision_has_exactly_one_concurrent_winner(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS, "assets/characters/lead.md"
        )

        def update(summary: str) -> object:
            try:
                return self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary=summary,
                )
            except Exception as exc:  # Captured for exact winner/loser assertions.
                return exc

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(update, ("one", "two")))

        winners = [x for x in results if isinstance(x, StoryWorkspaceDreamStageFile)]
        losers = [x for x in results if isinstance(x, StoryWorkspaceDreamFileConflict)]
        self.assertEqual(len(winners), 1)
        self.assertEqual(len(losers), 1)
        self.assertEqual(
            self.reader.read_stage(
                self.run, stage=StoryWorkspaceDreamStage.CHARACTERS
            ).revision,
            2,
        )

    def test_cross_process_cas_has_exactly_one_winner(self) -> None:
        if not getattr(
            dream_files,
            "STORY_WORKSPACE_DREAM_PLATFORM_SUPPORTED",
            False,
        ):
            self.skipTest("Dream runtime requires secure Unix dirfd capabilities")
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS, "assets/characters/lead.md"
        )
        context = multiprocessing.get_context("spawn")
        ready = context.Queue()
        start = context.Event()
        results = context.Queue()

        processes = [
            context.Process(
                target=cross_process_stage_update,
                args=(
                    str(self.workspace),
                    self.run,
                    ready,
                    start,
                    results,
                    summary,
                ),
            )
            for summary in ("process-one", "process-two")
        ]
        for process in processes:
            process.start()
        for _ in processes:
            self.assertTrue(ready.get(timeout=5))
        start.set()
        for process in processes:
            process.join(timeout=10)
            self.assertFalse(process.is_alive())
            self.assertEqual(process.exitcode, 0)

        outcomes = sorted(results.get(timeout=5) for _ in processes)
        self.assertEqual(outcomes, ["conflict", "written"])
        self.assertEqual(
            self.reader.read_stage(
                self.run, stage=StoryWorkspaceDreamStage.CHARACTERS
            ).revision,
            2,
        )

    def test_reader_compares_source_and_thread_to_authoritative_context(self) -> None:
        self.initialize_run()
        run_path = self.dream / "runtime" / "runs" / RUN_ID / "run.json"
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        payload["source"]["runtime_plugin_lock_id"] = "client-forged-lock"
        run_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(StoryWorkspaceDreamFileError):
            self.reader.read(self.run, thread_id="thread-1")

        payload["source"]["runtime_plugin_lock_id"] = "lock-1"
        payload["thread_id"] = "other-thread"
        run_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(StoryWorkspaceDreamFileError):
            self.reader.read(self.run, thread_id="thread-1")

        payload["thread_id"] = "thread-1"
        run_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(StoryWorkspaceDreamFileError):
            self.reader.read(
                authoritative_run(deck_plugin_binding_id="other-binding"),
                thread_id="thread-1",
            )

    def test_all_stage_entrypoints_reject_tampered_run_thread_without_mutation(
        self,
    ) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        run_path = self.dream / "runtime" / "runs" / RUN_ID / "run.json"
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        payload["thread_id"] = "attacker-thread"
        run_path.write_text(json.dumps(payload), encoding="utf-8")
        before = self.tree_snapshot(self.workspace)

        operations = {
            "read_stage": lambda: self.reader.read_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
            ),
            "read_stage_file": lambda: self.reader.read_stage_file(
                self.run,
                filename="characters.json",
            ),
            "write_stage": lambda: self.write_stage(
                StoryWorkspaceDreamStage.CHARACTERS,
                "assets/characters/lead.md",
                expected_revision=1,
                summary="must-not-land",
            ),
        }
        for name, operation in operations.items():
            with self.subTest(entrypoint=name):
                with self.assertRaises(StoryWorkspaceDreamFileError):
                    operation()
                self.assertEqual(self.tree_snapshot(self.workspace), before)

    def test_all_stage_entrypoints_reject_authoritative_run_without_thread(
        self,
    ) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        no_thread_run = authoritative_run(source_voice_thread_id=None)
        before = self.tree_snapshot(self.workspace)

        operations = {
            "read_stage": lambda: self.reader.read_stage(
                no_thread_run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
            ),
            "read_stage_file": lambda: self.reader.read_stage_file(
                no_thread_run,
                filename="characters.json",
            ),
            "write_stage": lambda: self.writer.write_stage(
                no_thread_run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
                source_files=["assets/characters/lead.md"],
                items=[self.item("assets/characters/lead.md", "must-not-land")],
                expected_revision=1,
            ),
        }
        for name, operation in operations.items():
            with self.subTest(entrypoint=name):
                with self.assertRaises(StoryWorkspaceDreamFileError):
                    operation()
                self.assertEqual(self.tree_snapshot(self.workspace), before)

    def test_write_stage_authorizes_thread_before_probing_source_paths(self) -> None:
        self.initialize_run()
        run_path = self.dream / "runtime" / "runs" / RUN_ID / "run.json"
        payload = json.loads(run_path.read_text(encoding="utf-8"))
        payload["thread_id"] = "attacker-thread"
        run_path.write_text(json.dumps(payload), encoding="utf-8")
        before = self.tree_snapshot(self.workspace)

        with patch.object(
            self.writer,
            "_validate_source_files",
            wraps=self.writer._validate_source_files,
        ) as validate_source_files:
            with self.assertRaises(StoryWorkspaceDreamFileError) as raised:
                self.writer.write_stage(
                    self.run,
                    stage=StoryWorkspaceDreamStage.CHARACTERS,
                    source_files=["private/probe.md"],
                    items=[self.item("private/probe.md")],
                    expected_revision=0,
                )
            validate_source_files.assert_not_called()
            self.assertIn("thread", str(raised.exception))

        self.assertEqual(self.tree_snapshot(self.workspace), before)

    def test_run_directory_replacement_before_read_fails_closed(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        run_directory = self.dream / "runtime" / "runs" / RUN_ID
        displaced = run_directory.with_name(f"{RUN_ID}.read-displaced")
        original_flock = dream_files.fcntl.flock
        replaced = False

        def replace_after_lock(descriptor: int, operation: int) -> object:
            nonlocal replaced
            result = original_flock(descriptor, operation)
            if not replaced and operation in {
                dream_files.fcntl.LOCK_SH,
                dream_files.fcntl.LOCK_EX,
            }:
                replaced = True
                run_directory.rename(displaced)
                shutil.copytree(displaced, run_directory)
            return result

        with patch.object(
            dream_files.fcntl,
            "flock",
            side_effect=replace_after_lock,
        ):
            with self.assertRaises(StoryWorkspaceDreamPathError):
                self.reader.read(self.run, thread_id="thread-1")

        visible = json.loads(
            (run_directory / "stages" / "characters.json").read_text()
        )
        self.assertEqual(visible["revision"], 1)

    def test_run_directory_replacement_before_cas_write_fails_closed(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        run_directory = self.dream / "runtime" / "runs" / RUN_ID
        displaced = run_directory.with_name(f"{RUN_ID}.write-displaced")
        original_flock = dream_files.fcntl.flock
        replaced = False

        def replace_after_lock(descriptor: int, operation: int) -> object:
            nonlocal replaced
            result = original_flock(descriptor, operation)
            if not replaced and operation == dream_files.fcntl.LOCK_EX:
                replaced = True
                run_directory.rename(displaced)
                shutil.copytree(displaced, run_directory)
            return result

        with patch.object(
            dream_files.fcntl,
            "flock",
            side_effect=replace_after_lock,
        ):
            with self.assertRaises(StoryWorkspaceDreamPathError):
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="must-not-reach-replacement",
                )

        visible = json.loads(
            (run_directory / "stages" / "characters.json").read_text()
        )
        self.assertEqual(visible["revision"], 1)

    def test_stage_directory_replacement_before_commit_fails_closed(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        stages = self.dream / "runtime" / "runs" / RUN_ID / "stages"
        displaced = stages.with_name("stages.commit-displaced")
        target = stages / "characters.json"
        old_bytes = target.read_bytes()
        original_write_temp = type(self.writer)._write_temp
        replaced = False

        def replace_after_temp(
            directory_descriptor: int,
            temporary_name: str,
            payload: bytes,
        ) -> None:
            nonlocal replaced
            original_write_temp(directory_descriptor, temporary_name, payload)
            if not replaced:
                replaced = True
                stages.rename(displaced)
                stages.mkdir()
                (stages / "characters.json").write_bytes(old_bytes)

        with patch.object(
            type(self.writer),
            "_write_temp",
            side_effect=replace_after_temp,
        ):
            with self.assertRaises(StoryWorkspaceDreamPathError):
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="must-not-commit-off-path",
                )

        visible = json.loads(target.read_text())
        self.assertEqual(visible["revision"], 1)

    def test_rollback_replace_failure_is_durability_indeterminate(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        original_fsync = os.fsync
        original_replace = os.replace
        replace_calls = 0

        def fail_directory_fsync(descriptor: int) -> None:
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError("injected main directory fsync failure")
            original_fsync(descriptor)

        def fail_rollback_replace(*args: object, **kwargs: object) -> None:
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 1:
                original_replace(*args, **kwargs)
                return
            raise OSError("injected rollback replace failure")

        with patch.object(os, "fsync", side_effect=fail_directory_fsync), patch.object(
            os,
            "replace",
            side_effect=fail_rollback_replace,
        ):
            with self.assertRaises(
                dream_files.StoryWorkspaceDreamDurabilityIndeterminate
            ) as raised:
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="new-visible",
                )

        self.assertEqual(raised.exception.observed_revision, 2)
        self.assertEqual(
            raised.exception.state_hint,
            "replacement-visible-rollback-failed",
        )
        self.assertEqual(
            self.reader.read_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
            ).revision,
            2,
        )

    def test_rollback_directory_fsync_failure_is_indeterminate(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        original_fsync = os.fsync

        def fail_directory_fsync(descriptor: int) -> None:
            if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise OSError("injected directory fsync failure")
            original_fsync(descriptor)

        with patch.object(os, "fsync", side_effect=fail_directory_fsync):
            with self.assertRaises(
                dream_files.StoryWorkspaceDreamDurabilityIndeterminate
            ) as raised:
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="rolled-back-visible",
                )

        self.assertEqual(raised.exception.observed_revision, 1)
        self.assertEqual(
            raised.exception.state_hint,
            "rollback-visible-durability-unknown",
        )
        self.assertEqual(
            self.reader.read_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
            ).revision,
            1,
        )

    def test_visible_stage_swap_after_directory_fsync_is_indeterminate(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        stages = self.dream / "runtime" / "runs" / RUN_ID / "stages"
        displaced = stages.with_name("stages.fsync-displaced")
        visible_target = stages / "characters.json"
        old_bytes = visible_target.read_bytes()
        original_fsync = os.fsync
        swapped = False

        def fsync_then_swap_visible_stages(descriptor: int) -> None:
            nonlocal swapped
            original_fsync(descriptor)
            if not swapped and stat.S_ISDIR(os.fstat(descriptor).st_mode):
                swapped = True
                stages.rename(displaced)
                stages.mkdir()
                visible_target.write_bytes(old_bytes)

        with patch.object(os, "fsync", side_effect=fsync_then_swap_visible_stages):
            with self.assertRaises(
                dream_files.StoryWorkspaceDreamDurabilityIndeterminate
            ) as raised:
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="durable-in-pinned-directory",
                )

        self.assertEqual(raised.exception.pinned_observed_revision, 2)
        self.assertEqual(raised.exception.visible_observed_revision, 1)
        self.assertEqual(
            raised.exception.state_hint,
            "pinned-commit-visible-directory-replaced",
        )
        self.assertEqual(
            json.loads((displaced / "characters.json").read_text())["revision"],
            2,
        )
        self.assertEqual(
            self.reader.read_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
            ).revision,
            1,
        )

    def test_visible_run_swap_after_directory_fsync_uses_root_tree(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        runs = self.dream / "runtime" / "runs"
        run_directory = runs / RUN_ID
        visible_snapshot = runs / f"{RUN_ID}.root-visible-snapshot"
        displaced = runs / f"{RUN_ID}.fsync-displaced"
        shutil.copytree(run_directory, visible_snapshot)
        original_fsync = os.fsync
        swapped = False

        def fsync_then_swap_visible_run(descriptor: int) -> None:
            nonlocal swapped
            original_fsync(descriptor)
            if not swapped and stat.S_ISDIR(os.fstat(descriptor).st_mode):
                swapped = True
                run_directory.rename(displaced)
                visible_snapshot.rename(run_directory)

        with patch.object(os, "fsync", side_effect=fsync_then_swap_visible_run):
            with self.assertRaises(
                dream_files.StoryWorkspaceDreamDurabilityIndeterminate
            ) as raised:
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="durable-in-displaced-run",
                )

        self.assertEqual(raised.exception.pinned_observed_revision, 2)
        self.assertEqual(raised.exception.visible_observed_revision, 1)
        self.assertEqual(
            raised.exception.state_hint,
            "pinned-commit-visible-directory-replaced",
        )
        self.assertEqual(
            json.loads(
                (displaced / "stages" / "characters.json").read_text()
            )["revision"],
            2,
        )
        self.assertEqual(
            self.reader.read_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
            ).revision,
            1,
        )

    def test_durable_commit_cleanup_failure_warns_and_returns_revision(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        with patch.object(
            os,
            "unlink",
            side_effect=OSError("injected post-commit cleanup failure"),
        ):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                committed = self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="durably-committed",
                )

        self.assertEqual(committed.revision, 2)
        self.assertTrue(
            any("cleanup" in str(warning.message).lower() for warning in caught)
        )
        self.assertEqual(
            self.reader.read_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
            ).revision,
            2,
        )

    def test_cleanup_error_does_not_mask_primary_replace_error(self) -> None:
        self.initialize_run()
        self.write_stage(
            StoryWorkspaceDreamStage.CHARACTERS,
            "assets/characters/lead.md",
        )
        with patch.object(
            os,
            "replace",
            side_effect=OSError("primary replace failure"),
        ), patch.object(
            os,
            "unlink",
            side_effect=OSError("secondary cleanup failure"),
        ):
            with self.assertRaises(
                dream_files.StoryWorkspaceDreamIOError
            ) as raised:
                self.write_stage(
                    StoryWorkspaceDreamStage.CHARACTERS,
                    "assets/characters/lead.md",
                    expected_revision=1,
                    summary="must-not-land",
                )
        self.assertIsInstance(raised.exception.__cause__, OSError)
        self.assertIn("primary replace failure", str(raised.exception.__cause__))

    def test_platform_capability_missing_fails_fast_at_construction(self) -> None:
        with patch.object(dream_files, "fcntl", None):
            with self.assertRaises(
                dream_files.StoryWorkspaceDreamPlatformUnsupported
            ):
                StoryWorkspaceDreamFileReader(self.workspace)
            with self.assertRaises(
                dream_files.StoryWorkspaceDreamPlatformUnsupported
            ):
                StoryWorkspaceDreamFileWriter(self.workspace)
        self.assertFalse((self.dream / "runtime").exists())

    def test_wire_stage_direct_construction_enforces_storage_invariants(self) -> None:
        valid = {
            "stage": "characters",
            "revision": 1,
            "sourceFiles": ["assets/characters/lead.md"],
            "page": {
                "title": "人物",
                "entryRoute": f"/story-workspace/characters?run={RUN_ID}",
            },
            "items": [{
                "entityId": "entity-1",
                "displayName": "Entity",
                "summary": "summary",
                "sourceFile": "assets/characters/lead.md",
                "relations": [],
            }],
        }
        invalid_variants = {
            "external-route": {
                **valid,
                "page": {"title": "人物", "entryRoute": "https://evil.invalid"},
            },
            "duplicate-source": {
                **valid,
                "sourceFiles": [
                    "assets/characters/lead.md",
                    "assets/characters/lead.md",
                ],
            },
            "undeclared-item-source": {
                **valid,
                "items": [{**valid["items"][0], "sourceFile": "private/other.md"}],
            },
            "empty-relation": {
                **valid,
                "items": [{**valid["items"][0], "relations": [""]}],
            },
            "duplicate-entity": {
                **valid,
                "items": [valid["items"][0], valid["items"][0]],
            },
        }
        for name, payload in invalid_variants.items():
            with self.subTest(case=name):
                with self.assertRaises(ValidationError):
                    StoryWorkspaceDreamStageResponse.model_validate(payload)

        with self.assertRaises(ValidationError):
            StoryWorkspaceDreamSourceResponse(
                deck_plugin_binding_id="",
                binding_revision=1,
                deck_plugin_version="1",
                deck_runtime_snapshot_id="snapshot",
                runtime_plugin_lock_id="lock",
            )

    def test_service_wraps_contract_validation_and_reclaims_local_lock(self) -> None:
        self.initialize_run()
        with self.assertRaises(
            dream_files.StoryWorkspaceDreamContractError
        ) as raised:
            self.writer.write_stage(
                self.run,
                stage=StoryWorkspaceDreamStage.CHARACTERS,
                source_files=["assets/characters/lead.md"],
                items=[
                    self.item("assets/characters/lead.md", "one"),
                    self.item("assets/characters/lead.md", "two"),
                ],
                expected_revision=0,
            )
        self.assertIsInstance(raised.exception.__cause__, ValidationError)
        self.reader.read(self.run, thread_id="thread-1")
        self.assertEqual(dream_files._THREAD_LOCKS, {})

    def test_reader_uses_shared_process_lock(self) -> None:
        self.initialize_run()
        operations: list[int] = []
        original_flock = dream_files.fcntl.flock

        def record_flock(descriptor: int, operation: int) -> object:
            operations.append(operation)
            return original_flock(descriptor, operation)

        with patch.object(
            dream_files.fcntl,
            "flock",
            side_effect=record_flock,
        ):
            self.reader.read(self.run, thread_id="thread-1")
        self.assertIn(dream_files.fcntl.LOCK_SH, operations)

    def test_unlock_failure_is_public_io_error_and_descriptor_is_closed(self) -> None:
        self.initialize_run()
        original_flock = dream_files.fcntl.flock
        locked_descriptors: list[int] = []

        def fail_unlock(descriptor: int, operation: int) -> object:
            if operation == dream_files.fcntl.LOCK_UN:
                raise OSError("injected unlock failure")
            locked_descriptors.append(descriptor)
            return original_flock(descriptor, operation)

        with patch.object(
            dream_files.fcntl,
            "flock",
            side_effect=fail_unlock,
        ):
            with self.assertRaises(dream_files.StoryWorkspaceDreamIOError) as raised:
                self.reader.read(self.run, thread_id="thread-1")

        self.assertIsInstance(raised.exception.__cause__, OSError)
        self.assertEqual(dream_files._THREAD_LOCKS, {})
        for descriptor in locked_descriptors:
            with self.assertRaises(OSError):
                os.fstat(descriptor)


if __name__ == "__main__":
    unittest.main()
