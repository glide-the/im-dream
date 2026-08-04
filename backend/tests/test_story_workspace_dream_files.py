"""Dream runtime file protocol contract and filesystem safety tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

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
    StoryWorkspaceDreamStage,
    StoryWorkspaceDreamStageFile,
)


RUN_ID = "run_0123456789abcdef0123456789abcdef"
OTHER_RUN_ID = "run_fedcba9876543210fedcba9876543210"


def authoritative_run(run_id: str = RUN_ID, **overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "workflow_run_id": run_id,
        "deck_plugin_binding_id": "binding-1",
        "binding_revision": 3,
        "deck_plugin_version": "1.2.3",
        "deck_runtime_snapshot_id": "snapshot-1",
        "runtime_plugin_lock_id": "lock-1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


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
            source=run_file.source,
            required_stages=list(StoryWorkspaceDreamStage),
            stages={},
            can_confirm=False,
        )
        wire = response.model_dump(mode="json", by_alias=True)
        self.assertEqual(wire["storyWorkspaceRunId"], RUN_ID)
        self.assertEqual(wire["threadId"], "thread-1")
        self.assertIn("deckPluginBindingId", wire["source"])
        self.assertIn("requiredStages", wire)
        self.assertEqual(wire["confirmationLabel"], "确认并继续")

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
        outside = Path(self.temporary_directory.name).parent / "dream-outside.txt"
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
            with self.assertRaises(OSError):
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
            with self.assertRaises(OSError):
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


if __name__ == "__main__":
    unittest.main()
