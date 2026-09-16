"""Provider-free startup reconciliation tests; no PostgreSQL, CLI or runtime DDL.

[Sync] 2026-09-16: assert the production database module is absent after Admin adoption.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from services.admin_data.claude_plugin_data import (
    ClaudePluginBuiltinEnsureOutputDTO,
    ClaudePluginBuiltinReportOutputDTO,
    ClaudePluginInstallPlanDTO,
    ClaudePluginOperationDTO,
)
from services.admin_data.errors import AdminDataError
from services.claude_plugin.builtin_reconcile import reconcile_platform_builtins


SPEC = "ink-dream-story@platform-builtin"
NOW = datetime(2026, 9, 16, tzinfo=UTC)


def operation(status="running"):
    return ClaudePluginOperationDTO(
        id="cop_builtin",
        operation_kind="install",
        requested_package_spec=SPEC,
        marketplace_entry_id=None,
        status=status,
        phase="starting" if status == "running" else "ready",
        progress=5 if status == "running" else 100,
        message="started",
        executable=None,
        argv_json=None,
        cwd=None,
        cli_version=None,
        exit_code=None,
        evidence_path=None,
        installation_id=None if status == "running" else "cpi_ready",
        error_code=None,
        error_summary=None,
        created_at=NOW,
        updated_at=NOW,
        finished_at=None if status == "running" else NOW,
    )


class FakeData:
    def __init__(self, ensure_result) -> None:
        self.ensure_result = ensure_result
        self.ensure_calls = []
        self.report_calls = []

    def ensure(self, request, request_id):
        self.ensure_calls.append((request, request_id))
        if isinstance(self.ensure_result, Exception):
            raise self.ensure_result
        return self.ensure_result

    def report(self, request, request_id):
        self.report_calls.append((request, request_id))
        return ClaudePluginBuiltinReportOutputDTO(
            operation=operation(), refs_created=0
        )


class FakeInstaller:
    def __init__(self, reporter) -> None:
        self.reporter = reporter
        self.calls = []

    def install(self, package_spec, **kwargs):
        self.calls.append((package_spec, kwargs))
        assert self.reporter.report(
            SimpleNamespace(operation_id="cop_builtin")
        ).id == "cop_builtin"


def test_ready_builtin_stops_before_cli_and_keeps_admin_ref_result():
    data = FakeData(
        ClaudePluginBuiltinEnsureOutputDTO(
            action="ready",
            package_spec=SPEC,
            installation_id="cpi_ready",
            refs_created=1,
        )
    )
    factories = []
    reconcile_platform_builtins(
        data,
        package_specs=[SPEC],
        request_id_factory=lambda: "request-ready",
        install_service_factory=lambda reporter: factories.append(reporter),
    )
    assert len(data.ensure_calls) == 1
    assert factories == []


def test_install_plan_executes_only_dream_cli_port_and_reports_to_admin():
    data = FakeData(
        ClaudePluginBuiltinEnsureOutputDTO(
            action="install",
            plan=ClaudePluginInstallPlanDTO(
                accepted=True,
                operation_id="cop_builtin",
                package_spec=SPEC,
                marketplace_entry_id=None,
                requested_source_type="platform-builtin",
                marketplace_source=None,
            ),
        )
    )
    installers = []

    def factory(reporter):
        result = FakeInstaller(reporter)
        installers.append(result)
        return result

    reconcile_platform_builtins(
        data,
        package_specs=[SPEC],
        request_id_factory=lambda: "request-install",
        install_service_factory=factory,
    )
    assert installers[0].calls == [
        (
            SPEC,
            {
                "source_type": "platform-builtin",
                "marketplace_entry": None,
                "operation_id": "cop_builtin",
            },
        )
    ]
    assert len(data.report_calls) == 1


def test_admin_failure_is_nonfatal_and_never_requests_a_database_fallback():
    data = FakeData(AdminDataError("ADMIN_UPSTREAM_UNAVAILABLE", 503))
    created = []
    reconcile_platform_builtins(
        data,
        package_specs=[SPEC],
        request_id_factory=lambda: "request-failed",
        install_service_factory=lambda reporter: created.append(reporter),
    )
    assert created == []
    assert len(data.ensure_calls) == 1


def test_production_startup_and_database_module_have_no_builtin_sql_fallback():
    root = Path(__file__).resolve().parents[1]
    coordinator = (root / "services/claude_plugin/builtin_reconcile.py").read_text()
    server = (root / "server.py").read_text()
    assert not (root / "database.py").exists()
    assert "import database" not in coordinator
    assert "get_db" not in coordinator
    startup = server.split("async def startup_claude_plugin_seed", 1)[1].split(
        '@app.on_event("shutdown")', 1
    )[0]
    assert "database" not in startup
    assert "SELECT " not in startup
