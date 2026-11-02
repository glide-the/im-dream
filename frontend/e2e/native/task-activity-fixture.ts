// [Input] Explicit synthetic task records and controlled HTTP outcomes for Native presentation tests.
// [Output] Fixture-only original DTO responses, pending reads and safe request metadata.
// [Pos] Provider-free technical data; no production transport, credentials, model or database.
export function createTaskActivityFixture(){
 const f={mode:'all',fail:new Set<string>(),hold:new Set<string>(),calls:[] as {path:string;method:string;signal?:AbortSignal|null;headers:Record<string,string>}[],pending:[] as {path:string;signal?:AbortSignal|null;release:()=>void}[],navigation:[] as string[],scheduled:[] as string[],expired:0,version:0,interval:100_000};
 const transport:typeof fetch=async(input,init={})=>{
  const path=String(input);
  if(path==='/auth/session')return new Response(JSON.stringify({user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
  f.calls.push({path,method:init.method??'GET',signal:init.signal,headers:Object.fromEntries(new Headers(init.headers).entries())});
  const id=decodeURIComponent(path.split('/threads/')[1]?.split('/')[0]??'fixture-thread'),child=id==='child-thread';
  const link={task_id:'task-one',source_thread_id:'fixture-thread',thread_id:'child-thread',title:'Review task '+f.version,launch_status:'starting',launch_error_code:null,created_at:'2026-10-30T00:00:00Z'};
  const allowed=(key:string)=>!child&&(f.mode==='all'||f.mode===key),key=path.includes('/tasks/')?'detail':path.split('/').at(-1)!;
  let body:unknown;
  if(key==='task-links')body={source:child?{...link,source_title:'Original conversation'}:null,created:allowed('links')?[link]:[]};
  else if(key==='detail')body={task_id:'task-one',thread_id:'child-thread',title:link.title,launch_status:'starting',error_code:null,status:'idle',running:false};
  else if(key==='scheduled-tasks')body={source:null,created:allowed('scheduled')?[{id:'schedule-one',source_thread_id:id,title:'Morning note',prompt:'Fixture only',rule:{kind:'daily',local_time:'09:00',time_zone:'Asia/Shanghai'},run_thread_mode:'source_thread',model_alias:'fixture-model',next_run_at:null,status:'active',revision:1,created_at:'2026-10-30T00:00:00Z',updated_at:'2026-10-30T00:00:00Z'}]:[]};
  else if(key==='plan')body={thread_id:id,exists:allowed('plan'),plan_mode:allowed('plan')?'planning':'none',slug:'review',file_name:'review.md',content:allowed('plan')?'## Original plan\n\nReview the current work.':null,content_bytes:40,truncated:false,updated_at:'2026-10-30T00:00:00Z'};
  else if(key==='todos')body={thread_id:id,exists:allowed('todos'),source:'task_v2',todos:allowed('todos')?Array.from({length:5},(_,i)=>({id:'todo-'+i,content:'Todo item '+i,status:i===0?'completed':i===1?'in_progress':'pending',active_form:i===1?'Reviewing item 1':null,owner:i===1?'Reviewer':null,blocked_by:i===2?['previous task']:[]})):[],truncated:false,updated_at:'2026-10-30T00:00:00Z'};
  else if(key==='subagents')body={exists:allowed('agents'),tasks:allowed('agents')?(['running','completed','failed','cancelled'] as const).map((status,i)=>({task_id:'agent-'+i,agent_id:'agent-'+i,agent_type:'reviewer',description:'Review subagent '+i,summary:'Saved summary '+i,status,tool_call_id:'agent-call-'+i,spawn_depth:1,started_at:'2026-10-30T00:00:00Z',finished_at:status==='running'?null:'2026-10-30T00:01:00Z',duration_ms:60_000,error:status==='failed'?'Fixture execution failed':null,activity:[],messages:[
   {id:'dispatch',sequence:1,kind:'task',timestamp:null,text:'Review this synthetic document.',status:null,tool_name:null,tool_call_id:null,input:null,output:null},
   {id:'tool-call',sequence:2,kind:'tool_call',timestamp:null,text:null,status:'started',tool_name:'Read',tool_call_id:'read-one',input:'fixture.txt',output:null,redacted:true},
   {id:'tool-result',sequence:3,kind:'tool_result',timestamp:null,text:null,status:'completed',tool_name:'Read',tool_call_id:'read-one',input:null,output:'SYNTHETIC REDACTED BODY MUST STAY HIDDEN',redacted:true,truncated:true},
   {id:'final',sequence:4,kind:'final',timestamp:null,text:'## Review complete\n\nSaved result remains readable.',status:status,tool_name:null,tool_call_id:null,input:null,output:null}
  ],message_count:4,messages_truncated:true,projection_version:2})):[],updated_at:null};
  else throw Error('Unexpected technical fixture operation');
  const failed=f.fail.has(key);
  if(f.hold.has(key))await new Promise<void>(resolve=>f.pending.push({path,signal:init.signal,release:resolve}));
  return new Response(JSON.stringify(failed?{}:body),{status:failed?503:200});
 };
 return {f,transport};
}
