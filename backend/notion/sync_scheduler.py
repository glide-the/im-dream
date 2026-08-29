# [Input] Authenticated connector candidates, versioned per-connector sync policy, and the existing Notion facade.
# [Output] One process-local background loop that refreshes due actor snapshots outside Agent turns.
# [Pos] Notion scheduled snapshot synchronization worker in backend/notion
# [Sync] 2026-08-28: add strategy-driven background synchronization without a queue, new service, or schema change.

"""Background synchronization for actor-scoped Notion snapshots."""
from __future__ import annotations

import asyncio
import logging
import math
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import store
from .factory import NotionConnectorFacade, build_notion_facade
from .sync_policy import SYNC_POLICY_CONFIG_KEY, sync_policy_is_due

logger = logging.getLogger(__name__)

NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS = 60.0
NOTION_SYNC_SCHEDULER_INTERVAL_ENV = "INK_NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS"


def scheduler_interval_from_env() -> float:
    raw = os.environ.get(NOTION_SYNC_SCHEDULER_INTERVAL_ENV, "").strip()
    if not raw:
        return NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS
    try:
        parsed = float(raw)
    except ValueError:
        return NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS
    if not math.isfinite(parsed) or parsed < 5 or parsed > 3600:
        return NOTION_SYNC_SCHEDULER_INTERVAL_SECONDS
    return parsed


@dataclass(frozen=True)
class NotionSyncSweepResult:
    candidates: int
    attempted: int
    succeeded: int
    failed: int


class NotionSnapshotSyncWorker:
    """Evaluate policies periodically; connector locks remain in the facade."""

    def __init__(
        self,
        *,
        candidate_provider: Callable[[], list[dict[str, Any]]] = store.list_sync_candidates,
        facade_factory: Callable[[int, str], NotionConnectorFacade] = build_notion_facade,
        interval_seconds: float | None = None,
    ) -> None:
        self._candidate_provider = candidate_provider
        self._facade_factory = facade_factory
        self._interval_seconds = interval_seconds or scheduler_interval_from_env()
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
        if task is None or task.done():
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def sync_due_once(self) -> NotionSyncSweepResult:
        candidates = await asyncio.to_thread(self._candidate_provider)
        attempted = 0
        succeeded = 0
        failed = 0
        for connector in candidates:
            config = connector.get("config") if isinstance(connector.get("config"), dict) else {}
            sources = connector.get("sources") if isinstance(connector.get("sources"), list) else []
            if not sources or not sync_policy_is_due(
                config.get(SYNC_POLICY_CONFIG_KEY),
                last_synced_at=connector.get("last_synced_at"),
            ):
                continue
            connector_id = str(connector.get("id") or "")
            user_id = connector.get("user_id")
            if not connector_id or isinstance(user_id, bool) or not isinstance(user_id, int):
                continue
            attempted += 1
            try:
                await self._facade_factory(user_id, connector_id).sync(
                    connector_id=connector_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                failed += 1
                logger.warning("Notion scheduled sync failed safely: code=connector_sync_failed")
            else:
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
