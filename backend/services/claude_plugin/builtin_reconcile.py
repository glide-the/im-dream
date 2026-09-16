"""Coordinate repository-owned Claude Plugin installation through Admin.

[Input] Server-owned Admin builtin data port and repository-declared package specs.
[Output] Real Dream CLI/artifact execution with lifecycle and Deck refs committed by Admin.
[Pos] Startup orchestration boundary; contains no PostgreSQL access or fallback.
[Sync] 2026-09-16: replace startup installation/ref SQL with Registry183-184 DTO calls.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
import uuid

from services.admin_data.claude_plugin_data import (
    AdminClaudePluginBuiltinData,
    ClaudePluginBuiltinEnsureInputDTO,
    ClaudePluginInstallReportInputDTO,
)
from services.admin_data.errors import AdminDataError

from .builtin_sources import PLATFORM_BUILTIN_SOURCES
from .install_service import (
    PluginInstallError,
    PluginInstallReporter,
    PluginInstallService,
)


class _BuiltinReporter(PluginInstallReporter):
    def __init__(
        self,
        data: AdminClaudePluginBuiltinData,
        request_id_factory: Callable[[], str],
        logger: logging.Logger,
    ) -> None:
        self._data = data
        self._request_id_factory = request_id_factory
        self._logger = logger

    def report(self, request: ClaudePluginInstallReportInputDTO):
        result = self._data.report(request, self._request_id_factory())
        if result.refs_created:
            self._logger.info(
                "created %d Deck Claude plugin refs for %s",
                result.refs_created,
                result.operation.requested_package_spec,
            )
        return result.operation


def _new_request_id() -> str:
    return str(uuid.uuid4())


def reconcile_platform_builtins(
    data: AdminClaudePluginBuiltinData,
    *,
    package_specs: Iterable[str] = tuple(PLATFORM_BUILTIN_SOURCES),
    request_id_factory: Callable[[], str] = _new_request_id,
    install_service_factory: Callable[[PluginInstallReporter], PluginInstallService]
    = PluginInstallService,
    logger: logging.Logger | None = None,
) -> None:
    """Ensure all declared builtins; expected failures stay non-fatal per package."""

    log = logger or logging.getLogger(__name__)
    service: PluginInstallService | None = None
    for canonical in package_specs:
        try:
            result = data.ensure(
                ClaudePluginBuiltinEnsureInputDTO(package_spec=canonical),
                request_id_factory(),
            )
            if result.action == "ready":
                if result.refs_created:
                    log.info(
                        "created %d Deck Claude plugin refs for %s",
                        result.refs_created,
                        canonical,
                    )
                continue
            if result.plan is None:
                raise RuntimeError("Admin returned an incomplete builtin plan")
            if service is None:
                service = install_service_factory(
                    _BuiltinReporter(data, request_id_factory, log)
                )
            service.install(
                result.plan.package_spec,
                source_type=result.plan.requested_source_type,
                marketplace_entry=result.plan.marketplace_source,
                operation_id=result.plan.operation_id,
            )
        except (AdminDataError, PluginInstallError) as exc:
            log.warning(
                "platform-builtin plugin seed failed for %s: %s",
                canonical,
                exc,
            )
