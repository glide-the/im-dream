# [Input] Real image-turn adapter, strict DTOs and Host publication with isolated Admin/Provider seams.
# [Output] Unknown-write receipt-only recovery, owner/source checks and native file identity evidence.
# [Pos] Provider-free technical tests; no normal account, model, schema or service.
# [Sync] 2026-10-10: exercise the new turn contract independently of the browser fixture.
import base64
import hashlib
from types import SimpleNamespace
from uuid import uuid4
import pytest
import tests._sdk_stubs  # noqa: F401
from services.admin_data.image_turn_data import (
    AdminImageTurnData, ImageTurnBindInputDTO, ImageTurnBindOutputDTO,
    ImageTurnSelectInputDTO, ImageTurnSelectOutputDTO, ImageTurnResultInputDTO,
    NativeImageSummaryDTO, BIND_IMAGE_TURN, SELECT_IMAGE_OPERATION,
    image_input_digest, image_receipt_key,
)
from services.admin_data.models import CommittedReceiptDTO
from services.admin_data.errors import AdminDataError
from tests.test_image_generation_tool import picture, bound
from tests._image_turn_fixtures import select_provider
from libs.claude_agent_kit.server.image_generation_protocol import IMAGE_TOOL_NAME


def boundary():
    class Client:
        def __init__(self): self.calls=[];self.receipts=[];self.failure=None;self.override=None;self.committed=None;self.available=True
        def supports(self,*_): return self.available
        def execute(self,op,dto,key,**kwargs):
            self.calls.append((op,dto,key,kwargs))
            if op is BIND_IMAGE_TURN: result=ImageTurnBindOutputDTO(**dto.model_dump(),canonical_user_id='7',run_id=None)
            elif op is SELECT_IMAGE_OPERATION: result=ImageTurnSelectOutputDTO(turn_key=dto.turn_key,source_call_id=dto.source_call_id,operation=dto.arguments.operation,arguments_sha256=image_input_digest(dto.arguments.model_dump()),reference_images=dto.arguments.reference_images)
            else: raise AssertionError(op)
            self.committed=result
            if self.failure: raise self.failure
            return self.override or result
        def receipt(self,op,key,**kwargs):
            self.receipts.append((op,key,kwargs))
            return CommittedReceiptDTO(request_id=key,status='committed',operation=op.capability.name,result=self.committed)
    client=Client();grant=SimpleNamespace(purpose='server-persistence',thread_id='thread',run_id=None,token='idg_fixture')
    data=AdminImageTurnData(client,lambda:grant,canonical_user_id='7')
    dto=ImageTurnBindInputDTO(thread_id='thread',turn_id='turn',turn_key='dream-turn-'+'a'*64,message_id='message',ai_model='ai',image_model=None,materials=[])
    return client,grant,data,dto


def test_unknown_commit_only_reads_original_receipt_never_reposts():
    client,grant,data,dto=boundary();client.failure=AdminDataError('ADMIN_UNAVAILABLE',503,None,True)
    with pytest.raises(AdminDataError): data.bind(dto)
    client.failure=None
    assert data.bind(dto).ai_model=='ai'
    assert len(client.calls)==1 and len(client.receipts)==1
    assert client.receipts[0][1]==image_receipt_key(dto.turn_key)
    assert client.receipts[0][2]['access_token']==grant.token


def test_unknown_write_does_not_issue_other_image_operations():
    client,_,data,dto=boundary();client.failure=AdminDataError('ADMIN_UNAVAILABLE',503,None,True)
    with pytest.raises(AdminDataError): data.bind(dto)
    selection=ImageTurnSelectInputDTO(thread_id='thread',turn_key=dto.turn_key,source_call_id='actual',arguments={'operation':'none','prompt':'Discuss image_gen','reference_images':[]})
    with pytest.raises(AdminDataError,match='IMAGE_TURN_OUTCOME_UNKNOWN'): data.select(selection)
    assert len(client.calls)==1 and not client.receipts


@pytest.mark.parametrize('field,value',[('purpose','gateway-cli'),('thread_id','other')])
def test_wrong_grant_cannot_bind(field,value):
    client,grant,data,dto=boundary();setattr(grant,field,value)
    with pytest.raises(AdminDataError,match='IMAGE_TURN_AUTHORITY_REQUIRED'): data.bind(dto)
    assert not client.calls


def test_capability_absence_fails_only_the_image_adapter():
    client,_,data,dto=boundary();client.available=False
    assert not data.ready()
    with pytest.raises(AdminDataError,match='IMAGE_TURN_CONFIGURATION_UNAVAILABLE'): data.bind(dto)
    assert not client.calls


def test_substituted_bind_owner_is_unknown_and_can_only_recover_exact_receipt():
    client,_,data,dto=boundary()
    client.override=ImageTurnBindOutputDTO(**dto.model_dump(),canonical_user_id='8',run_id=None)
    with pytest.raises(AdminDataError) as error: data.bind(dto)
    assert error.value.outcome_unknown
    assert data.bind(dto).canonical_user_id=='7'
    assert len(client.calls)==1 and len(client.receipts)==1


def native(provider):
    args={'prompt':'Make a blue image','reference_images':[]}
    from tests.test_image_chat_public_journey import _catalog_model
    transport=provider.transport
    transport.catalog['data'].append(_catalog_model('ai-model',native=True))
    select_provider(provider,args,operation='native_generate')
    payload=picture();call='ig_actual';gateway='req_'+'b'*32
    provider._image_turn_data.native_summary=NativeImageSummaryDTO(gatewayRequestId=gateway,responseId='resp_actual',providerHttpRequestId='upstream_actual',configuredImageModel=None,reportedImageModel=None,usageKnown=False,usageUnknownReason='responses_image_usage_not_reported',imageCalls=[{'callId':call,'outputIndex':2,'status':'completed','operation':'generate','reportedAction':'generate','format':'png','byteLength':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}])
    block={'type':'image_generation_tool_result','tool_use_id':call,'gateway_request_id':gateway,'response_id':'resp_actual','content':[{'type':'image','source':{'type':'base64','media_type':'image/png','data':base64.b64encode(payload).decode()}}]}
    return block


def test_native_result_keeps_actual_identity_and_original_public_file_contract(bound):
    provider,transport,_,_=bound;block=native(provider)
    result=provider.publish_native(block)
    assert result.requestId=='ig_actual' and result.gatewayRequestId==block['gateway_request_id']
    assert result.responseId=='resp_actual' and result.outputIndex==2 and result.operation=='generate'
    assert (provider.workspace/result.images[0].uri.removeprefix('workspace://')).read_bytes()==picture()
    assert not transport.calls
    with pytest.raises(AdminDataError,match='IMAGE_RESULT_ALREADY_PUBLISHED'): provider.publish_native(block)


def test_native_selection_blocks_explicit_tool_and_damaged_result(bound):
    provider,transport,_,_=bound;block=native(provider)
    with pytest.raises(AdminDataError,match='IMAGE_TURN_SELECTION_MISMATCH'): provider.authorize_tool(IMAGE_TOOL_NAME,'different-route',{'prompt':'Make a blue image','reference_images':[]})
    block['content'][0]['source']['data']=base64.b64encode(b'invalid').decode()
    with pytest.raises(AdminDataError): provider.publish_native(block)
    assert not transport.calls and not provider._published


def test_native_cancel_before_publish_does_not_write_file(bound):
    provider,transport,_,_=bound;block=native(provider);provider.close()
    with pytest.raises(AdminDataError,match='IMAGE_CANCELLED'): provider.publish_native(block)
    assert not (provider.workspace/'files'/'generated').exists() and not transport.calls
def test_native_unavailable_returns_before_saving_selection_or_dispatching_images(bound):
    provider,transport,_,_=bound
    with pytest.raises(AdminDataError,match='AI_MODEL_IMAGE_OPERATION_UNAVAILABLE'):
        select_provider(provider,{'prompt':'Generate an image','reference_images':[]},operation='native_generate')
    assert provider.selected_operation is None and provider._image_turn_data.selection is None
    assert not transport.calls
