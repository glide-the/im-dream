"""Provider-free plugin executable and management compatibility regression.

[Input] Production CLI boundary with mocked qualified resolver/subprocesses.
[Output] Default/override and version-only failure contract without installations.
[Pos] Plugin install boundary tests; no database, provider or user service.
[Sync] 2026-09-15: bind default plugin management to the Agent Runtime resolver.
[Sync] 2026-10-26: native transport retains original version/help checks and rejects another executable.
"""
import os
from pathlib import Path
import subprocess
import tempfile
from unittest import mock

import pytest
from services.claude_plugin import cli


def test_default_uses_qualified_resolver_not_ambient_claude():
    with mock.patch.dict(os.environ, {"INK_CLAUDE_CLI_PATH": ""}), \
         mock.patch.object(cli, "resolve_claude_cli_path", return_value="/qualified/runtime") as resolve:
        assert cli.resolve_claude_binary() == Path("/qualified/runtime")
        resolve.assert_called_once_with()


def test_missing_or_unqualified_runtime_fails_without_fallback():
    for value in (None, RuntimeError("manifest capability mismatch")):
        with mock.patch.dict(os.environ, {"INK_CLAUDE_CLI_PATH": ""}), \
             mock.patch.object(cli, "resolve_claude_cli_path", **(
                 {"side_effect": value} if isinstance(value, Exception) else {"return_value": value}
             )), pytest.raises(cli.ClaudeCliError):
            cli.resolve_claude_binary()


def test_explicit_override_must_be_absolute_and_executable():
    with tempfile.TemporaryDirectory(prefix="ink-plugin-cli-test-") as directory:
        executable = Path(directory) / "cli"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o700)
        with mock.patch.dict(os.environ, {"INK_CLAUDE_CLI_PATH": str(executable)}):
            assert cli.resolve_claude_binary() == executable.resolve()
        with mock.patch.dict(os.environ, {"INK_CLAUDE_CLI_PATH": "relative-cli"}), \
             mock.patch.object(cli, "resolve_claude_cli_path") as resolve, \
             pytest.raises(cli.ClaudeCliError):
            cli.resolve_claude_binary()
        resolve.assert_not_called()


@pytest.mark.parametrize("management_exit", [0, 2])
def test_version_output_does_not_replace_management_compatibility(management_exit):
    results = [subprocess.CompletedProcess([], 0, "2.1.241 (Claude Code)\n", ""),
               subprocess.CompletedProcess([], management_exit, "plugin help", "")]
    with mock.patch.object(cli.subprocess, "run", side_effect=results) as run, \
         mock.patch.object(cli.runtime, "managed_cli_env", return_value={"CLAUDE_CONFIG_DIR": "/managed"}):
        if management_exit:
            with pytest.raises(cli.ClaudeCliError, match="does not support plugin management"):
                cli.get_cli_version(Path("/qualified/runtime"))
        else:
            assert cli.get_cli_version(Path("/qualified/runtime")) == "2.1.241 (Claude Code)"
        assert run.call_args_list[1].args[0] == ["/qualified/runtime", "plugin", "--help"]
        assert run.call_args_list[1].kwargs["env"] == {"CLAUDE_CONFIG_DIR": "/managed"}


def test_bound_transport_runs_original_version_and_management_checks(tmp_path, monkeypatch):
    executable = tmp_path / "cli.js"
    executable.write_text("// original runtime fixture")
    results = [subprocess.CompletedProcess([], 0, "2.1.241 (Claude Code)\n", ""),
               subprocess.CompletedProcess([], 0, "plugin help", "")]
    runner = mock.Mock(side_effect=results)
    monkeypatch.setattr(cli, "_command_execution", None)
    monkeypatch.setenv("INK_CLAUDE_CLI_PATH", "")
    monkeypatch.setenv("INK_CLAUDE_PLUGIN_RUNTIME_ROOT", str(tmp_path / "managed-runtime"))
    cli.bind_command_execution(executable, runner)
    with mock.patch.object(cli.subprocess, "run", side_effect=AssertionError("desktop subprocess")):
        assert cli.get_cli_version() == "2.1.241 (Claude Code)"
    assert [call.args[0] for call in runner.call_args_list] == [
        [str(executable), "--version"], [str(executable), "plugin", "--help"]]
    assert runner.call_args_list[1].kwargs["env"]["CLAUDE_CONFIG_DIR"]
    with pytest.raises(cli.ClaudeCliError, match="already bound"):
        cli.bind_command_execution(executable, runner)
    with pytest.raises(cli.ClaudeCliError, match="mismatch"):
        cli.get_cli_version(tmp_path / "foreign-cli")
    monkeypatch.setenv("INK_CLAUDE_CLI_PATH", str(tmp_path / "foreign-cli"))
    with pytest.raises(cli.ClaudeCliError, match="differs"):
        cli.resolve_claude_binary()
