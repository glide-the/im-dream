# [Input] Authenticated current turn, frozen owner policy and owner-verified L2 versions.
# [Output] Bounded current-task plans; no policy writes, psychological diagnosis or hidden model calls.
# [Pos] Host memory provider; taxonomy is data, never executable prompt text.
# [Sync] 2026-10-15: revisioned turn snapshot and fixed action execution.
from __future__ import annotations
from dataclasses import dataclass
import re
import time
from config import memory_resolve_timeout_seconds
from uuid import uuid4
from services.admin_data.memory_data import AdminMemoryData,EmptyDTO,ListDTO,LookupDTO,SettingsDTO
from services.admin_data.request_auth import AdminRequestActor
from services.admin_data.errors import AdminDataError
from libs.claude_agent_kit.server.reflection_memory_tool import MemoryResult,Summary,Cursor,Reference,Plan
from .documents import POLICY,THEMES,TAG_THEME,classify,validate_document
from .files import read
ACTIONS={
 'acknowledge_then_help':'简短承接用户当前表达的困难，然后继续解决当前任务；不要替用户诊断。',
 'help_only':'直接推进用户当前任务，不主动延伸心理解释。',
 'ask_support_type':'若当前任务仍不明确，询问用户想先倾诉还是获得具体帮助；任务已明确时直接帮助。',
 'respect_distance':'尊重用户表达边界，保持具体帮助，不追问被拒绝的心理话题。',
 'prioritize_actions':'按当前任务提出优先顺序和下一步，避免增加额外负担；不强行打断。',
 'connect_goal_to_choice':'结合用户当前说出的目标解释选项与取舍，不声称存在唯一正确选择。',
 'acknowledge_only':'简短回应用户当前说出的价值与需要，不承诺结果或排他关系。',
}
@dataclass(frozen=True,slots=True)
class BehaviorPolicySnapshot:
    owner_id:str
    revision:int
    desired_json:str
    @classmethod
    def from_settings(cls,owner_id:str,settings:SettingsDTO):
        if settings.owner_id != owner_id: raise ValueError("MEMORY_OWNER_DENIED")
        desired=settings.desired
        for theme in POLICY['themes']:
            if getattr(desired.themes,theme['id']).action not in theme['actions']: raise ValueError('MEMORY_POLICY_INVALID')
        return cls(owner_id,settings.revision,desired.model_dump_json())
    def desired(self):
        from services.admin_data.memory_data import DesiredDTO
        return DesiredDTO.model_validate_json(self.desired_json)

class MemoryTurnProvider:
    def __init__(self,client,current_user,current_text,thread_id,message_id):
        self.data=AdminMemoryData(client);self.actor=current_user['_admin_actor']
        self.owner_id=str(current_user['user_id']);self.current_text=current_text
        self.thread_id=thread_id;self.message_id=message_id;self.snapshot=None;self._resolved={};self.scoped_boundary=False
        self.resolve_timeout=memory_resolve_timeout_seconds()
        try:
            settings=self.data.settings(EmptyDTO(),str(uuid4()),access_token=self.actor.access_token)
            self.snapshot=BehaviorPolicySnapshot.from_settings(self.owner_id,settings)
            if not settings.desired.enabled: return
            from services.admin_data.chat_data import AdminChatData
            from services.admin_data.chat_models import ThreadIdInputDTO
            history=AdminChatData(client).list_messages(ThreadIdInputDTO(thread_id=thread_id),str(uuid4()),access_token=self.actor.access_token)
            for message in history.messages:
                if message.role!='user': continue
                text='\n'.join(part.get('text','') for part in message.parts if isinstance(part,dict) and part.get('type')=='text')
                if re.search(POLICY['boundary_restore'],text): self.scoped_boundary=False
                elif re.search(POLICY['explicit_boundary'],text,re.I) or re.search(POLICY['interpretation_rejection'],text,re.I): self.scoped_boundary=True
            if re.search(POLICY['boundary_restore'],self.current_text): self.scoped_boundary=False
        except (AdminDataError,ValueError): self.snapshot=None
    def refresh_authorization(self,current_user):
        actor=current_user.get('_admin_actor')
        if not isinstance(actor,AdminRequestActor) or actor.canonical_user_id!=self.owner_id: raise AdminDataError('MEMORY_OWNER_DENIED',403)
        self.actor=actor
    def perform_memory_tool(self,request):
        try:
            return self._perform(request)
        except (OSError,ValueError):
            raise AdminDataError('MEMORY_FILE_UNAVAILABLE',503,request.request_id) from None
    def _perform(self,request):
        token=self.actor.access_token
        if request.operation=='memory.list':
            page=self.data.list(ListDTO(limit=request.limit or 20,before=None if request.before is None else request.before.model_dump()),request.request_id,access_token=token)
            return MemoryResult(status='listed',artifacts=[Summary(artifact_id=a.artifact_id,revision=a.revision,report_id=a.report_id,state=a.state,theme_state=a.theme_state,created_at=a.created_at,item_count=a.metadata.item_count if a.metadata else None,failed_sections=a.metadata.failed_sections if a.metadata else []) for a in page.artifacts],next_cursor=Cursor(**page.next_cursor.model_dump()) if page.next_cursor else None)
        if request.operation=='memory.read':
            a=self.data.read(LookupDTO(artifact_id=request.artifact_id,revision=request.revision),request.request_id,access_token=token)
            document=read(a) if a.state=='ready' else None
            return MemoryResult(status=a.state,artifact=Reference(artifact_id=a.artifact_id,revision=a.revision),report_id=a.report_id,document=document,document_sha256=a.document_sha256 if document else None,reason=a.error_code)
        if self.snapshot is None: return MemoryResult(status='unavailable',reason='当前设置读取失败，本轮不使用记忆回应策略。',plans=[])
        rev=self.snapshot.revision
        if self.scoped_boundary or re.search(POLICY['explicit_boundary'],self.current_text,re.I) or re.search(POLICY['interpretation_rejection'],self.current_text,re.I): return MemoryResult(status='explicit_boundary',policy_revision=rev,plans=[],reason='尊重当前任务边界，继续具体帮助。')
        desired=self.snapshot.desired()
        if not desired.enabled: return MemoryResult(status='disabled',policy_revision=rev,plans=[])
        current_tags=set(classify(self.current_text))
        if not current_tags: return MemoryResult(status='no_match',policy_revision=rev,plans=[])
        refs=sorted({(r.artifact_id,r.revision) for r in request.artifacts})
        cache_key=tuple(refs)
        if cache_key in self._resolved: return self._resolved[cache_key]
        by_theme={}
        deadline=time.monotonic()+self.resolve_timeout
        for ident,version in refs:
            if time.monotonic()>=deadline: raise AdminDataError("MEMORY_RESOLVE_TIMEOUT",503,request.request_id)
            a=self.data.read(LookupDTO(artifact_id=ident,revision=version),request.request_id,access_token=token)
            if a.state!='ready' or a.theme_state!='ready': continue
            read(a);read(a,theme=True)
            _,records=validate_document(a,theme=True)
            for row in records:
                tag=row['TriggeringTagId'];theme=TAG_THEME[tag]
                if tag not in current_tags or not getattr(desired.themes,theme).enabled: continue
                entry=by_theme.setdefault(theme,{'sources':set(),'items':set()})
                entry['sources'].add((ident,version));entry['items'].update(row['source_item_ids'])
        if len(by_theme)>1:
            return MemoryResult(status='no_match',policy_revision=rev,plans=[],reason='当前表达包含多个主题，不能确定单一回应方式；继续当前任务帮助。')
        plans=[]
        for theme,entry in by_theme.items():
            action=getattr(desired.themes,theme).action
            plans.append(Plan(theme=theme,action=action,instructions=ACTIONS[action],sources=[Reference(artifact_id=i,revision=v) for i,v in sorted(entry['sources'])],source_item_ids=sorted(entry['items'])))
        result=MemoryResult(status='resolved' if plans else 'no_match',policy_revision=rev,plans=plans,delivery='resolved' if plans else None)
        self._resolved[cache_key]=result
        return result
