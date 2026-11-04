// [Input] Production App/Chat hooks and public history DTOs with a synthetic authenticated HTTP boundary.
// [Output] App deletion composition evidence; fixture persistence lives only in this browser's sessionStorage.
// [Pos] APP-01 technical fixture; no real account, database, runtime startup, model or native device operation.
// [Sync] 2026-11-03: supply a valid positive decimal synthetic user ID to the production session parser.
// [Sync] 2026-11-02: model explicit DELETE rejection statuses and count the production session-expiry callback.
import React from 'react';
import {createRoot} from 'react-dom/client';
import App from '../../src/App';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import i18n from '../../app/_dream/i18n';

await i18n.changeLanguage('en');
await loadBrowserSession(async()=>Response.json({user:{id:'910000001',email:'delete@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'a'.repeat(43)}));
const storageKey='app-01-delete-fixture-rows';
const now=new Date().toISOString();
const initialRows=[
  {id:'fixture-delete-a',title:'Mountain walk notes',created_at:now,updated_at:now},
  {id:'fixture-delete-b',title:'Garden reading notes',created_at:now,updated_at:now},
  {id:'fixture-delete-untitled',title:null,created_at:now,updated_at:now},
];
const f=(window as any).__appDeleteFixture={
  rows:JSON.parse(sessionStorage.getItem(storageKey)||JSON.stringify(initialRows)),
  calls:[] as Array<{path:string;method:string;headers:Record<string,string>}>,
  alerts:[] as any[],closures:0,failDelete:false,deleteStatus:null as number|null,sessionRefreshes:0,holdDelete:false,pending:[] as Array<()=>void>,
  failClosed:[] as string[],switchAccount:undefined as undefined|(()=>void),
};
window.fetch=async(input,init={})=>{
  const url=new URL(String(input),'http://fixture.invalid'),path=url.pathname,method=init.method||'GET';
  f.calls.push({path:url.pathname+url.search,method,headers:Object.fromEntries(new Headers(init.headers))});
  if(path==='/api/system-config')return Response.json({workspace_enabled:true,im_full_access_enabled:false});
  if(path==='/api/decks'||path==='/api/decks/catalog')return Response.json({decks:[]});
  if(path==='/api/claude-agent/scheduled-tasks/day')return Response.json({tasks:[],triggers:[]});
  if(path==='/api/claude-agent/threads'&&method==='GET'){
    const query=url.searchParams.get('query')?.toLowerCase();
    const rows=query?f.rows.filter((row:any)=>row.title?.toLowerCase().includes(query)):f.rows;
    const offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||rows.length);
    return Response.json({threads:rows.slice(offset,offset+limit)});
  }
  const match=/^\/api\/claude-agent\/threads\/([^/]+)(?:\/(messages|status|inputs))?$/.exec(path);
  if(match){
    const id=decodeURIComponent(match[1]),row=f.rows.find((item:any)=>item.id===id),resource=match[2];
    if(method==='DELETE'&&!resource){
      const reply=()=>{
        if(f.deleteStatus)return Response.json({detail:'Fixture deletion rejected'},{status:f.deleteStatus});
        if(f.failDelete)return Response.json({detail:'Fixture deletion unavailable'},{status:503});
        f.rows=f.rows.filter((item:any)=>item.id!==id);sessionStorage.setItem(storageKey,JSON.stringify(f.rows));
        return Response.json({ok:true});
      };
      return f.holdDelete?new Promise<Response>(resolve=>f.pending.push(()=>resolve(reply()))):reply();
    }
    if(!row)return Response.json({detail:'Fixture not found'},{status:404});
    if(resource==='messages')return Response.json({thread:row,messages:[{id:id+'-message',role:'assistant',parts:[{type:'text',text:'Saved body: '+(row.title||'Untitled fixture')}],metadata:{turnStatus:'completed'},created_at:row.created_at}],has_more:false,next_cursor:null,latest_message_id:id+'-message',unchanged:false});
    if(resource==='status')return Response.json({running:false,lifecycle:'idle',turn_count:1,pending_tool_call_ids:[],tool_confirmation_observation:'known'});
    if(resource==='inputs')return Response.json({entries:[],local_owner:true});
  }
  f.failClosed.push(method+' '+path);
  throw new Error('UNEXPECTED_APP_DELETE_FIXTURE_REQUEST: '+method+' '+path);
};
createRoot(document.getElementById('root')!).render(<App/>);
