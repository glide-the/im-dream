# [Input] Dream backend/frontend project manifests, uv lock, and unchanged API schema declaration.
# [Output] Prove the patch metadata bump is complete without changing the API contract.
# [Pos] Provider-free project-version regression tests.
# [Sync] 2026-09-13: require backend 0.1.2, frontend 0.0.2, and the matching backend lock.

from pathlib import Path
import json
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ProjectVersionTests(unittest.TestCase):
    def test_backend_project_and_lock_versions_match(self) -> None:
        project = tomllib.loads((ROOT / "backend/pyproject.toml").read_text())
        lock = tomllib.loads((ROOT / "backend/uv.lock").read_text())
        locked = next(package for package in lock["package"]
                      if package["name"] == "ink-and-memory-backend")
        self.assertEqual(project["project"]["version"], "0.1.2")
        self.assertEqual(locked["version"], "0.1.2")
        self.assertIn("ink-claude-dream-agent-sdk==0.2.145", project["project"]["dependencies"])

    def test_frontend_patch_metadata_and_api_schema_are_explicit(self) -> None:
        frontend = json.loads((ROOT / "frontend/package.json").read_text())
        self.assertEqual(frontend["version"], "0.0.2")
        self.assertEqual(frontend["packageManager"], "pnpm@10.28.1")
        self.assertIn('version="2.0.0"', (ROOT / "backend/server.py").read_text())


if __name__ == "__main__":
    unittest.main()
