// [Sync] 2026-11-13: support Thread receipt reads and unavailable connection fixtures.
// [Input] Explicit synthetic IM catalog/configuration and managed MCP fixtures.
// [Output] Intercepted original public endpoints plus recorded PATCH/PUT receipts for UI tests.
// [Pos] Provider-free test harness only; no real account, model, database or remote MCP.
import type {Page} from '@playwright/test';
import type {GatewayModel} from '../../app/_dream/api/gatewayModelsApi';
import type {ClaudeMcpServer} from '../../app/_dream/api/claudeMcpApi';
export const composerModels:GatewayModel[]=[
  {modelAlias:'fixture-model-a',displayName:'IM Model Alpha',protocol:'anthropic',capabilities:{chat:true},contextWindow:200000,maxOutputTokens:32000,enabled:true,callable:true,availability:'included',requiredPlanCode:null,upgradeHint:null},
  {modelAlias:'fixture-model-b',displayName:'IM Model Beta with a longer label',protocol:'openai',capabilities:{chat:true},contextWindow:128000,maxOutputTokens:16000,enabled:true,callable:true,availability:'included',requiredPlanCode:null,upgradeHint:null},
  {modelAlias:'fixture-model-paid',displayName:'IM Unavailable Model',protocol:'openai',capabilities:{chat:true},contextWindow:128000,maxOutputTokens:16000,enabled:true,callable:false,availability:'upgrade_required',requiredPlanCode:'fixture-plan',upgradeHint:'Fixture subscription required'},
];
export interface ComposerApiOptions {connectionEnabled?:boolean;failure?:number;readFailure?:boolean;modelFailure?:number;modelAppliedOnFailure?:boolean;catalogFailure?:boolean;savedModel?:string;}
export async function installComposerApi(page:Page,options:ComposerApiOptions={}){
  let server:ClaudeMcpServer={name:'research',display_name:'Research library',id:'fixture-mcp',revision:7,enabled:options.connectionEnabled??true,transport:'streamable_http',url:'https://tools.example.invalid/mcp',stdio_profile_key:null,workspace_id:null,state:'connected',auth_state:'anonymous',auth_kind:'none',detail:null,active_operation_id:null,config_scope:'user',removable:true,credential_revision:0,credential_ref:null,credential_configured:false};
  let fail=options.failure,readFailure=options.readFailure,modelFailure=options.modelFailure,catalogFailure=options.catalogFailure,model=options.savedModel??'fixture-model-a';
  const mcpPatches:Record<string,unknown>[]=[],modelPatches:Record<string,unknown>[]=[];
  await page.route('**/api/**',async route=>{
    const request=route.request(),url=new URL(request.url());
    if(!url.pathname.startsWith('/api/'))return route.fallback();
    if(url.pathname==='/api/storage')return route.fulfill({json:{type:'unknown',supportsDirectUpload:false,isConfigured:true}});
    if(url.pathname==='/api/system-config'){
      if(request.method()==='PUT'){
        const body=request.postDataJSON();modelPatches.push(body);
        if(modelFailure){const status=modelFailure;modelFailure=undefined;if(options.modelAppliedOnFailure)model=body.model;return route.fulfill({status,json:{error:{code:'FIXTURE_MODEL_FAILURE'}}});}
        model=body.model;
      }
      return route.fulfill({json:{data:{model,workspace_enabled:true,im_full_access_enabled:false}}});
    }
    if(url.pathname==='/api/gateway/models'){
      if(catalogFailure){catalogFailure=false;return route.fulfill({status:503,json:{error:'fixture catalog unavailable'}});}
      return route.fulfill({json:{data:composerModels,defaultModelAlias:'fixture-model-a'}});
    }
    if(url.pathname==='/api/claude-mcp/capability')return route.fulfill({json:{enabled:true,transports:['streamable_http','sse'],management_mode:'managed_db'}});
    if(url.pathname==='/api/claude-mcp/servers'){
      if(readFailure){readFailure=false;return route.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Fixture list unavailable'}}});}
      return route.fulfill({json:{servers:[server]}});
    }
    if(url.pathname==='/api/claude-mcp/servers/fixture-mcp'&&request.method()==='PATCH'){
      const body=request.postDataJSON();mcpPatches.push(body);
      if(fail){const status=fail;fail=undefined;if(status===409)server={...server,revision:8};return route.fulfill({status,json:{error:{code:status===409?'CONFLICT':'UNAVAILABLE',message:'Fixture save unavailable'}}});}
      if(body.expected_revision!==server.revision)throw Error('Fixture revision mismatch');server={...server,enabled:body.enabled,revision:server.revision!+1};return route.fulfill({json:{server}});
    }
    if(url.pathname.endsWith('/plugin-load-receipt'))return route.fulfill({json:{thread_id:url.pathname.split('/')[4],deck_id:null,workspace_found:false,receipt:null,launch_manifest:null}});
    if(url.pathname==='/api/claude-agent/skill-commands')return route.fulfill({json:{commands:[],skills:[]}});
    throw Error('Unexpected fixture HTTP: '+url.pathname);
  });
  return {mcpPatches,modelPatches};
}
