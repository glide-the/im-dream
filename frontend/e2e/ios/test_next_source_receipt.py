# [Input] Public iOS Next source-verification command and explicitly owned minimal receipt fixtures.
# [Output] Fail-closed checks for legacy receipts, source changes, cross-snapshot metadata and unsafe input paths.
# [Pos] Provider-free build-contract tests; no application resources, services, database or account are modified.
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]
IOS = REPO / "frontend/ios"
SCRIPT = IOS / "scripts/bundle-next.py"
RELATIVE = "app/_dream/App.tsx"


class NextSourceReceiptTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="writing-source-gate-", dir=IOS / "build"))
        (self.root / ".writing-source-gate-test").write_text("owned\n")
        self.stage = self.root / "build-source" / RELATIVE
        self.stage.parent.mkdir(parents=True)
        self.source = (REPO / "frontend" / RELATIVE).read_bytes()
        self.stage.write_bytes(self.source)
        digest = hashlib.sha256(self.source).hexdigest()
        self.receipt = {"sourceInputs": [{"path": RELATIVE, "sha256": digest}],
                        "sourceFiles": [{"path": RELATIVE, "sha256": digest}]}

    def tearDown(self):
        self.assertFalse(self.root.is_symlink())
        self.assertEqual((self.root / ".writing-source-gate-test").read_text(), "owned\n")
        shutil.rmtree(self.root)

    def verify(self):
        (self.root / "source-receipt.json").write_text(json.dumps(self.receipt))
        env = dict(os.environ, INK_IOS_NEXT_ROOT=str(self.root))
        return subprocess.run([sys.executable, str(SCRIPT), "--verify-sources"], env=env,
                              cwd=REPO, text=True, capture_output=True)

    def test_current_snapshot_is_accepted_without_app_output(self):
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified current Next runtime inputs: 1", result.stdout)
        self.assertFalse((self.root / "next").exists())

    def test_legacy_receipt_requires_prepare_and_rebuild(self):
        del self.receipt["sourceInputs"]
        result = self.verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("IOS_NEXT_SOURCE_RECEIPT_MISSING", result.stderr)

    def test_prepared_file_change_is_rejected(self):
        self.stage.write_bytes(self.source + b"\n// changed after preparation\n")
        result = self.verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("IOS_NEXT_SOURCES_STALE", result.stderr)

    def test_changed_checkout_receipt_is_rejected(self):
        self.receipt["sourceInputs"][0]["sha256"] = "0" * 64
        result = self.verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("IOS_NEXT_SOURCES_STALE", result.stderr)

    def test_individually_matching_but_different_snapshots_are_rejected(self):
        earlier = self.source + b"\n// previous snapshot\n"
        self.stage.write_bytes(earlier)
        self.receipt["sourceFiles"][0]["sha256"] = hashlib.sha256(earlier).hexdigest()
        result = self.verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("checkout/prepared receipt differs", result.stderr)

    def test_unsafe_relative_path_is_rejected_before_read(self):
        self.receipt["sourceInputs"][0]["path"] = "../../outside-input"
        result = self.verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("IOS_NEXT_SOURCE_PATH_INVALID", result.stderr)


if __name__ == "__main__":
    unittest.main()
