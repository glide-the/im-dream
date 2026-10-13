# [Sync] 2026-10-13: retain safe pre-claim failure observations and log exact allowlisted causes.
# [Sync] 2026-10-07: delegate latest due and active owner decisions to Admin claim; busy/not_due skip without false success/failure.
# [Input] Authenticated connector candidates, versioned per-connector sync policy, and the existing Notion facade.
# [Output] One process-local background loop that requests Admin-owned due runs outside Agent turns.
# [Pos] Notion scheduled snapshot synchronization worker in backend/notion
# [Sync] 2026-08-28: add strategy-driven background synchronization without a queue, new service, or schema change.

"""Background synchronization for actor-scoped Notion snapshots."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import store
from .factory import NotionConnectorFacade, build_notion_facade
from .sync_status import (
    NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS, NOTION_SYNC_SCHEDULER_INTERVAL_ENV,
    NotionSyncDiagnostics, scheduler_interval_from_env, sync_diagnostics,
)

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class NotionSyncSweepResult:
    candidates: int
    attempted: int
    succeeded: int
    failed: int


class NotionSnapshotSyncWorker:
    """Request scheduled claims periodically; Admin owns due and active-run decisions."""

    def __init__(
        self,
        *,
        candidate_provider: Callable[[], list[dict[str, Any]]] = store.list_sync_candidates,
        facade_factory: Callable[[int, str], NotionConnectorFacade] = build_notion_facade,
        interval_seconds: float | None = None,
        diagnostics: NotionSyncDiagnostics = sync_diagnostics,
    ) -> None:
        self._candidate_provider = candidate_provider
        self._facade_factory = facade_factory
        self._interval_seconds = interval_seconds or scheduler_interval_from_env()
        self._diagnostics = diagnostics
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(),
                name="notion-snapshot-sync-worker",
            )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        self._diagnostics.retain_candidates([])
        if task is None or task.done():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def sync_due_once(self) -> NotionSyncSweepResult:
        candidates = await asyncio.to_thread(self._candidate_provider)
        self._diagnostics.retain_candidates(candidates)
        attempted = 0
        succeeded = 0
        failed = 0
        for connector in candidates:
            sources = connector.get("sources") if isinstance(connector.get("sources"), list) else []
            # Admin owns current due/lease decisions; persisted syncing is not a local mutex.
            if not sources:
                continue
            connector_id = str(connector.get("id") or "")
            user_id = connector.get("user_id")
            if not connector_id or isinstance(user_id, bool) or not isinstance(user_id, int):
                continue
            attempted += 1
            try:
                outcome = await self._facade_factory(user_id, connector_id).sync(
                    connector_id=connector_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as error:
                failed += 1
                code = self._diagnostics.failed(connector, error)
                logger.warning("Notion scheduled sync failed safely: code=%s", code)
            else:
                self._diagnostics.clear(connector_id)
                if isinstance(outcome, dict) and outcome.get("synced") is True:
                    succeeded += 1
        return NotionSyncSweepResult(
            candidates=len(candidates),
            attempted=attempted,
            succeeded=succeeded,
            failed=failed,
        )

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval_seconds)
            try:
                await self.sync_due_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Notion scheduled sync sweep failed safely: code=sweep_failed")


__all__ = [
    "NOTION_SYNC_SCHEDULER_INTERVAL_ENV",
    "NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS",
    "NotionSnapshotSyncWorker",
    "NotionSyncSweepResult",
    "scheduler_interval_from_env",
]
