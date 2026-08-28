# [Input] Consume libs/claude_agent_kit/server/sdk_env.py SDK metadata, CLI path,
#         and SDK buffer policy helpers.
# [Output] Verify the custom distribution/import owner, Dream CLI default,
#          explicit official rollback, fail-closed resolution, and buffers.
# [Pos] test node in backend/tests
# [Sync] 2026-07-26: initial — cli_path resolution coverage for the Docker
#                    apply-seccomp-patched npm CLI pinning (claude-sdk-env-design).
# [Sync] 2026-08-20: cover the server-owned 1–64 MiB SDK stdout message buffer policy.
# [Sync] 2026-08-26: require ink-claude-dream-agent-sdk 0.2.144 and default
#                    ink-claude-code-dream; official CLI is an absolute
#                    CLAUDE_CODE_CLI_PATH-only rollback and missing runtime fails closed.
# [Sync] 2026-08-23: reject manifests without a pruned core, production
#                    eligibility, or required MCP management identity capability.
# [Sync] 2026-08-28: verify exact server-owned Runtime env validation, precedence,
#                    parent scrubbing, and omit-when-unset behavior.

"""Tests for sdk_env.apply_cli_path_to_options (2026-07-26)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import libs.claude_agent_kit.server.sdk_env as sdk_env_module
import tests._sdk_stubs  # noqa: F401
from libs.claude_agent_kit.server.sdk_env import (
    CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT,
    CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME,
    DREAM_CLAUDE_CLI_EXECUTABLE,
    DREAM_CLAUDE_CLI_VERSION,
    DREAM_CLAUDE_REQUIRED_CAPABILITIES,
    DREAM_CLAUDE_RUNTIME_MANIFEST_SCHEMA,
    DREAM_CLAUDE_SDK_DISTRIBUTION,
    DREAM_CLAUDE_SDK_IMPORT,
    DREAM_CLAUDE_SDK_VERSION,
    apply_cli_path_to_options,
    require_dream_claude_sdk_distribution,
    resolve_claude_agent_max_buffer_size,
    resolve_claude_cli_path,
)


def _make_options(cli_path=None) -> types.SimpleNamespace:
    return types.SimpleNamespace(cli_path=cli_path)


class TestApplyCliPathToOptions(unittest.TestCase):
    def _env(self, **vars: str):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_CLI_PATH"}
        env.update(vars)
        return unittest.mock.patch.dict(os.environ, env, clear=True)

    @staticmethod
    def _qualified_runtime(root: Path, **core_overrides: bool) -> Path:
        executable = root / "bin" / DREAM_CLAUDE_CLI_EXECUTABLE
        executable.parent.mkdir(parents=True)
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o700)
        core = {
            "corePruned": True,
            "productionEligible": True,
            **core_overrides,
        }
        manifest = {
            "schemaVersion": DREAM_CLAUDE_RUNTIME_MANIFEST_SCHEMA,
            "runtime": {
                "name": DREAM_CLAUDE_CLI_EXECUTABLE,
                "version": DREAM_CLAUDE_CLI_VERSION,
                "entrypoint": f"bin/{DREAM_CLAUDE_CLI_EXECUTABLE}",
                "integration": {
                    "environment": "CLAUDE_CODE_CLI_PATH",
                    "sdkVersion": DREAM_CLAUDE_SDK_VERSION,
                    "sdkOption": "ClaudeAgentOptions.cli_path",
                },
            },
            "core": core,
            "protocol": {"name": "claude-code-stream-json", "version": 1},
            "capabilityEvidence": "manifest/capabilities.json",
        }
        capability_evidence = {
            "runtime": core,
            "capabilities": [
                {"id": capability_id}
                for capability_id in sorted(DREAM_CLAUDE_REQUIRED_CAPABILITIES)
            ],
        }
        (root / "release-manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        evidence_path = root / "manifest" / "capabilities.json"
        evidence_path.parent.mkdir()
        evidence_path.write_text(json.dumps(capability_evidence), encoding="utf-8")
        return executable

    def test_env_override_honored_when_path_exists(self):
        with tempfile.NamedTemporaryFile() as cli:
            os.chmod(cli.name, 0o700)
            options = _make_options()
            with self._env(CLAUDE_CODE_CLI_PATH=cli.name):
                result = apply_cli_path_to_options(options)
        self.assertIs(result, options)
        self.assertEqual(options.cli_path, str(Path(cli.name).resolve()))

    def test_missing_env_path_falls_through_to_which_with_warning(self):
        with tempfile.TemporaryDirectory() as runtime_root:
            cli = self._qualified_runtime(Path(runtime_root))
            options = _make_options()
            with (
                self._env(CLAUDE_CODE_CLI_PATH="/nonexistent/claude"),
                unittest.mock.patch.object(
                    sdk_env_module.shutil, "which", return_value=str(cli)
                ),
                self.assertLogs(sdk_env_module.logger, level="WARNING") as logs,
            ):
                apply_cli_path_to_options(options)
            self.assertEqual(options.cli_path, str(cli.resolve()))
        self.assertTrue(any("CLAUDE_CODE_CLI_PATH" in m for m in logs.output))

    def test_dream_cli_on_path_is_default_when_env_unset(self):
        with tempfile.TemporaryDirectory() as runtime_root:
            cli = self._qualified_runtime(Path(runtime_root))
            options = _make_options()
            with (
                self._env(),
                unittest.mock.patch.object(
                    sdk_env_module.shutil, "which", return_value=str(cli)
                ),
            ):
                apply_cli_path_to_options(options)
            self.assertEqual(options.cli_path, str(cli.resolve()))

    def test_missing_dream_runtime_fails_closed_without_bundled_fallback(self):
        options = _make_options()
        with (
            self._env(),
            unittest.mock.patch.object(
                sdk_env_module.shutil, "which", return_value=None
            ),
            self.assertRaisesRegex(RuntimeError, DREAM_CLAUDE_CLI_EXECUTABLE),
        ):
            apply_cli_path_to_options(options)
        self.assertIsNone(options.cli_path)

    def test_explicit_cli_path_preserved(self):
        options = _make_options(cli_path="/explicit/claude")
        with tempfile.NamedTemporaryFile() as cli:
            with self._env(CLAUDE_CODE_CLI_PATH=cli.name):
                apply_cli_path_to_options(options)
        self.assertEqual(options.cli_path, "/explicit/claude")

    def test_explicit_cli_path_preserved_over_which(self):
        options = _make_options(cli_path="/explicit/claude")
        with (
            self._env(),
            unittest.mock.patch.object(
                sdk_env_module.shutil, "which", return_value="/usr/local/bin/claude"
            ),
        ):
            apply_cli_path_to_options(options)
        self.assertEqual(options.cli_path, "/explicit/claude")

    def test_which_checked_with_dream_runtime_name(self):
        options = _make_options()
        with (
            self._env(),
            unittest.mock.patch.object(
                sdk_env_module.shutil, "which", return_value=None
            ) as which_mock,
            self.assertRaises(RuntimeError),
        ):
            apply_cli_path_to_options(options)
        which_mock.assert_called_once_with(DREAM_CLAUDE_CLI_EXECUTABLE, path=None)

    def test_absolute_override_is_explicit_official_cli_rollback(self):
        with tempfile.NamedTemporaryFile(prefix="official-claude-") as cli:
            os.chmod(cli.name, 0o700)
            selected = resolve_claude_cli_path(
                {"CLAUDE_CODE_CLI_PATH": cli.name, "PATH": ""}
            )
        self.assertEqual(selected, str(Path(cli.name).resolve()))

    def test_relative_override_cannot_select_official_cli(self):
        with (
            unittest.mock.patch.object(
                sdk_env_module.shutil, "which", return_value=None
            ),
            self.assertLogs(sdk_env_module.logger, level="WARNING"),
        ):
            selected = resolve_claude_cli_path(
                {"CLAUDE_CODE_CLI_PATH": "./claude", "PATH": ""}
            )
        self.assertIsNone(selected)

    def test_unpruned_compatibility_envelope_is_rejected(self):
        with tempfile.TemporaryDirectory() as runtime_root:
            cli = self._qualified_runtime(
                Path(runtime_root),
                corePruned=False,
            )
            with (
                self._env(),
                unittest.mock.patch.object(
                    sdk_env_module.shutil, "which", return_value=str(cli)
                ),
                self.assertRaisesRegex(RuntimeError, "production-qualified"),
            ):
                resolve_claude_cli_path()

    def test_non_production_runtime_is_rejected(self):
        with tempfile.TemporaryDirectory() as runtime_root:
            cli = self._qualified_runtime(
                Path(runtime_root),
                productionEligible=False,
            )
            with (
                self._env(),
                unittest.mock.patch.object(
                    sdk_env_module.shutil, "which", return_value=str(cli)
                ),
                self.assertRaisesRegex(RuntimeError, "production-qualified"),
            ):
                resolve_claude_cli_path()

    def test_runtime_missing_mcp_identity_capability_is_rejected(self):
        with tempfile.TemporaryDirectory() as runtime_root:
            root = Path(runtime_root)
            cli = self._qualified_runtime(root)
            evidence_path = root / "manifest" / "capabilities.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["capabilities"] = [
                value
                for value in evidence["capabilities"]
                if value["id"] != "mcp.management.identity"
            ]
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            with (
                self._env(),
                unittest.mock.patch.object(
                    sdk_env_module.shutil, "which", return_value=str(cli)
                ),
                self.assertRaisesRegex(RuntimeError, "mcp.management.identity"),
            ):
                resolve_claude_cli_path()


class TestDreamSdkDistribution(unittest.TestCase):
    @staticmethod
    def _distribution(*, name: str, version: str):
        return types.SimpleNamespace(metadata={"Name": name}, version=version)

    @staticmethod
    def _modules(*, version: str = DREAM_CLAUDE_SDK_VERSION):
        sdk = types.SimpleNamespace(
            __version__=version,
            ClaudeAgentOptions=object(),
            ClaudeSDKClient=object(),
            query=object(),
        )
        sdk_types = types.SimpleNamespace(
            AssistantMessage=object(),
            ResultMessage=object(),
            StreamEvent=object(),
            SystemMessage=object(),
            UserMessage=object(),
        )
        return sdk, sdk_types

    def _importer(self, *, version: str = DREAM_CLAUDE_SDK_VERSION):
        sdk, sdk_types = self._modules(version=version)
        return unittest.mock.Mock(
            side_effect=lambda name: (
                sdk if name == "claude_agent_sdk" else sdk_types
            )
        )

    def test_exact_custom_distribution_owns_preserved_import(self):
        distribution = self._distribution(
            name=DREAM_CLAUDE_SDK_DISTRIBUTION,
            version=DREAM_CLAUDE_SDK_VERSION,
        )
        importer = self._importer()
        with (
            unittest.mock.patch.object(
                sdk_env_module.importlib_metadata,
                "distribution",
                return_value=distribution,
            ) as distribution_lookup,
            unittest.mock.patch.object(
                sdk_env_module.importlib_metadata,
                "packages_distributions",
                return_value={
                    "claude_agent_sdk": [DREAM_CLAUDE_SDK_DISTRIBUTION]
                },
            ),
            unittest.mock.patch.object(
                sdk_env_module.importlib,
                "import_module",
                new=importer,
            ),
        ):
            result = require_dream_claude_sdk_distribution()
        self.assertIs(result, distribution)
        distribution_lookup.assert_called_once_with(DREAM_CLAUDE_SDK_DISTRIBUTION)

    def test_official_distribution_competing_for_import_fails_closed(self):
        distribution = self._distribution(
            name=DREAM_CLAUDE_SDK_DISTRIBUTION,
            version=DREAM_CLAUDE_SDK_VERSION,
        )
        with (
            unittest.mock.patch.object(
                sdk_env_module.importlib_metadata,
                "distribution",
                return_value=distribution,
            ),
            unittest.mock.patch.object(
                sdk_env_module.importlib_metadata,
                "packages_distributions",
                return_value={
                    "claude_agent_sdk": [
                        DREAM_CLAUDE_SDK_DISTRIBUTION,
                        "claude-agent-sdk",
                    ]
                },
            ),
            self.assertRaisesRegex(RuntimeError, "provided only"),
        ):
            require_dream_claude_sdk_distribution()

    def test_distribution_version_drift_fails_closed(self):
        distribution = self._distribution(
            name=DREAM_CLAUDE_SDK_DISTRIBUTION,
            version="0.2.145",
        )
        with (
            unittest.mock.patch.object(
                sdk_env_module.importlib_metadata,
                "distribution",
                return_value=distribution,
            ),
            self.assertRaisesRegex(RuntimeError, DREAM_CLAUDE_SDK_VERSION),
        ):
            require_dream_claude_sdk_distribution()

    def test_stream_protocol_symbol_drift_fails_closed(self):
        distribution = self._distribution(
            name=DREAM_CLAUDE_SDK_DISTRIBUTION,
            version=DREAM_CLAUDE_SDK_VERSION,
        )
        sdk, sdk_types = self._modules()
        del sdk_types.StreamEvent
        with (
            unittest.mock.patch.object(
                sdk_env_module.importlib_metadata,
                "distribution",
                return_value=distribution,
            ),
            unittest.mock.patch.object(
                sdk_env_module.importlib_metadata,
                "packages_distributions",
                return_value={
                    "claude_agent_sdk": [DREAM_CLAUDE_SDK_DISTRIBUTION]
                },
            ),
            unittest.mock.patch.object(
                sdk_env_module.importlib,
                "import_module",
                side_effect=lambda name: (
                    sdk if name == "claude_agent_sdk" else sdk_types
                ),
            ),
            self.assertRaisesRegex(RuntimeError, "StreamEvent"),
        ):
            require_dream_claude_sdk_distribution()


class TestResolveClaudeAgentMaxBufferSize(unittest.TestCase):
    def test_default_covers_observed_image_read_message(self):
        value = resolve_claude_agent_max_buffer_size({})
        self.assertEqual(value, 8 * 1024 * 1024)
        self.assertGreater(value, 1_202_954)

    def test_valid_server_override_is_used(self):
        value = resolve_claude_agent_max_buffer_size(
            {CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME: str(4 * 1024 * 1024)}
        )
        self.assertEqual(value, 4 * 1024 * 1024)

    def test_invalid_or_unbounded_override_falls_back_with_warning(self):
        for raw in ("invalid", "1048575", str(64 * 1024 * 1024 + 1)):
            with self.subTest(raw=raw), self.assertLogs(
                sdk_env_module.logger,
                level="WARNING",
            ):
                value = resolve_claude_agent_max_buffer_size(
                    {CLAUDE_AGENT_MAX_BUFFER_SIZE_ENV_NAME: raw}
                )
            self.assertEqual(value, CLAUDE_AGENT_MAX_BUFFER_SIZE_DEFAULT)


class TestClaudeCodeRuntimeEnv(unittest.TestCase):
    def test_configured_values_override_user_overlay(self):
        options = types.SimpleNamespace(env={
            "CLAUDE_CODE_EFFORT_LEVEL": "low",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "10",
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "20",
            "KEEP": "yes",
        })
        sdk_env_module.apply_server_claude_code_runtime_env_to_options(
            options,
            {
                "CLAUDE_CODE_EFFORT_LEVEL": "high",
                "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "262144",
                "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "262144",
            },
        )
        self.assertEqual(options.env, {
            "CLAUDE_CODE_EFFORT_LEVEL": "high",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "262144",
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "262144",
            "KEEP": "yes",
        })

    def test_unset_values_are_removed_from_parent_and_options(self):
        parent = {
            "CLAUDE_CODE_EFFORT_LEVEL": "max",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1",
            "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "1",
            "KEEP": "yes",
        }
        sdk_env_module.clear_server_claude_code_runtime_parent_env(parent)
        self.assertEqual(parent, {"KEEP": "yes"})

        options = types.SimpleNamespace(env={**parent, "CLAUDE_CODE_EFFORT_LEVEL": "low"})
        sdk_env_module.apply_server_claude_code_runtime_env_to_options(options, {})
        self.assertEqual(options.env, {"KEEP": "yes"})

    def test_invalid_or_unknown_runtime_values_fail_closed(self):
        invalid = (
            {"CLAUDE_CODE_EFFORT_LEVEL": "ultra"},
            {"CLAUDE_CODE_EFFORT_LEVEL": 1},
            {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "0"},
            {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": 262144},
            {"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "2147483648"},
            {"CLAUDE_CODE_MAX_CONTEXT_TOKENS": "262144.0"},
            {"CLAUDE_CODE_UNKNOWN": "1"},
        )
        for runtime_env in invalid:
            with self.subTest(runtime_env=runtime_env), self.assertRaises(ValueError):
                sdk_env_module.apply_server_claude_code_runtime_env_to_options(
                    types.SimpleNamespace(env={}),
                    runtime_env,
                )


if __name__ == "__main__":
    unittest.main()
