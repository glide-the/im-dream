# [Input] Authenticated public settings request, revision and original save request ID.
# [Output] Owner-bound behavior state and idempotent CAS result.
# [Pos] Existing Dream browser-auth production entrance; no report page changes.
# [Sync] 2026-10-15: memory behavior get/save and safe unknown-save retry.
from fastapi import APIRouter,Depends,Request,Header
from starlette.concurrency import run_in_threadpool
from fastapi import HTTPException
from services.admin_data.errors import AdminDataError
from services.admin_data.memory_data import AdminMemoryData,EmptyDTO,SettingsSaveDTO
from .deps import get_current_user,get_admin_request_auth,invoke_admin_operation,SafeRequestValidationRoute
router=APIRouter(prefix='/api/memory',tags=['memory'],route_class=SafeRequestValidationRoute)
@router.get('/behavior')
async def get_behavior(current_user=Depends(get_current_user),owner=Depends(get_admin_request_auth)):
    return await invoke_admin_operation(current_user,AdminMemoryData(owner.client).settings,EmptyDTO())
@router.put('/behavior')
async def save_behavior(input_dto:SettingsSaveDTO,request_id:str=Header(alias='X-Request-ID',min_length=1,max_length=256),current_user=Depends(get_current_user),owner=Depends(get_admin_request_auth)):
    return await invoke_admin_operation(current_user,AdminMemoryData(owner.client).save,input_dto,request_id=request_id)

@router.get('/behavior/receipt/{request_id}')
async def behavior_receipt(request_id:str,current_user=Depends(get_current_user),owner=Depends(get_admin_request_auth)):
    actor=current_user['_admin_actor']
    try:
        receipt=await run_in_threadpool(AdminMemoryData(owner.client).save_receipt,request_id,access_token=actor.access_token)
        return {'status':receipt.status,'result':getattr(receipt,'result',None)}
    except AdminDataError as exc:
        raise HTTPException(status_code=exc.status_code,detail={'error_code':exc.code,'outcome_unknown':exc.outcome_unknown}) from None
