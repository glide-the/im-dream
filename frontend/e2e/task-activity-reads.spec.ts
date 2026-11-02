// [Input] Production task/plan/todo/subagent readers with explicit fixture-only HTTP and original CSRF session.
// [Output] Shared DTO/cancellation/header, store-independent reads and late plan-mode compatibility evidence.
// [Pos] Provider-free contract; no real account, model, database or network.
import {test,expect} from '@playwright/test';
import {loadBrowserSession,clearBrowserSession} from '../app/_dream/lib/browserSession';
import {fetchTaskSessionLinks,fetchTaskSessionDetail} from '../app/_dream/components/chat/taskSessionLinks';
import {readThreadPlan} from '../app/_dream/hooks/useThreadPlan';
import {readThreadTodos} from '../app/_dream/hooks/useThreadTodos';
import {readThreadSubagents} from '../app/_dream/hooks/useThreadSubagents';
import {getThreadScheduledTasks} from '../app/_dream/api/scheduledTaskApi';
const session={user:{id:'1',email:'fixture@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)};
const link={task_id:'task-one',source_thread_id:'thread/with space',thread_id:'child-thread',title:'Review task',launch_status:'starting',launch_error_code:null,created_at:'2026-10-30T00:00:00Z'};
test.beforeEach(async()=>{clearBrowserSession();await loadBrowserSession((async()=>new Response(JSON.stringify(session))) as typeof fetch);});
test.afterEach(()=>clearBrowserSession());
test('all task snapshot readers use the same cancellable authenticated GET and original projections',async()=>{
 const calls:{path:string;init:RequestInit}[]=[],controller=new AbortController();
 const transport:typeof fetch=async(input,init={})=>{
  const path=String(input);calls.push({path,init});let body:unknown;
  if(path.endsWith('/task-links'))body={source:null,created:[link]};
  else if(path.endsWith('/tasks/task-one'))body={task_id:'task-one',thread_id:'child-thread',title:'Review task',launch_status:'starting',error_code:null,status:'idle',running:false,result_text:'Private result must stay outside this projection'};
  else if(path.endsWith('/scheduled-tasks'))body={source:null,created:[]};
  else if(path.endsWith('/plan'))body={thread_id:'thread/with space',exists:true,plan_mode:'exited',slug:'review',file_name:'review.md',content:'## Original plan',content_bytes:16,truncated:false,updated_at:null};
  else if(path.endsWith('/todos'))body={exists:true,source:'task_v2',todos:[{id:'todo',content:'Review',active_form:null,status:'pending',owner:null,blocked_by:[]}],truncated:true,updated_at:null};
  else if(path.endsWith('/subagents'))body={exists:true,tasks:[{task_id:'agent',agent_id:'agent',agent_type:'reviewer',description:'Review',summary:'Completed',status:'completed',tool_call_id:'agent-call',spawn_depth:1,started_at:null,finished_at:null,duration_ms:100,activity:[]}],updated_at:null};
  else throw new Error('Unexpected fixture path');
  return new Response(JSON.stringify(body),{status:200});
 };
 const options={transport,signal:controller.signal},id='thread/with space';
 const [links,detail,scheduled,plan,todos,subagents]=await Promise.all([fetchTaskSessionLinks(id,options),fetchTaskSessionDetail(id,'task-one',options),getThreadScheduledTasks(id,options),readThreadPlan(id,options),readThreadTodos(id,options),readThreadSubagents(id,options)]);
 expect(links.created).toEqual([link]);expect(detail.status).toBe('idle');expect('result_text' in detail).toBe(false);expect(scheduled.created).toEqual([]);
 expect(plan).toMatchObject({planMode:'exited',content:'## Original plan'});expect(todos.source).toBe('task_v2');expect(todos.truncated).toBe(true);
 expect(subagents.tasks[0].messages).toEqual(expect.arrayContaining([expect.objectContaining({kind:'final',text:'Completed',legacy:true})]));
 expect(calls).toHaveLength(6);
 for(const call of calls){expect(call.path).toContain('/threads/thread%2Fwith%20space/');expect(call.init.method??'GET').toBe('GET');expect(call.init.body).toBeUndefined();expect(call.init.signal).toBe(controller.signal);expect(new Headers(call.init.headers).get('x-ink-csrf')).toBe(session.csrf_token);expect(new Headers(call.init.headers).get('authorization')).toBeNull();}
 controller.abort();expect(calls.every(call=>call.init.signal?.aborted)).toBe(true);
});
test('shared readers report HTTP failures and empty projections retain their original modes',async()=>{
 const transport=(async()=>new Response('{}',{status:503})) as typeof fetch;
 for(const read of [readThreadPlan,readThreadTodos,readThreadSubagents])await expect(read('fixture',{transport})).rejects.toThrow();
 const empty=(async()=>new Response(JSON.stringify({exists:false,plan_mode:'planning'}))) as typeof fetch;
 expect(await readThreadPlan('fixture',{transport:empty})).toMatchObject({exists:false,planMode:'planning',content:null});
 expect(await readThreadTodos('fixture',{transport:empty})).toMatchObject({exists:false,todos:[],source:null});
});
test('the plan reader uses the latest fallback mode after a pending REST response',async()=>{
 let mode:'planning'|'exited'='planning',release!:(response:Response)=>void;
 const transport=(()=>new Promise<Response>(resolve=>{release=resolve;})) as typeof fetch;
 const pending=readThreadPlan('pending-mode-fixture',{transport},()=>mode);
 mode='exited';release(new Response(JSON.stringify({exists:true,slug:'review',file_name:'review.md',content:'Saved plan',content_bytes:10,truncated:false,updated_at:null})));
 expect(await pending).toMatchObject({exists:true,planMode:'exited',content:'Saved plan'});
});
