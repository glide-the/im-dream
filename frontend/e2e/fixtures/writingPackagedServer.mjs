// [Input] An explicit packaged Next loopback origin and original public Writing session/preferences DTOs.
// [Output] Read-only asset proxy plus in-memory account/session boundary for real Simulator WKWebView tests.
// [Pos] Isolated technical HTTP fixture; no real credentials, backend, database, Agent, Hook or model.
import http from 'node:http';
import fs from 'node:fs';
const upstream=new URL(process.env.INK_WRITING_PACKAGED_ORIGIN??'');
if(upstream.hostname!=='127.0.0.1'&&upstream.hostname!=='localhost')throw Error('LOOPBACK_PACKAGED_ORIGIN_REQUIRED');
const output=process.env.INK_WRITING_FIXTURE_RECEIPT;if(!output)throw Error('FIXTURE_RECEIPT_REQUIRED');
const now=()=>new Date().toISOString();
let selected='unhappy',greeting='今天感觉怎么样？',editor=null;
const facts={requests:[],preferenceWrites:[],sessionSaves:[],unexpectedWrites:[],realAccounts:0,modelCalls:0,databaseWrites:0};
function snapshot(){fs.writeFileSync(output,JSON.stringify({...facts,selected},null,2));}
const states={happy:{name:'Happy',prompt:'happy'},ok:{name:'OK',prompt:'ok'},unhappy:{name:'Unhappy',prompt:'unhappy'}};
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,'http://127.0.0.1'),path=url.pathname;
 const json=(value,status=200)=>{res.writeHead(status,{'content-type':'application/json','cache-control':'no-store'});res.end(JSON.stringify(value));};
 let body='';for await(const chunk of req)body+=chunk;let data={};if(body){try{data=JSON.parse(body);}catch{return json({error:'invalid fixture JSON'},400);}}
 if(path.startsWith('/_writing-fixture/')){
  if(path.endsWith('/reset')&&req.method==='POST'){selected=null;editor=null;greeting='今天的感受值得认真记录，请向上滑动查看所有心情。'.repeat(16);snapshot();return json({success:true});}
  if(path.endsWith('/state')&&req.method==='GET')return json({...facts,selected});
  return json({},404);
 }
 if(path==='/auth/session'){facts.requests.push({method:req.method,path});return json({user:{id:'20261101',email:'writing-fixture@example.invalid',display_name:'Writing fixture',avatar_url:null,role:'user',created_at:null},csrf_token:'w'.repeat(43)});}
 if(path.startsWith('/api/')){
  facts.requests.push({method:req.method,path});snapshot();
  if(path==='/api/preferences'){
   if(req.method==='POST'){if('selected_state' in data){selected=data.selected_state;facts.preferenceWrites.push({selected_state:selected});}snapshot();return json({success:true});}
   return json({first_login_completed:true,timezone:'Asia/Shanghai',selected_state:selected,updated_at:now(),state_config:{states,greeting}});
  }
  if(path==='/api/sessions/events'){res.writeHead(200,{'content-type':'text/event-stream','cache-control':'no-store'});res.write(': connected\n\n');return;}
  if(path==='/api/sessions'){
   if(req.method==='POST'){editor=data.editor_state;facts.sessionSaves.push({session_id:data.session_id,textCells:editor?.cells?.filter(cell=>cell.type==='text').length??0});snapshot();return json({success:true});}
   return json({sessions:[{id:'writing-fixture-session',created_at:now(),updated_at:now(),labels:[]}]});
  }
  if(path==='/api/sessions/writing-fixture-session')return json({id:'writing-fixture-session',created_at:now(),updated_at:now(),labels:[],editor_state:editor??{id:'writing-fixture-session',createdAt:now(),selectedState:selected??undefined,cells:[{id:'writing-fixture-cell',type:'text',content:''}],commentors:[],tasks:[],weightPath:[],overlappedPhrases:[],notFoundPhrases:[]}});
  if(req.method==='GET')return json(path==='/api/decks'||path==='/api/decks/catalog'?{decks:[]}:path==='/api/claude-agent/threads'?{threads:[]}:{});
  facts.unexpectedWrites.push({method:req.method,path});snapshot();return json({error:'UNEXPECTED_FIXTURE_WRITE'},501);
 }
 // All HTML/font/chunk bytes come from the packaged production server. No HTML or JS rewriting.
 const target=new URL(req.url,upstream);
 const headers={...req.headers,host:upstream.host};delete headers.connection;
 const proxy=http.request(target,{method:req.method,headers},response=>{res.writeHead(response.statusCode??502,response.headers);response.pipe(res);});
 proxy.on('error',()=>{if(!res.headersSent)res.writeHead(502);res.end('Packaged server unavailable');});
 if(body)proxy.write(body);proxy.end();
});
server.listen(0,'127.0.0.1',()=>{const address=server.address();snapshot();console.log(JSON.stringify({origin:`http://127.0.0.1:${address.port}`,upstream:upstream.origin,receipt:output}));});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>{snapshot();server.closeAllConnections();server.close(()=>process.exit(0));});
