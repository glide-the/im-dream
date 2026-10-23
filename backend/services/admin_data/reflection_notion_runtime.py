# [Input] Task-owned metadata scope, section binding, live authority and existing Notion credential store.
# [Output] Existing .notion index projection and authorized, persisted first-read page payloads.
# [Pos] Reflections adapter for the existing Notion Read hook; no additional Agent Tool or credential projection.
# [Sync] 2026-10-23: fetch one requested page after task start and retain actual evidence through Admin.
from __future__ import annotations
import asyncio
import hashlib
from datetime import datetime, timezone
from uuid import uuid4
from notion import NotionCredentialStore, NotionSnapshotStore, clear_workspace_snapshot
from notion.operations import NotionOperationClient
from notion.today import safe_url
from .errors import AdminDataError
from .reflection_notion_scope_data import (
    AdminReflectionNotionScopeData, ReflectionScopeSnapshotDTO,
    ReflectionNotionBindingDTO, ReflectionNotionEvidenceDTO, ReflectionNotionReadDTO,
)

class ReflectionNotionRuntime:
    def __init__(self, content, *, actor_id, begin, task_id, client, authorize):
        self.content = content
        self.actor_id, self.begin, self.task_id = actor_id, begin, task_id
        self.data = AdminReflectionNotionScopeData(client)
        self.authorize = authorize
        self.available = isinstance(content, ReflectionScopeSnapshotDTO) and content.notion is not None
        self.read_page_ids: set[str] = set()
        self._lock = asyncio.Lock()

    def project(self, workspace):
        credentials = NotionCredentialStore()
        credentials.clear_thread_projection(workspace)
        if not self.available:
            clear_workspace_snapshot(workspace)
            return
        snapshot = self.content.notion.snapshot.model_dump(mode="json")
        source, metadata = snapshot["connector"], snapshot["metadata"]
        connector = {**source, "last_synced_at": metadata["fetched_at"],
            "current_snapshot_version": metadata["snapshot_version"],
            "current_source_revision": metadata["source_revision"], "current_sync_cursor": metadata["sync_cursor"],
            "sources": [{"resource_type": kind, "external_id": identity}
                for kind, key in (("notion_page", "selected_pages"), ("notion_database", "selected_databases"))
                for identity in source[key]]}
        NotionSnapshotStore(credentials).project_thread(self.actor_id, connector, workspace, snapshot=snapshot)

    async def read_page(self, page_id):
        if not self.available:
            raise AdminDataError("REFLECTION_NOTION_REFERENCE_DENIED", 403)
        async with self._lock:
            self.authorize()
            notion = self.content.notion
            entry = next((item for item in notion.snapshot.index if item.page_id == page_id), None)
            if entry is None:
                raise AdminDataError("REFLECTION_NOTION_REFERENCE_DENIED", 403)
            binding = ReflectionNotionBindingDTO(task_id=self.task_id, section=self.begin.section,
                thread_id=self.begin.thread_id, section_revision=self.begin.revision, page_id=page_id)
            cached = await asyncio.to_thread(self.data.read_context, binding, str(uuid4()))
            page = cached.page
            if page is None:
                home = NotionCredentialStore().effective_home(self.actor_id)
                result = await NotionOperationClient(home).get_page_markdown(page_id)
                if not result.success:
                    raise AdminDataError("NOTION_ANALYSIS_READ_FAILED", 502)
                markdown = str((result.data or {}).get("markdown") or "")
                proposed = ReflectionNotionReadDTO(page_id=page_id, title=entry.title, url=safe_url(entry.url),
                    markdown=markdown, content_sha256=hashlib.sha256(markdown.encode()).hexdigest(),
                    read_at=datetime.now(timezone.utc).isoformat())
                self.authorize()
                try:
                    persisted = await asyncio.to_thread(self.data.record,
                        ReflectionNotionEvidenceDTO(**binding.model_dump(), page=proposed), str(uuid4()))
                except AdminDataError as error:
                    if not error.outcome_unknown:
                        raise
                    # Read back the same page after an unknown write. No POST replay.
                    persisted = await asyncio.to_thread(self.data.read_context, binding, str(uuid4()))
                page = persisted.page
                if page is None or page.content_sha256 != proposed.content_sha256:
                    raise AdminDataError("REFLECTION_NOTION_EVIDENCE_UNCONFIRMED", 503)
            self.authorize()
            if page.page_id != page_id or page.title != entry.title or page.url != safe_url(entry.url) or hashlib.sha256(page.markdown.encode()).hexdigest() != page.content_sha256:
                raise AdminDataError("ADMIN_RESPONSE_INVALID", 503)
            if not any(item.page_id == page_id for item in notion.pages):
                notion.pages.append(page)
            self.read_page_ids.add(page_id)
            return {"ok": True, **page.model_dump(mode="json"), "snapshot_version": notion.snapshot_version}
