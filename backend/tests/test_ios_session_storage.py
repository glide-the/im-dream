# [Input] Original resume lookup and isolated iOS container-layout fixtures.
# [Output] Verify exclusive project relocation, unchanged transcript bytes and foreign-path rejection.
# [Pos] Provider-free filesystem compatibility checks; no account, database or model access.
# [Sync] 2026-10-25: cover consecutive Data/Bundle container relocations while original JSONL cwd remains unchanged.
# [Sync] 2026-10-26: reject locations outside the App data root and preserve descriptor traversal without system ancestor reads.
import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import tests._sdk_stubs  # noqa: F401
from libs.claude_agent_kit.server import session_files as storage
from mobile_runtime import ios_session_storage as compatibility


SESSION = "44444444-4444-4444-8444-444444444444"
PREVIOUS = "11111111-1111-4111-8111-111111111111"
CURRENT = "22222222-2222-4222-8222-222222222222"
FOLLOWING = "33333333-3333-4333-8333-333333333333"


class ContainerLocationTests(unittest.TestCase):
    def test_only_application_container_uuid_may_change(self):
        for kind in ("Data", "Bundle"):
            before = f"/fixture/Containers/{kind}/Application/{PREVIOUS}/same/项目😀"
            after = before.replace(PREVIOUS, CURRENT)
            self.assertTrue(compatibility._same_container_location(before, after))
            self.assertFalse(compatibility._same_container_location(before, after + "/other"))
            self.assertFalse(compatibility._same_container_location(before, after.replace("same", "foreign")))
            self.assertFalse(compatibility._same_container_location(before, before))
            self.assertFalse(compatibility._same_container_location(before, after.replace(CURRENT, "invalid")))


class ApplicationDirectoryTests(unittest.TestCase):
    def test_directory_walk_starts_inside_application_and_rejects_links(self):
        with tempfile.TemporaryDirectory(prefix="ink-ios-directory-root-") as temporary:
            root = Path(temporary).resolve()
            target = root / "owned" / "projects"
            target.mkdir(parents=True)
            original_open = os.open
            opened = []

            def guarded_open(path, *args, **kwargs):
                opened.append(path)
                if str(path) == "/":
                    raise PermissionError("system ancestors are outside the fixture application")
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "home", return_value=root), patch.object(os, "open", side_effect=guarded_open):
                descriptor = compatibility._open_directory(target)
                try:
                    self.assertEqual(os.fstat(descriptor).st_ino, target.stat().st_ino)
                finally:
                    os.close(descriptor)
                self.assertEqual(opened[0], root)
                with self.assertRaises(ValueError):
                    compatibility._open_directory(root.parent)
                (root / "linked").symlink_to(root / "owned", target_is_directory=True)
                with self.assertRaises(OSError):
                    compatibility._open_directory(root / "linked" / "projects")


@unittest.skipUnless(hasattr(ctypes.CDLL(None), "renameatx_np"), "Darwin exclusive rename required")
class IOSSessionStorageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ink-ios-session-layout-")
        self.addCleanup(temporary.cleanup)
        self.fixture_root = Path(temporary.name).resolve()
        self.cwd = (self.fixture_root / "Containers/Data/Application" / CURRENT
                    / "Library/Application Support/InkMemory/runtime/workspaces/thread-fixture-项目😀")
        self.home = self.cwd / ".claude-home"
        self.application_root = self.fixture_root / "Containers/Data/Application" / CURRENT
        home = patch.object(Path, "home", side_effect=lambda: self.application_root)
        home.start()
        self.addCleanup(home.stop)
        self.projects = self.home / "projects"
        self.projects.mkdir(parents=True)
        platform = patch.object(sys, "platform", "ios")
        platform.start()
        self.addCleanup(platform.stop)
        self.previous_cwd = str(self.cwd).replace(CURRENT, PREVIOUS)
        self.previous = self.projects / storage._runtime_project_name(self.previous_cwd)
        self.current = self.projects / storage._runtime_project_name(str(self.cwd))

    def write(self, cwd=None, directory=None, session_id=SESSION):
        directory = directory or self.previous
        directory.mkdir(exist_ok=True)
        record = directory / (SESSION + ".jsonl")
        record.write_text(json.dumps({"type": "user", "uuid": "fixture-message", "sessionId": session_id,
                                     "cwd": cwd or self.previous_cwd, "message": {"role": "user", "content": "fixture"}}) + "\n")
        return record

    def probe(self):
        return storage.locate_resumable_session(SESSION, cwd=str(self.cwd), config_home=str(self.home))

    def test_relocation_preserves_record_and_inode(self):
        original = self.write()
        before, identity = original.read_bytes(), original.stat().st_ino
        located = Path(self.probe())
        self.assertEqual(located, self.current / original.name)
        self.assertEqual(located.read_bytes(), before)
        self.assertEqual(located.stat().st_ino, identity)
        self.assertFalse(self.previous.exists())
        self.assertEqual(self.probe(), str(located))

    def test_second_data_container_relocation_preserves_original_record(self):
        original = self.write()
        body, inode = original.read_bytes(), original.stat().st_ino
        self.assertIsNotNone(self.probe())
        following_cwd = Path(str(self.cwd).replace(CURRENT, FOLLOWING))
        following_cwd.parent.mkdir(parents=True)
        self.cwd.rename(following_cwd)
        following_home = following_cwd / ".claude-home"
        self.application_root = self.fixture_root / "Containers/Data/Application" / FOLLOWING
        located = storage.locate_resumable_session(
            SESSION, cwd=str(following_cwd), config_home=str(following_home),
        )
        expected = following_home / "projects" / storage._runtime_project_name(str(following_cwd)) / original.name
        self.assertEqual(located, str(expected))
        self.assertEqual(expected.read_bytes(), body)
        self.assertEqual(expected.stat().st_ino, inode)

    def test_second_bundle_container_relocation_preserves_original_record(self):
        previous = self.fixture_root / "Containers/Bundle/Application" / PREVIOUS / "InkMemory.app/app"
        current = Path(str(previous).replace(PREVIOUS, CURRENT))
        following = Path(str(previous).replace(PREVIOUS, FOLLOWING))
        current.mkdir(parents=True)
        following.mkdir(parents=True)
        original = self.write(cwd=str(previous), directory=self.projects / storage._runtime_project_name(str(previous)))
        body, inode = original.read_bytes(), original.stat().st_ino
        self.assertIsNotNone(storage.locate_resumable_session(
            SESSION, cwd=str(current), config_home=str(self.home),
        ))
        located = storage.locate_resumable_session(
            SESSION, cwd=str(following), config_home=str(self.home),
        )
        expected = self.projects / storage._runtime_project_name(str(following)) / original.name
        self.assertEqual(located, str(expected))
        self.assertEqual(expected.read_bytes(), body)
        self.assertEqual(expected.stat().st_ino, inode)

    def test_foreign_cwd_or_directory_is_not_adopted(self):
        for cwd, directory in ((self.previous_cwd + "/foreign", self.previous),
                               (self.previous_cwd, self.projects / "foreign-project")):
            with self.subTest(directory=directory.name):
                record = self.write(cwd=cwd, directory=directory)
                self.assertIsNone(self.probe())
                self.assertTrue(record.exists())
                record.unlink()
                directory.rmdir()

    def test_encoded_container_uuid_does_not_adopt_a_foreign_project(self):
        foreign_cwd = self.previous_cwd.replace("/workspaces/", "/foreign-workspaces/")
        foreign = self.projects / storage._runtime_project_name(foreign_cwd)
        record = self.write(directory=foreign)
        self.assertIsNone(self.probe())
        self.assertTrue(record.exists())

    def test_record_identity_and_corruption_fail_closed(self):
        record = self.write(session_id=PREVIOUS)
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()
        record.write_text("{broken\n")
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()
        self.assertTrue(self.previous.exists())

    def test_symlink_record_and_projects_root_fail_closed(self):
        record = self.write()
        body = record.read_bytes()
        outside = self.cwd / "outside.jsonl"
        outside.write_bytes(body)
        record.unlink()
        record.symlink_to(outside)
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()
        record.unlink()
        self.previous.rmdir()
        self.projects.rmdir()
        self.projects.symlink_to(self.cwd)
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()
        self.assertEqual(outside.read_bytes(), body)

    def test_ambiguous_previous_containers_are_not_merged(self):
        self.write()
        other_cwd = self.previous_cwd.replace(PREVIOUS, "33333333-3333-4333-8333-333333333333")
        other = self.projects / storage._runtime_project_name(other_cwd)
        self.write(cwd=other_cwd, directory=other)
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()
        self.assertTrue(self.previous.exists() and other.exists())
        self.assertFalse(self.current.exists())

    def test_ambiguous_relocated_projects_are_not_merged(self):
        self.write()
        intermediate_cwd = self.previous_cwd.replace(PREVIOUS, FOLLOWING)
        intermediate = self.projects / storage._runtime_project_name(intermediate_cwd)
        self.write(cwd=self.previous_cwd, directory=intermediate)
        with self.assertRaises(storage.ClaudeResumeStorageError):
            self.probe()
        self.assertTrue(self.previous.exists() and intermediate.exists())
        self.assertFalse(self.current.exists())

    def test_existing_destination_is_never_replaced(self):
        record = self.write()
        self.current.mkdir()
        self.assertIsNone(self.probe())
        parent = os.open(self.projects, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaises(FileExistsError):
                compatibility._rename_no_replace(parent, self.previous.name, self.current.name)
        finally:
            os.close(parent)
        self.assertTrue(record.exists() and self.current.is_dir())
