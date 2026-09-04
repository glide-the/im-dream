# [Input] Temporary common/platform Skill source trees and canonical/invalid `.skill` ZIP packages.
# [Output] Regression proof for catalog identity, directory symlinks, thread-local archive extraction, pruning, and fail-closed archive validation.
# [Pos] Focused unit test node for libs/claude_agent_kit/server/builtin_skill_packages.py.
# [Sync] 2026-09-04: require every repository .claude Skill to have an exact
#                    backend/common release mirror before production packaging.

from __future__ import annotations

import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from libs.claude_agent_kit.server.builtin_skill_packages import (
    BuiltinSkillPackageError,
    discover_builtin_skill_packages,
    sync_builtin_skill_packages,
)


def _write_directory_skill(root: Path, namespace: str, skill_id: str) -> Path:
    skill_root = root / namespace / skill_id
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text(
        f"---\nname: {skill_id}\ndescription: test package\n---\n\n# {skill_id}\n",
        encoding="utf-8",
    )
    return skill_root


def _write_archive_skill(root: Path, namespace: str, skill_id: str) -> Path:
    namespace_root = root / namespace
    namespace_root.mkdir(parents=True, exist_ok=True)
    archive_path = namespace_root / f"{skill_id}.skill"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"{skill_id}/SKILL.md",
            f"---\nname: {skill_id}\ndescription: archive package\n---\n\n# {skill_id}\n",
        )
    return archive_path


def _package_files(root: Path) -> dict[str, bytes]:
    """Return stable package contents while ignoring local interpreter caches."""

    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or "__pycache__" in relative.parts
            or path.suffix == ".pyc"
            or path.name == ".DS_Store"
        ):
            continue
        files[relative.as_posix()] = path.read_bytes()
    return files


class TestBuiltinSkillPackages(unittest.TestCase):
    def test_project_claude_skills_have_exact_common_release_mirrors(self) -> None:
        project_skills_root = PROJECT_ROOT / ".claude" / "skills"
        project_packages = tuple(
            sorted(
                path
                for path in project_skills_root.iterdir()
                if path.is_dir() and (path / "SKILL.md").is_file()
            )
        )
        common_packages = {
            package.skill_id: package
            for package in discover_builtin_skill_packages(
                ("common",),
                skills_root=ROOT / "builtin_skills",
            )
        }

        self.assertGreater(len(project_packages), 0)
        for project_package in project_packages:
            with self.subTest(skill_id=project_package.name):
                release_package = common_packages.get(project_package.name)
                self.assertIsNotNone(release_package)
                assert release_package is not None
                self.assertFalse(release_package.is_archive)
                self.assertEqual(
                    _package_files(release_package.source_path),
                    _package_files(project_package),
                )

    def test_directory_packages_link_and_archives_unpack_flat_in_thread(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "builtin"
            common_source = _write_directory_skill(root, "common", "always-on")
            notion_source = _write_directory_skill(root, "notion", "notion-read")
            _write_archive_skill(root, "notion", "notion-write")
            workspace = Path(temporary_directory) / "workspace"

            result = sync_builtin_skill_packages(
                workspace,
                enabled_platforms=("notion",),
                skills_root=root,
                prune_inactive_platforms=True,
            )

            common_target = workspace / "skills" / "always-on"
            notion_target = workspace / "skills" / "notion-read"
            archive_target = workspace / "skills" / "notion-write"
            self.assertTrue(common_target.is_symlink())
            self.assertEqual(common_target.resolve(), common_source.resolve())
            self.assertTrue(notion_target.is_symlink())
            self.assertEqual(notion_target.resolve(), notion_source.resolve())
            self.assertTrue(archive_target.is_dir())
            self.assertFalse(archive_target.is_symlink())
            self.assertTrue((archive_target / "SKILL.md").is_file())
            self.assertFalse((archive_target / "notion-write").exists())
            self.assertEqual(
                set(result.linked_source_paths),
                {str(common_source.resolve()), str(notion_source.resolve())},
            )

    def test_common_is_always_selected_and_inactive_platform_ids_are_precisely_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "builtin"
            _write_directory_skill(root, "common", "always-on")
            _write_directory_skill(root, "notion", "notion-read")
            workspace = Path(temporary_directory) / "workspace"
            user_skill = workspace / "skills" / "user-owned"
            user_skill.mkdir(parents=True)
            (user_skill / "SKILL.md").write_text("user", encoding="utf-8")

            sync_builtin_skill_packages(
                workspace,
                enabled_platforms=("notion",),
                skills_root=root,
                prune_inactive_platforms=True,
            )
            result = sync_builtin_skill_packages(
                workspace,
                skills_root=root,
                prune_inactive_platforms=True,
            )

            self.assertTrue((workspace / "skills" / "always-on").is_symlink())
            self.assertFalse((workspace / "skills" / "notion-read").exists())
            self.assertTrue((user_skill / "SKILL.md").is_file())
            self.assertEqual(result.removed_ids, ("notion-read",))

    def test_selected_namespace_duplicate_id_fails_before_workspace_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "builtin"
            _write_directory_skill(root, "common", "duplicate")
            _write_directory_skill(root, "notion", "duplicate")
            workspace = Path(temporary_directory) / "workspace"
            marker = workspace / "skills" / "keep" / "SKILL.md"
            marker.parent.mkdir(parents=True)
            marker.write_text("keep", encoding="utf-8")

            with self.assertRaises(BuiltinSkillPackageError):
                sync_builtin_skill_packages(
                    workspace,
                    enabled_platforms=("notion",),
                    skills_root=root,
                    prune_inactive_platforms=True,
                )

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_skill_archive_path_traversal_and_symlink_entries_fail_closed(self) -> None:
        for entry_kind in ("traversal", "symlink"):
            with self.subTest(entry_kind=entry_kind), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory) / "builtin"
                archive_path = _write_archive_skill(root, "notion", "unsafe")
                with zipfile.ZipFile(archive_path, "a") as archive:
                    if entry_kind == "traversal":
                        archive.writestr("unsafe/../outside.txt", "outside")
                    else:
                        link = zipfile.ZipInfo("unsafe/link")
                        link.create_system = 3
                        link.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(link, "SKILL.md")

                with self.assertRaises(BuiltinSkillPackageError):
                    discover_builtin_skill_packages(
                        ("notion",),
                        skills_root=root,
                    )


if __name__ == "__main__":
    unittest.main()
