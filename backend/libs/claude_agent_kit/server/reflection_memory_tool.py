# [Sync] 2026-10-25: accept an explicit per-server broker context for embedded MCP; default stdio behavior and tool schemas remain unchanged.
# [Input] Model-selected opaque artifact references and private turn broker capability.
# [Output] Three strict owner-bound memory Tools, with no path, actor or current-message selector.
# [Pos] User MCP memory surface; Admin credentials stay exclusively in the Host.
# [Sync] 2026-10-15: keep Tool descriptions role-only; input schemas retain nullable cursor semantics.
# [Sync] 2026-10-15: L2 list/read and current-task behavior resolution.
# [Sync] 2026-10-15: explain personal-recall triggers, source/date checks, and optional L3 response adaptation.
# [Sync] 2026-10-15: publish nullable first-page cursor matching MemoryRequest; malformed cursors remain rejected.
from __future__ import annotations
import json
import os
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .session_projection_protocol import SessionProjectionBrokerClient,SessionProjectionProtocolError,SessionProjectionErrorDTO
class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True,hide_input_in_errors=True)
class Reference(Strict):
    artifact_id:str=Field(pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    revision:int=Field(ge=1,le=2147483647)
class Cursor(Strict):
    created_at:str
    artifact_id:str=Field(pattern=r'^[0-9a-f-]{36}$')
class MemoryRequest(Strict):
    capability:str=Field(pattern=r'^[A-Za-z0-9_-]{43}$',repr=False)
    request_id:str=Field(min_length=1,max_length=256)
    operation:Literal['memory.list','memory.read','memory.resolve']
    limit:int|None=Field(default=None,ge=1,le=100)
    before:Cursor|None=None
    artifact_id:str|None=None
    revision:int|None=Field(default=None,ge=1,le=2147483647)
    artifacts:list[Reference]|None=Field(default=None,max_length=100)
    @model_validator(mode='after')
    def shape(self):
        if self.operation=='memory.list': valid=self.artifact_id is None and self.revision is None and self.artifacts is None
        elif self.operation=='memory.read': valid=self.artifact_id is not None and self.revision is not None and self.limit is None and self.before is None and self.artifacts is None
        else: valid=self.artifacts is not None and self.limit is None and self.before is None and self.artifact_id is None and self.revision is None
        if not valid: raise ValueError('Invalid memory arguments')
        if self.artifact_id is not None: Reference(artifact_id=self.artifact_id,revision=self.revision)
        return self
class Summary(Reference):
    report_id:str
    state:Literal['pending','running','publishing','ready','empty','failed']
    theme_state:Literal['pending','ready','empty','failed']
    created_at:str
    item_count:int|None
    failed_sections:list[str]
class Plan(Strict):
    theme:str
    action:str
    instructions:str
    sources:list[Reference]
    source_item_ids:list[str]
class MemoryResult(Strict):
    status:Literal['listed','ready','pending','running','publishing','empty','failed','resolved','disabled','no_match','explicit_boundary','unavailable']
    artifacts:list[Summary]|None=None
    next_cursor:Cursor|None=None
    artifact:Reference|None=None
    report_id:str|None=None
    document:str|None=None
    document_sha256:str|None=None
    policy_revision:int|None=None
    plans:list[Plan]|None=None
    reason:str|None=None
    delivery:Literal['resolved']|None=None
class MemoryResponse(Strict):
    ok:bool
    result:MemoryResult|None=None
    error:SessionProjectionErrorDTO|None=None
    @model_validator(mode='after')
    def shape(self):
        if self.ok!=(self.result is not None) or self.ok==(self.error is not None): raise ValueError('Invalid memory response')
        return self
class MemoryBrokerClient(SessionProjectionBrokerClient):
    def command(self,operation,values,call_id):
        request=MemoryRequest(capability=self._capability,request_id=call_id,operation=operation,**values)
        raw=self._round_trip(request,call_id)
        response=MemoryResponse.model_validate_json(raw)
        if not response.ok: self._raise_remote_error(response.error,call_id)
        return response.result
_OBJ={'type':'object','additionalProperties':False}
_REF={**_OBJ,'properties':{'artifact_id':{'type':'string'},'revision':{'type':'integer','minimum':1}},'required':['artifact_id','revision']}
_CURSOR={**_OBJ,'properties':{'created_at':{'type':'string'},'artifact_id':{'type':'string','pattern':r'^[0-9a-f-]{36}$'}},'required':['created_at','artifact_id']}
MEMORY_TOOL_SPECS={
 'list_memory_distillations':('列出当前用户的 Reflections 记忆蒸馏目录、版本、完成状态和分页信息。只读。',{**_OBJ,'properties':{'limit':{'type':'integer','minimum':1,'maximum':100,'default':20},'before':{'description':'首页省略或传null；翻页只传上页原样返回的next_cursor。','anyOf':[_CURSOR,{'type':'null'}],'default':None}}}),
 'read_memory_distillation':('读取指定版本的 memory_distillation.md，返回记忆观察及其来源信息。只读。',_REF),
 'resolve_memory_behavior':('根据当前任务和行为设置，解析指定记忆主题可采用的回应行动。不修改记忆或设置。',{**_OBJ,'properties':{'artifacts':{'type':'array','items':_REF,'maxItems':100}},'required':['artifacts']}),
}
_OPERATIONS={'list_memory_distillations':'memory.list','read_memory_distillation':'memory.read','resolve_memory_behavior':'memory.resolve'}
def handle_memory_tool(name,arguments,call_id,*,environment=None):
    if arguments is None and name=='list_memory_distillations': arguments={}
    if not isinstance(arguments,dict): raise ValueError('Invalid memory arguments')
    operation=_OPERATIONS[name]
    allowed={'memory.list':{'limit','before'},'memory.read':{'artifact_id','revision'},'memory.resolve':{'artifacts'}}[operation]
    if set(arguments)-allowed: raise ValueError('Invalid memory arguments')
    try:
        result=MemoryBrokerClient.from_env(dict(os.environ if environment is None else environment)).command(operation,arguments,call_id)
        return result.model_dump_json(exclude_none=True)
    except SessionProjectionProtocolError as error:
        return json.dumps({'status':'unavailable','error_code':error.code})
