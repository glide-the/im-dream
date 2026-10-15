# [Input] Production source conversion, private files, Host resolver and real strict DTOs.
# [Output] Provider-free complete memory chain, snapshot/refusal, recovery and owner-boundary evidence.
# [Pos] Isolated memory technical validation; no normal database or provider calls.
# [Sync] 2026-10-15: reproduce normal-model Chinese refusal miss and Thread history recovery without changing source conversion.
# [Sync] 2026-10-15: initial L2/L3 business-contract cases.
from types import SimpleNamespace
from unittest.mock import Mock
from dataclasses import replace
from uuid import uuid4
import json
from hashlib import sha256
import pytest
from pydantic import ValidationError
from services.admin_data.memory_data import ArtifactDTO,SourceDTO,SettingsDTO,AdminMemoryData,MEMORY_OPERATIONS,MEMORY_REQUIREMENTS,EmptyDTO
from services.admin_data.request_auth import AdminRequestActor
from services.memory.documents import convert,decode,digest,classify,POLICY,validate_document
from services.memory.files import publish,read
from services.memory.behavior import MemoryTurnProvider,BehaviorPolicySnapshot
from libs.claude_agent_kit.server.reflection_memory_tool import MemoryRequest

OWNER='7001';STAMP='2026-10-15T01:00:00Z'
@pytest.fixture
def chain(tmp_path,monkeypatch):
    monkeypatch.setenv('MEMORY_ARTIFACT_ROOT',str(tmp_path/'memory'))
    task=str(uuid4());rid='9007199254740993';result=str(uuid4())
    source=SourceDTO.model_validate({'analysis_content':None,'task_id':task,'report_id':rid,'report_sha256':'a'*64,'start_date':None,'end_date':None,'completed_sections':['echoes','patterns'],'created_at':STAMP,'echoes':[{'id':result,'task_id':task,'section':'echoes','title':'工作受阻后的感受','description':'我工作卡住时感到挫败，面对截止时间也感到焦虑。','related_session_ids':['note-1'],'evidence':'我觉得工作卡住了，很沮丧；截止时间让我紧张。','confidence':'medium','created_at':STAMP}],'traits':[],'patterns':[],'failed_sections':['traits']})
    a=ArtifactDTO(artifact_id=str(uuid4()),revision=1,report_id=rid,state='running',theme_state='pending',created_at=STAMP,source_sha256=digest(source.model_dump_json()),conversion_revision='memory-rules-v1',document=None,document_sha256=None,body_sha256=None,byte_length=None,theme_document=None,theme_sha256=None,metadata=None,error_code=None)
    document,body,theme,meta=convert(source,a)
    a=a.model_copy(update={'state':'ready','theme_state':'ready','document':document,'document_sha256':digest(document),'body_sha256':body,'byte_length':len(document.encode()),'theme_document':theme,'theme_sha256':digest(theme),'metadata':meta})
    desired={'enabled':True,'themes':{t['id']:{'enabled':True,'action':t['default_action']} for t in POLICY['themes']}}
    settings=SettingsDTO(owner_id=OWNER,catalog=[{k:t[k] for k in ('id','label','actions','default_action')} for t in POLICY['themes']],revision=1,taxonomy_revision='memory-rules-v1',default={**desired,'enabled':False},desired=desired,updated_at=STAMP)
    data=Mock();data.settings.return_value=settings;data.read.return_value=a
    monkeypatch.setattr('services.memory.behavior.AdminMemoryData',lambda _:data)
    monkeypatch.setattr('services.admin_data.chat_data.AdminChatData',lambda _:SimpleNamespace(list_messages=lambda *args,**kwargs:SimpleNamespace(messages=[])))
    actor=AdminRequestActor(subject='memory-user',canonical_user_id=OWNER,client_id='fixture-client',scopes=frozenset({'dream:read','dream:write'}),issued_at=1,expires_at=2,access_token='synthetic-owner-token')
    user={'user_id':OWNER,'_admin_actor':actor}
    def provider(text): return MemoryTurnProvider(Mock(),user,text,'thread-fixture','message-fixture')
    def request(op,**fields): return MemoryRequest(capability='A'*43,request_id=str(uuid4()),operation=op,**fields)
    return source,a,data,settings,provider,request

def test_report_to_l2_l3_read_resolve_and_reopen(chain):
    source,a,data,settings,provider,request=chain
    publish(a);publish(a,theme=True)
    first=provider('我工作卡住了，很沮丧，帮我整理下一步。')
    actual=first.perform_memory_tool(request('memory.read',artifact_id=a.artifact_id,revision=1))
    assert actual.document==a.document and actual.report_id==source.report_id
    result=first.perform_memory_tool(request('memory.resolve',artifacts=[{'artifact_id':a.artifact_id,'revision':1}]))
    assert result.status=='resolved' and result.policy_revision==1
    assert result.plans[0].theme=='THEME_FRUSTRATION'
    _,l2=decode(actual.document)
    assert l2[0]['evidence_kind']=='analysis_inference' and l2[0]['sources'][0]['confidence']=='medium'
    assert a.metadata.failed_sections==['traits']
    reopened=provider('我工作卡住了，很沮丧，帮我整理下一步。')
    assert reopened.perform_memory_tool(request('memory.read',artifact_id=a.artifact_id,revision=1)).document==actual.document

def test_missing_file_recovers_canonical_bytes_without_conversion(chain):
    _,a,*_=chain
    p=publish(a);p.unlink()
    assert read(a)==a.document and p.read_text()==a.document

def test_duplicate_observation_merges_sources_without_certainty_upgrade(chain):
    source,a,*_=chain
    original=source.echoes[0]
    source=source.model_copy(update={'patterns':[original.model_copy(update={'id':str(uuid4()),'section':'patterns','confidence':'low'})]})
    doc,_,_,meta=convert(source,a)
    _,items=decode(doc)
    assert meta.item_count==1 and len(items[0]['sources'])==2
    assert [s['confidence'] for s in items[0]['sources']]==['medium','low']

def test_empty_report_has_no_l2_or_l3(chain):
    source,a,*_=chain
    assert convert(source.model_copy(update={'echoes':[]}),a)[:3]==(None,None,None)

@pytest.mark.parametrize('text',['数据库迁移必须先完成，截止时间是周五。','请写小说，角色觉得工作受阻很沮丧。','我已经不觉得有压力了。','不是我，是同事工作卡住很沮丧。','只修复代码，不要分析情绪。'])
def test_current_task_counterexamples_do_not_trigger(text): assert classify(text)==[]

def test_policy_is_frozen_and_next_turn_reads_new_revision(chain):
    _,a,data,settings,provider,request=chain
    first=provider('我工作卡住了，很沮丧。')
    changed=settings.model_copy(update={'revision':2,'desired':settings.desired.model_copy(update={'enabled':False})})
    data.settings.return_value=changed
    selected=[{'artifact_id':a.artifact_id,'revision':1}]
    assert first.perform_memory_tool(request('memory.resolve',artifacts=selected)).policy_revision==1
    next_turn=provider('我工作卡住了，很沮丧。')
    assert next_turn.perform_memory_tool(request('memory.resolve',artifacts=selected)).status=='disabled'

def test_explicit_boundary_overrides_on_switch(chain):
    _,a,_,_,provider,request=chain
    p=provider('不要再分析我的情绪，只给我任务方案。')
    assert p.perform_memory_tool(request('memory.resolve',artifacts=[{'artifact_id':a.artifact_id,'revision':1}])).status=='explicit_boundary'

def test_symlink_and_tamper_are_rejected(chain,tmp_path):
    _,a,*_=chain
    p=publish(a);p.write_text(a.document+'changed')
    with pytest.raises(ValueError): read(a)
    p.unlink();other=tmp_path/'other';other.write_text(a.document);p.symlink_to(other)
    with pytest.raises(OSError): read(a)
    with pytest.raises(ValueError): publish(a)

@pytest.mark.parametrize('field,value',[('user_id','other'),('path','/private/data'),('current_text','invented')])
def test_model_cannot_select_actor_path_or_current_text(field,value):
    with pytest.raises(ValidationError): MemoryRequest.model_validate({'capability':'A'*43,'request_id':'call','operation':'memory.resolve','artifacts':[],field:value})

def test_exact_capability_fail_closed():
    client=Mock();client.supports.return_value=False
    from services.admin_data.errors import AdminDataError
    with pytest.raises(AdminDataError): AdminMemoryData(client).settings(EmptyDTO(),'request',access_token='fixture')
    client.supports.assert_called_once_with(MEMORY_OPERATIONS,MEMORY_REQUIREMENTS)
    client.execute.assert_not_called()

def test_worker_replays_publishing_bytes_without_converter(chain,monkeypatch):
    _,a,*_=chain
    from services.memory.worker import MemoryWorker
    from services.admin_data.memory_data import ClaimResultDTO
    worker=MemoryWorker(Mock());worker.data=Mock()
    worker.data.invoke.side_effect=[SimpleNamespace(discovered=0),ClaimResultDTO(artifact=a.model_copy(update={'state':'publishing'}),claim_token=str(uuid4()),source=None),a]
    monkeypatch.setattr('services.memory.worker.convert',lambda *args:pytest.fail('canonical recovery must not reconvert'))
    assert worker.step()
    names=[call.args[0] for call in worker.data.invoke.call_args_list]
    assert names==['memory.artifacts.discover','memory.artifacts.claim','memory.artifacts.publish']

def test_theme_publication_failure_keeps_l2_publishable(chain,monkeypatch):
    _,a,*_=chain
    from services.memory.worker import MemoryWorker
    from services.admin_data.memory_data import ClaimResultDTO
    from services.memory.files import publish as real_publish
    worker=MemoryWorker(Mock());worker.data=Mock()
    worker.data.invoke.side_effect=[SimpleNamespace(discovered=0),ClaimResultDTO(artifact=a.model_copy(update={'state':'publishing'}),claim_token=str(uuid4()),source=None),a]
    def fail_theme(artifact,theme=False):
        if theme: raise OSError('synthetic-publication-failure')
        return real_publish(artifact)
    monkeypatch.setattr('services.memory.worker.publish',fail_theme)
    assert worker.step()
    command=worker.data.invoke.call_args.args[1]
    assert command.document_sha256==a.document_sha256 and command.theme_published is False
    assert command.theme_error_code=='MEMORY_THEME_PUBLICATION_FAILED'
    assert read(a)==a.document

def test_unknown_stage_never_marks_conversion_failed(chain):
    source,a,*_=chain
    from services.memory.worker import MemoryWorker
    from services.admin_data.memory_data import ClaimResultDTO
    from services.admin_data.errors import AdminDataError
    worker=MemoryWorker(Mock());worker.data=Mock()
    claimed=a.model_copy(update={'state':'running','metadata':None,'document':None,'document_sha256':None,'body_sha256':None,'byte_length':None,'theme_document':None,'theme_sha256':None})
    worker.data.invoke.side_effect=[SimpleNamespace(discovered=0),ClaimResultDTO(artifact=claimed,claim_token=str(uuid4()),source=source),AdminDataError('ADMIN_OPERATION_UNAVAILABLE',503,'fixture-unknown',True)]
    assert worker.step()
    assert 'memory.artifacts.fail' not in [call.args[0] for call in worker.data.invoke.call_args_list]

def test_theme_reference_must_exist_in_exact_l2_version(chain):
    _,a,*_=chain
    header,records=decode(a.theme_document)
    records[0]['source_item_ids']=[str(uuid4())]
    from services.memory.documents import encode
    changed,_=encode(header,'Reflections 记忆主题',records)
    damaged=a.model_copy(update={'theme_document':changed,'theme_sha256':digest(changed)})
    with pytest.raises(ValueError,match='MEMORY_SOURCE_MISMATCH'):validate_document(damaged,theme=True)

def test_setting_owner_mismatch_fails_snapshot(chain):
    _,_,_,settings,*_=chain
    with pytest.raises(ValueError):BehaviorPolicySnapshot.from_settings('other-owner',settings)

def test_real_private_broker_round_trip_uses_bound_owner_and_current_message(chain):
    _,a,data,_,provider,_=chain
    from services.admin_data.session_projection_broker import SessionProjectionBroker,SessionProjectionBrokerSettings
    from libs.claude_agent_kit.server.reflection_memory_tool import MemoryBrokerClient
    broker=SessionProjectionBroker(Mock(),settings=SessionProjectionBrokerSettings(timeout_seconds=2,max_bytes=1024*1024))
    broker.bind_memory_provider(provider('我工作卡住了，很沮丧，帮我整理下一步。'))
    broker.start()
    try:
        client=MemoryBrokerClient.from_env(broker.child_env())
        result=client.command('memory.read',{'artifact_id':a.artifact_id,'revision':1},'fixture-read')
        assert result.document==a.document
        resolved=client.command('memory.resolve',{'artifacts':[{'artifact_id':a.artifact_id,'revision':1}]},'fixture-resolve')
        assert resolved.status=='resolved' and resolved.plans[0].action=='acknowledge_then_help'
        assert all(call.kwargs['access_token']=='synthetic-owner-token' for call in data.read.call_args_list)
        with pytest.raises(ValidationError):client.command('memory.resolve',{'artifacts':[],'current_text':'invented'},'invalid-call')
    finally:broker.close()

def test_rejected_interpretation_remains_thread_scoped_and_can_be_reopened(chain,monkeypatch):
    _,a,_,_,provider,request=chain
    history=SimpleNamespace(messages=[SimpleNamespace(role='user',parts=[{'type':'text','text':'这个心理判断不符合我的情况。'}])])
    monkeypatch.setattr('services.admin_data.chat_data.AdminChatData',lambda _:SimpleNamespace(list_messages=lambda *args,**kwargs:history))
    p=provider('我工作卡住了，很沮丧，帮我整理下一步。')
    assert p.perform_memory_tool(request('memory.resolve',artifacts=[{'artifact_id':a.artifact_id,'revision':1}])).status=='explicit_boundary'
    reopened=provider('现在可以聊我的感受了。我工作卡住了，很沮丧。')
    assert reopened.perform_memory_tool(request('memory.resolve',artifacts=[{'artifact_id':a.artifact_id,'revision':1}])).status=='resolved'

@pytest.mark.parametrize('text',[
    '这次不要根据历史回顾解释我的心理，也不要延伸情绪分析。请先检查这次的记忆回应是否应该停用，然后只帮我把当前事情整理成一个最小行动清单。',
    '也不要延伸情绪分析，只帮我整理待办。',
    '请不要根据回顾解释我的心理。',
])
def test_direct_current_refusal_precedes_empty_or_matching_themes(chain,text):
    _,a,data,_,provider,request=chain
    result=provider(text).perform_memory_tool(request('memory.resolve',artifacts=[{'artifact_id':a.artifact_id,'revision':1}]))
    assert result.status=='explicit_boundary' and result.policy_revision==1 and result.plans==[]
    data.read.assert_not_called()

def test_quoted_refusal_is_a_translation_task_not_a_new_boundary(chain):
    _,a,_,_,provider,request=chain
    result=provider('请翻译句子“不要根据历史回顾解释我的心理”。').perform_memory_tool(request('memory.resolve',artifacts=[{'artifact_id':a.artifact_id,'revision':1}]))
    assert result.status=='no_match'

def test_natural_refusal_survives_thread_reopen_and_explicit_restore(chain,monkeypatch):
    _,a,_,_,provider,request=chain
    history=SimpleNamespace(messages=[SimpleNamespace(role='user',parts=[{'type':'text','text':'这次不要根据历史回顾解释我的心理，也不要延伸情绪分析。'}])])
    monkeypatch.setattr('services.admin_data.chat_data.AdminChatData',lambda _:SimpleNamespace(list_messages=lambda *args,**kwargs:history))
    refs=[{'artifact_id':a.artifact_id,'revision':1}]
    assert provider('我工作卡住了，很沮丧。').perform_memory_tool(request('memory.resolve',artifacts=refs)).status=='explicit_boundary'
    assert provider('现在可以聊我的感受了。我工作卡住了，很沮丧。').perform_memory_tool(request('memory.resolve',artifacts=refs)).status=='resolved'

def test_theme_conversion_retry_reads_published_l2_without_rewriting_it(chain,monkeypatch):
    source,a,*_=chain
    from services.memory.worker import MemoryWorker
    from services.admin_data.memory_data import ClaimResultDTO
    worker=MemoryWorker(Mock());worker.data=Mock()
    claimed=a.model_copy(update={'theme_state':'failed','theme_document':None,'theme_sha256':None})
    worker.data.invoke.side_effect=[SimpleNamespace(discovered=0),ClaimResultDTO(artifact=claimed,claim_token=str(uuid4()),source=source),a,a]
    monkeypatch.setattr('services.memory.worker.convert',lambda *args:pytest.fail('L3 retry must not rewrite L2'))
    assert worker.step()
    staged=worker.data.invoke.call_args_list[2].args[1]
    assert staged.document==a.document and staged.body_sha256==a.body_sha256

@pytest.fixture
def public_settings(chain):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routers import memory as routes
    _,_,_,settings,*_=chain
    client=Mock();client.supports.return_value=True;client.execute.return_value=settings
    actor=AdminRequestActor(subject='memory-user',canonical_user_id=OWNER,client_id='fixture-client',scopes=frozenset({'dream:read','dream:write'}),issued_at=1,expires_at=2,access_token='synthetic-owner-token')
    app=FastAPI();app.include_router(routes.router)
    app.dependency_overrides[routes.get_current_user]=lambda:{'user_id':OWNER,'_admin_actor':actor}
    app.dependency_overrides[routes.get_admin_request_auth]=lambda:SimpleNamespace(client=client)
    with TestClient(app) as browser:yield browser,client,settings

def test_public_settings_get_uses_authenticated_owner(public_settings):
    browser,client,settings=public_settings
    response=browser.get('/api/memory/behavior')
    assert response.status_code==200 and response.json()['owner_id']==OWNER
    assert client.execute.call_args.args[0].capability.name=='memory.behavior.get'
    assert client.execute.call_args.kwargs=={'access_token':'synthetic-owner-token'}

def test_public_settings_save_forwards_original_key_and_revision(public_settings):
    browser,client,settings=public_settings
    key=str(uuid4())
    response=browser.put('/api/memory/behavior',headers={'X-Request-ID':key},json={'expected_revision':1,'desired':settings.desired.model_dump()})
    assert response.status_code==200
    operation,value,request=client.execute.call_args.args
    assert operation.capability.name=='memory.behavior.save' and request==key and value.expected_revision==1
    assert client.execute.call_args.kwargs['access_token']=='synthetic-owner-token'

def test_public_settings_unknown_result_preserves_safe_error_and_key(public_settings):
    browser,client,settings=public_settings
    from services.admin_data.errors import AdminDataError
    key=str(uuid4());client.execute.side_effect=AdminDataError('ADMIN_OPERATION_UNAVAILABLE',503,key,True)
    response=browser.put('/api/memory/behavior',headers={'X-Request-ID':key},json={'expected_revision':1,'desired':settings.desired.model_dump()})
    assert response.status_code==503 and response.json()['detail']['outcome_unknown'] is True
    assert response.json()['detail']['request_id']==key

def test_public_settings_extra_effective_or_actor_is_rejected_before_admin(public_settings):
    browser,client,settings=public_settings
    response=browser.put('/api/memory/behavior',headers={'X-Request-ID':str(uuid4())},json={'expected_revision':1,'desired':settings.desired.model_dump(),'effective':{},'user_id':'other'})
    assert response.status_code==422;client.execute.assert_not_called()

def test_public_settings_receipt_uses_original_owner_and_safe_result(public_settings):
    browser,client,settings=public_settings
    from services.admin_data.models import CommittedReceiptDTO
    key=str(uuid4());client.receipt.return_value=CommittedReceiptDTO[SettingsDTO](status='committed',operation='memory.behavior.save',request_id=key,result=settings)
    response=browser.get('/api/memory/behavior/receipt/'+key)
    assert response.status_code==200 and response.json()['result']['owner_id']==OWNER
    assert client.receipt.call_args.args[1]==key and client.receipt.call_args.kwargs['access_token']=='synthetic-owner-token'
