# [Input] Actual five Deck mutation routes/auth/DTO transport and controlled Admin responses.
# [Output] Original results/policy/deletion messages, strict detail ownership and unknown receipt evidence.
# [Pos] Provider-free Deck mutation harness; no copied transaction or normal business data.
# [Sync] 2026-09-15: fence public Deck SQL and verify code-owned deletion reasons and original UUIDs.
# [Sync] 2026-09-16: fence the public route from transitive Dream database imports used for error text.
from __future__ import annotations
import json
from pathlib import Path
from uuid import UUID
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from routers.voices import router
from services.admin_data import AdminDataClient, AdminDataConfig, AdminDataError
from services.admin_data.deck_mutation_data import AdminDeckMutationData, DECK_MUTATION_OPERATIONS
from services.admin_data.deck_version_data import DECK_VERSION_SCHEMA_REQUIREMENTS
from services.admin_data.models import AbsentReceiptDTO, CommittedReceiptDTO
from services.admin_data.request_auth import AdminRequestAuth
from tests.test_admin_request_auth import Verifier
HEADERS={'authorization':'Bearer write-token'}
ROUTES=[('put','/api/decks/deck-1','deck.update',{'name':'新名'}),('delete','/api/decks/deck-1','deck.delete',None),
 ('post','/api/decks/deck-1/publish','deck.toggle-publication',None),('post','/api/decks/deck-1/fork','deck.collect',None),
 ('post','/api/decks/deck-1/sync','deck.sync-parent',None)]


def test_public_deck_route_has_no_dream_database_dependency():
 source=Path(__file__).parents[1]/'routers'/'voices.py';text=source.read_text(encoding='utf-8')
 assert 'import database' not in text and 'database.' not in text

@pytest.fixture
def boundary(monkeypatch):
 import database
 monkeypatch.setattr(database,'get_db',lambda:pytest.fail('Public Deck mutations must not use Dream PG'))
 for name in ('update_deck','delete_deck','fork_deck','increment_deck_install_count','get_deck_with_voices','publish_deck','unpublish_deck','sync_deck_with_parent'):
  assert not hasattr(database,name)
 config=AdminDataConfig(base_url='https://admin.example',issuer='https://admin.example/api/auth',resource='https://dream.example/api',service_client_id='dream-service',service_secret='s'*32)
 outputs={'deck.update':{'changed':True},'deck.delete':{'changed':True},'deck.toggle-publication':{'published':True},'deck.collect':{'deck_id':'collected-deck'},'deck.sync-parent':{'success':True,'synced_voices':5}}
 schemas=[s.model_dump() for s in DECK_VERSION_SCHEMA_REQUIREMENTS];operations=[s.capability.model_dump() for s in DECK_MUTATION_OPERATIONS]
 calls=[];receipts={};receipt_calls=[]
 class DeckVerifier(Verifier):
  def verify(self,token,*,required_scopes):
   if token.startswith('idg_'):raise AdminDataError('INVALID_ACCESS_TOKEN',401)
   return super().verify(token,required_scopes=required_scopes)
 def handler(request):
  request_id=request.headers['x-request-id'];UUID(request_id)
  if request.url.path.endswith('/capabilities'):
   value={'version':'1','auth':{'issuer':config.issuer,'jwks_uri':config.jwks_uri,'resource':config.resource,'algorithm':'ES256','clients':{'browser':'dream-browser','device':'dream-device'},'scopes':['dream:read','dream:write'],'delegations':[]},'schema_capabilities':schemas,'operations':operations}
  elif request.url.path.endswith('/principal'):
   value={'subject':'opaque-ba-subject','canonical_user_id':'42','client_id':'dream-browser','scopes':['dream:read'] if request.headers['authorization']=='Bearer read-token' else ['dream:read','dream:write'],'status':'active'}
  elif '/receipts/' in request.url.path:
   name=request.url.params['operation'];receipt_calls.append((name,request_id));value=receipts.get(request_id,{'status':'absent','operation':name,'request_id':request_id})
  else:
   name=request.url.path.rsplit('/',1)[-1];body=json.loads(request.content)
   assert set(body)=={'request_id','input'} and body['request_id']==request_id
   assert not {'user_id','actor_id','subject'} & body['input'].keys()
   assert request.headers['authorization']=='Bearer write-token' and 'cookie' not in request.headers
   calls.append((name,body['input'],request_id));value=outputs[name]
   if isinstance(value,Exception):raise value
   if isinstance(value,tuple):
    status,code,details=value;error={'code':code,'message':'private SQL token/body'}
    if details is not ...:error['details']=details
    return httpx.Response(status,json={'request_id':request_id,'error':error})
  return httpx.Response(200,json={'request_id':request_id,'data':value})
 http=httpx.Client(transport=httpx.MockTransport(handler));client=AdminDataClient(config,client=http,operations=DECK_MUTATION_OPERATIONS)
 app=FastAPI();app.state.admin_request_auth=AdminRequestAuth(config,client=client,verifier=DeckVerifier());app.include_router(router)
 with TestClient(app) as browser:yield browser,calls,outputs,schemas,operations,AdminDeckMutationData(client),receipts,receipt_calls
 http.close()

def call(browser,method,url,body=None,headers=HEADERS):return browser.request(method.upper(),url,headers=headers,**({'json':body} if body is not None else {}))

@pytest.mark.parametrize('method,url,name,body',ROUTES)
def test_all_five_original_results_are_one_admin_operation(boundary,method,url,name,body):
 browser,calls,*_=boundary;r=call(browser,method,url,body)
 expected={'success':True,'published':True} if name.endswith('publication') else {'deck_id':'collected-deck'} if name.endswith('collect') else {'success':True,'synced_voices':5} if name.endswith('parent') else {'success':True}
 assert r.status_code==200 and r.json()==expected and len(calls)==1
 assert calls[0][1]==({'deck_id':'deck-1','updates':{'name':'新名'}} if name=='deck.update' else {'deck_id':'deck-1'})

def test_update_null_omitted_empty_false_zero_preserved(boundary):
 browser,calls,*_=boundary
 assert call(browser,'put','/api/decks/deck-1',{'name':None,'description':'','enabled':False,'order_index':0}).json()=={'success':True}
 assert calls[0][1]['updates']=={'description':'','enabled':False,'order_index':0}
 assert call(browser,'put','/api/decks/deck-1',{}).status_code==200 and calls[1][1]['updates']=={}

@pytest.mark.parametrize('published',[True,False])
def test_publish_keeps_toggle_result_without_deck_preread(boundary,published):
 browser,calls,outputs,*_=boundary;outputs['deck.toggle-publication']={'published':published}
 r=call(browser,'post','/api/decks/deck-1/publish');assert r.json()=={'success':True,'published':published} and len(calls)==1

@pytest.mark.parametrize('method,name',[('put','deck.update'),('delete','deck.delete')])
def test_changed_false_keeps_original_404(boundary,method,name):
 browser,_,outputs,*_=boundary;outputs[name]={'changed':False};r=call(browser,method,'/api/decks/deck-1',{} if method=='put' else None)
 assert r.status_code==404 and r.json()=={'detail':'Deck not found or permission denied'}

@pytest.mark.parametrize('reason,message',[
 ('child_decks','Deck cannot be deleted while derived Decks still reference it.'),
 ('related_threads','Deck cannot be deleted while related Chat conversations still exist.'),
 ('runtime_history','Deck cannot be deleted because it has immutable runtime history.'),
 ('referenced_records','Deck cannot be deleted because it is still referenced.')])
def test_four_closed_delete_reasons_keep_original_messages(boundary,reason,message):
 browser,_,outputs,*_=boundary;outputs['deck.delete']=(409,'DECK_DELETE_BLOCKED',{'reason':reason});r=call(browser,'delete','/api/decks/deck-1')
 assert r.status_code==409 and r.json()=={'detail':message} and 'private SQL' not in r.text

@pytest.mark.parametrize('code,details',[('DECK_DELETE_BLOCKED',{'reason':'private unknown'}),('DECK_DELETE_BLOCKED',{'reason':'child_decks','sql':'private'}),
 ('DECK_DELETE_BLOCKED',None),('OTHER_ERROR',{'reason':'child_decks'}),('DECK_VERSION_CONFLICT',{'reason':'child_decks'}),
 ('DECK_DELETE_BLOCKED',{'current_draft_revision':1,'current_version':None})])
def test_error_details_are_closed_and_owned_by_code(boundary,code,details):
 browser,calls,outputs,*_=boundary;outputs['deck.delete']=(409,code,details);r=call(browser,'delete','/api/decks/deck-1')
 assert r.status_code==503 and r.json()['detail']=={'error_code':'ADMIN_RESPONSE_INVALID','request_id':calls[0][2],'outcome_unknown':True}
 assert 'private unknown' not in r.text

@pytest.mark.parametrize('name,code,status,url,expected_status,message',[
 ('deck.toggle-publication','DEFAULT_DECK_PUBLISH_FORBIDDEN',409,'/api/decks/deck-1/publish',409,'System-initialized Decks cannot be published'),
 ('deck.collect','SELF_COLLECTION_FORBIDDEN',409,'/api/decks/deck-1/fork',409,'You cannot collect your own published Deck'),
 ('deck.collect','COLLECTION_SOURCE_UNAVAILABLE',404,'/api/decks/deck-1/fork',409,'Only system or published Decks can be collected'),
 ('deck.collect','DECK_ACCESS_DENIED',404,'/api/decks/deck-1/fork',404,'Deck deck-1 not found'),
 ('deck.toggle-publication','DECK_ACCESS_DENIED',404,'/api/decks/deck-1/publish',404,'Deck not found or not owned by user'),
 ('deck.sync-parent','DECK_ACCESS_DENIED',404,'/api/decks/deck-1/sync',400,'Deck not found or permission denied'),
 ('deck.sync-parent','DECK_PARENT_MISSING',409,'/api/decks/deck-1/sync',400,'Deck is not a fork (no parent)'),
 ('deck.sync-parent','DECK_PARENT_MISSING',404,'/api/decks/deck-1/sync',400,'Parent deck not found')])
def test_known_policy_and_parent_errors_keep_original_feedback(boundary,name,code,status,url,expected_status,message):
 browser,_,outputs,*_=boundary;outputs[name]=(status,code,...);r=call(browser,'post',url)
 assert r.status_code==expected_status and r.json()=={'detail':message} and 'private SQL' not in r.text

@pytest.mark.parametrize('method,url,name,body',ROUTES)
def test_unknown_write_original_receipt_only_no_retry(boundary,method,url,name,body):
 browser,calls,outputs,_,_,data,receipts,receipt_calls=boundary;outputs[name]=httpx.ReadTimeout('private token/body');r=call(browser,method,url,body);rid=calls[0][2]
 assert r.status_code==504 and r.json()['detail']=={'error_code':'ADMIN_TIMEOUT','request_id':rid,'outcome_unknown':True}
 spec=next(x for x in DECK_MUTATION_OPERATIONS if x.capability.name==name)
 assert isinstance(data.receipt(spec,rid,access_token='write-token'),AbsentReceiptDTO)
 result={'deck_id':'original-copy'} if name=='deck.collect' else {'published':False} if name.endswith('publication') else {'success':True,'synced_voices':0} if name.endswith('parent') else {'changed':True}
 receipts[rid]={'status':'committed','operation':name,'request_id':rid,'result':result};committed=data.receipt(spec,rid,access_token='write-token')
 assert isinstance(committed,CommittedReceiptDTO) and committed.result.model_dump()==result and len(calls)==1 and receipt_calls==[(name,rid)]*2

@pytest.mark.parametrize('method,url,name,body',ROUTES)
@pytest.mark.parametrize('token,status',[('read-token',403),('idg_synthetic',401)])
def test_mutations_require_current_user_oauth(boundary,method,url,name,body,token,status):
 browser,calls,*_=boundary;r=call(browser,method,url,body,{'authorization':'Bearer '+token});assert r.status_code==status and not calls

@pytest.mark.parametrize('mutation',['schema-missing','schema-hash','schema-duplicate','op-missing','op-hash'])
def test_exact_four_schema_hash_gates_before_domain_io(boundary,mutation):
 browser,calls,_,schemas,operations,*_=boundary
 if mutation=='schema-missing':schemas.pop()
 elif mutation=='schema-hash':schemas[0]['contract_sha256']='0'*64
 elif mutation=='schema-duplicate':schemas.append(schemas[0].copy())
 elif mutation=='op-missing':operations.pop(0)
 else:operations[0]['contract_sha256']='0'*64
 r=call(browser,'put','/api/decks/deck-1',{});assert r.status_code==503 and not calls and not r.json()['detail']['outcome_unknown']

@pytest.mark.parametrize('raw',['{"enabled":0}','{"user_id":42}','{"order_index":NaN}','{"order_index":9007199254740992}','{"name":3}'])
def test_public_update_validation_safe_422_without_echo(boundary,raw):
 browser,calls,*_=boundary;r=browser.put('/api/decks/deck-1',headers={**HEADERS,'content-type':'application/json'},content=raw)
 assert r.status_code==422 and r.json()=={'detail':'Invalid Deck request'} and not calls

@pytest.mark.parametrize('name,url,value',[
 ('deck.update','/api/decks/deck-1',{'changed':1}),
 ('deck.delete','/api/decks/deck-1',{'changed':True,'sql':'private'}),
 ('deck.toggle-publication','/api/decks/deck-1/publish',{'published':0}),
 ('deck.collect','/api/decks/deck-1/fork',{'deck_id':''}),
 ('deck.sync-parent','/api/decks/deck-1/sync',{'success':1,'synced_voices':0}),
 ('deck.sync-parent','/api/decks/deck-1/sync',{'success':False,'synced_voices':0}),
 ('deck.sync-parent','/api/decks/deck-1/sync',{'success':True,'synced_voices':-1}),
 ('deck.sync-parent','/api/decks/deck-1/sync',{'success':True,'synced_voices':True}),
 ('deck.sync-parent','/api/decks/deck-1/sync',{'success':True,'synced_voices':9007199254740992})])
def test_malformed_write_results_keep_original_unknown_id(boundary,name,url,value):
 browser,calls,outputs,*_=boundary;outputs[name]=value
 method='put' if name=='deck.update' else 'delete' if name=='deck.delete' else 'post'
 response=call(browser,method,url,{} if method=='put' else None)
 assert response.status_code==503 and response.json()['detail']=={'error_code':'ADMIN_RESPONSE_INVALID','request_id':calls[0][2],'outcome_unknown':True}
 assert len(calls)==1 and 'private' not in response.text

def test_optional_delete_details_keep_generic_original_conflict(boundary):
 browser,_,outputs,*_=boundary;outputs['deck.delete']=(409,'DECK_DELETE_BLOCKED',...)
 response=call(browser,'delete','/api/decks/deck-1')
 assert response.status_code==409 and response.json()=={'detail':'Deck cannot be deleted because it is still referenced.'}
