# [Input] Application-owned Admin client and frozen source-bound artifact claims.
# [Output] Automatic L2/L3 publication with canonical-byte crash recovery.
# [Pos] Small Reflections after-report worker; no extra model invocation or generic task system.
# [Sync] 2026-10-15: discover new reports after capability adoption and drain claims.
from __future__ import annotations
import asyncio
import logging
from config import memory_poll_seconds
from uuid import uuid4
from services.admin_data.memory_data import AdminMemoryData,EmptyDTO,StageDTO,PublishDTO,FailDTO
from .documents import convert,convert_theme,validate_document
from .files import publish
logger=logging.getLogger(__name__)
class MemoryWorker:
    def __init__(self,client):
        self.data=AdminMemoryData(client);self.task=None;self.closed=False
        self.interval=memory_poll_seconds()
    def step(self):
        self.data.invoke('memory.artifacts.discover',EmptyDTO(),str(uuid4()))
        claimed=self.data.invoke('memory.artifacts.claim',EmptyDTO(),str(uuid4()))
        if claimed.artifact is None: return False
        artifact=claimed.artifact;phase='MEMORY_CONVERSION_FAILED'
        key={'artifact_id':artifact.artifact_id,'revision':artifact.revision,'claim_token':claimed.claim_token}
        try:
            if artifact.metadata is None:
                doc,body,theme,metadata=convert(claimed.source,artifact)
                artifact=self.data.invoke('memory.artifacts.stage',StageDTO(**key,document=doc,body_sha256=body,theme_document=theme,metadata=metadata,theme_error_code='MEMORY_THEME_CONVERSION_FAILED' if doc is not None and theme is None else None),str(uuid4()))
            elif artifact.state=='ready' and artifact.theme_state=='failed' and artifact.theme_document is None:
                header,records=validate_document(artifact)
                try:
                    theme,count=convert_theme(claimed.source,artifact,header,records,artifact.body_sha256)
                    theme_error=None
                except (ValueError,TypeError,KeyError):
                    theme,count,theme_error=None,0,'MEMORY_THEME_CONVERSION_FAILED'
                metadata=artifact.metadata.model_copy(update={'theme_count':count})
                artifact=self.data.invoke('memory.artifacts.stage',StageDTO(**key,document=artifact.document,body_sha256=artifact.body_sha256,theme_document=theme,metadata=metadata,theme_error_code=theme_error),str(uuid4()))
            phase='MEMORY_PUBLICATION_FAILED'
            if artifact.document is not None: publish(artifact)
            theme_published=False
            theme_error='MEMORY_THEME_CONVERSION_FAILED' if artifact.theme_state=='failed' and artifact.theme_document is None else None
            if artifact.theme_document is not None:
                try:
                    publish(artifact,theme=True);theme_published=True
                except (OSError,ValueError): theme_error='MEMORY_THEME_PUBLICATION_FAILED'
            self.data.invoke('memory.artifacts.publish',PublishDTO(**key,document_sha256=artifact.document_sha256,theme_sha256=artifact.theme_sha256 if theme_published else None,theme_published=theme_published,theme_error_code=theme_error),str(uuid4()))
        except Exception as error:
            # Keep canonical publishing bytes for lease-based recovery. Conversion is deterministic,
            # so an unknown stage response can be safely inspected/reclaimed without provider dispatch.
            logger.warning('Memory publication deferred; artifact_id=%s phase=%s',artifact.artifact_id,phase)
            # A permanent converter/schema error is visible; transient publication uses expired-lease recovery.
            if phase=='MEMORY_CONVERSION_FAILED' and not getattr(error,'outcome_unknown',False):
                try: self.data.invoke('memory.artifacts.fail',FailDTO(**key,error_code=phase,retryable=False),str(uuid4()))
                except Exception: pass
        return True
    async def _run(self):
        while not self.closed:
            try:
                step_task=asyncio.create_task(asyncio.to_thread(self.step))
                try:
                    worked=await asyncio.shield(step_task)
                except asyncio.CancelledError:
                    await step_task
                    raise
                if worked: continue
            except Exception:
                # Missing capabilities fail closed for memory only; reports and ordinary Chat stay usable.
                pass
            await asyncio.sleep(self.interval)
    def start(self): self.task=asyncio.create_task(self._run(),name='reflections-memory-worker')
    async def close(self):
        self.closed=True
        if self.task:
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
