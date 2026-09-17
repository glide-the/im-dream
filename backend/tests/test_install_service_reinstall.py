# [Input] Dream CLI/filesystem install pipeline plus a typed in-memory Admin reporter.
# [Output] Lifecycle order, terminal failure, immutable artifact and remote digest evidence.
# [Pos] Provider-free executor contract; replay/revive transactions are tested in Admin.
# [Sync] 2026-09-16: remove the retired SQLite persistence fixture from Dream install tests.
from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import tempfile
from unittest import mock

import pytest

from services.admin_data.claude_plugin_data import (
    ClaudePluginInstallReportInputDTO,
    ClaudePluginMarketplaceSourceDTO,
    ClaudePluginOperationDTO,
)
from services.claude_plugin import cli as plugin_cli
from services.claude_plugin import install_service
from services.claude_plugin.digest import compute_plugin_digest
from services.claude_plugin.install_service import (
    MARKETPLACE_REMOTE_DRIFT,
    PLUGIN_INSTALL_FAILED,
    PluginInstallError,
    PluginInstallService,
)
from services.claude_plugin.package_spec import parse_package_spec


PACKAGE_SPEC = "drama-forge@drama-studio"
NOW = datetime(2026, 9, 16, tzinfo=UTC)


def _approved_remote_source() -> ClaudePluginMarketplaceSourceDTO:
    return ClaudePluginMarketplaceSourceDTO(
        entry_id="cpme_drama_forge",
        package_spec=PACKAGE_SPEC,
        package_name="drama-forge",
        marketplace_name="drama-studio",
        remote_url="https://github.com/example/drama-studio",
        requested_ref="release/v1",
        approved_commit_sha="a" * 40,
        marketplace_manifest_sha256="b" * 64,
        plugin_manifest_sha256=None,
        approved_plugin_digest="sha256:" + "0" * 64,
        compatibility={},
    )


def _fake_execution(argv: list[str]) -> plugin_cli.CliExecution:
    return plugin_cli.CliExecution(
        executable="/fake/claude",
        argv=list(argv),
        cwd="/fake/cwd",
        cli_version="2.1.220",
        exit_code=0,
        timed_out=False,
        stdout="",
        stderr="",
        started_at="2026-09-16T00:00:00+00:00",
        finished_at="2026-09-16T00:00:01+00:00",
        duration_ms=1000,
    )


def _operation(operation_id: str, **changes) -> ClaudePluginOperationDTO:
    values = {
        "id": operation_id,
        "operation_kind": "install",
        "requested_package_spec": PACKAGE_SPEC,
        "marketplace_entry_id": None,
        "status": "running",
        "phase": "starting",
        "progress": 5,
        "message": "Install execution started",
        "executable": None,
        "argv_json": None,
        "cwd": None,
        "cli_version": None,
        "exit_code": None,
        "evidence_path": None,
        "installation_id": None,
        "error_code": None,
        "error_summary": None,
        "created_at": NOW,
        "updated_at": NOW,
        "finished_at": None,
    }
    values.update(changes)
    return ClaudePluginOperationDTO.model_validate(values)


class Reporter:
    def __init__(self, operation_id: str, *, marketplace_entry_id=None) -> None:
        self.operation_id = operation_id
        self.marketplace_entry_id = marketplace_entry_id
        self.calls: list[ClaudePluginInstallReportInputDTO] = []
        self.installation = None

    def report(
        self, request: ClaudePluginInstallReportInputDTO
    ) -> ClaudePluginOperationDTO:
        assert request.operation_id == self.operation_id
        self.calls.append(request)
        common = {"marketplace_entry_id": self.marketplace_entry_id}
        if request.event == "begin":
            return _operation(self.operation_id, **common)
        if request.event == "progress":
            return _operation(
                self.operation_id,
                phase=request.phase,
                progress=request.progress,
                message=request.message,
                **common,
            )
        if request.event == "fail":
            return _operation(
                self.operation_id,
                status="error",
                phase="error",
                progress=100,
                message=request.error_summary,
                error_code=request.error_code,
                error_summary=request.error_summary,
                evidence_path=request.evidence_path,
                finished_at=NOW,
                **common,
            )
        self.installation = request.installation
        return _operation(
            self.operation_id,
            status="ready",
            phase="ready",
            progress=100,
            message="Installation completed",
            installation_id="cpi_installation",
            evidence_path=request.evidence_path,
            executable=(request.execution.executable if request.execution else None),
            argv_json=(
                json.dumps(request.execution.argv) if request.execution else None
            ),
            cwd=request.execution.cwd if request.execution else None,
            cli_version=(request.execution.cli_version if request.execution else None),
            exit_code=request.execution.exit_code if request.execution else None,
            finished_at=NOW,
            **common,
        )


@pytest.fixture
def install_fixture(monkeypatch):
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        monkeypatch.setenv(
            "INK_CLAUDE_PLUGIN_RUNTIME_ROOT", str(root / "runtime")
        )
        plugin_root = root / "src" / "drama-forge"
        (plugin_root / ".claude-plugin").mkdir(parents=True)
        (plugin_root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "drama-forge", "version": "1.0.1"})
        )
        (plugin_root / "skills").mkdir()
        (plugin_root / "skills" / "SKILL.md").write_text("# skill")
        monkeypatch.setattr(
            install_service,
            "_ensure_marketplace",
            lambda spec, evidence, **_kwargs: evidence.setdefault(
                "marketplace_revision", {}
            ),
        )
        monkeypatch.setattr(
            install_service,
            "_registry_entry_for",
            lambda spec: {
                "installPath": str(plugin_root),
                "version": "1.0.1",
                "gitCommitSha": "abc123",
            },
        )
        monkeypatch.setattr(
            plugin_cli,
            "run_claude",
            lambda argv, *, cwd, timeout_seconds: _fake_execution(argv),
        )
        yield plugin_root


def test_success_reports_closed_lifecycle_and_admin_installation_evidence(
    install_fixture,
):
    reporter = Reporter("cop_success")
    result = PluginInstallService(reporter).install(
        PACKAGE_SPEC, operation_id="cop_success"
    )

    assert result["status"] == "ready"
    assert result["installation_id"] == "cpi_installation"
    assert [item.event for item in reporter.calls] == [
        "begin",
        "progress",
        "progress",
        "complete",
    ]
    assert [item.phase for item in reporter.calls[1:3]] == [
        "cli-install",
        "verify",
    ]
    assert reporter.installation is not None
    assert reporter.installation.artifact_digest == compute_plugin_digest(
        install_fixture
    )
    assert Path(reporter.installation.artifact_path).is_dir()


def test_unexpected_executor_failure_reports_terminal_error(install_fixture):
    reporter = Reporter("cop_failed")
    with mock.patch.object(
        install_service.artifact_store,
        "import_tree",
        side_effect=OSError("disk unavailable"),
    ):
        with pytest.raises(PluginInstallError) as caught:
            PluginInstallService(reporter).install(
                PACKAGE_SPEC, operation_id="cop_failed"
            )

    assert caught.value.code == PLUGIN_INSTALL_FAILED
    assert reporter.calls[-1].event == "fail"
    assert reporter.calls[-1].error_code == PLUGIN_INSTALL_FAILED
    assert Path(reporter.calls[-1].evidence_path).is_file()


def test_remote_entry_rejects_content_outside_admin_approved_digest(
    install_fixture,
):
    approved = _approved_remote_source()
    reporter = Reporter(
        "cop_drift", marketplace_entry_id=approved.entry_id
    )

    with pytest.raises(PluginInstallError) as caught:
        PluginInstallService(reporter).install(
            PACKAGE_SPEC,
            source_type="marketplace",
            marketplace_entry=approved,
            operation_id="cop_drift",
        )

    assert caught.value.code == MARKETPLACE_REMOTE_DRIFT
    assert compute_plugin_digest(install_fixture) != approved.approved_plugin_digest
    assert reporter.calls[-1].event == "fail"
    assert reporter.calls[-1].error_code == MARKETPLACE_REMOTE_DRIFT


def test_remote_marketplace_registration_transports_the_approved_ref() -> None:
    approved = _approved_remote_source()
    observed: list[list[str]] = []

    def run_claude(argv: list[str], *, cwd: Path):
        observed.append(list(argv))
        return _fake_execution(argv)

    with (
        mock.patch.object(install_service, "_known_marketplaces", return_value={}),
        mock.patch.object(
            install_service,
            "resolve_local_marketplace",
            side_effect=AssertionError(
                "remote entry must not resolve a local marketplace"
            ),
        ),
        mock.patch.object(plugin_cli, "run_claude", side_effect=run_claude),
        mock.patch.object(
            install_service.runtime,
            "get_install_workspace",
            return_value=Path("/managed/install-workspace"),
        ),
        mock.patch.object(
            install_service,
            "_verified_remote_marketplace_checkout",
        ) as verify_checkout,
    ):
        install_service._ensure_marketplace(
            parse_package_spec(PACKAGE_SPEC),
            {},
            marketplace_entry=approved,
        )

    assert observed == [
        [
            "plugin",
            "marketplace",
            "add",
            "https://github.com/example/drama-studio#release/v1",
        ]
    ]
    verify_checkout.assert_called_once()
