// [Sync] 2026-10-29: expose the production shared Hook in a compact explicit technical lane; touch scrolling is qualified separately.
// [Input] Actual Hermes, Foundation UUID, built-in iOS Settings and production settings renderers.
// [Output] Explicit synthetic save/receipt, Product reads, About and five-peer More target qualification.
// [Pos] Isolated entry only; no runtime start, real HTTP, account, credentials, database or model calls.
import '../../src/platform/sdkWebApis.native';
import {useEffect,useState} from 'react';
import {AppRegistry,AppState,Pressable,SafeAreaView,Settings,StyleSheet,TextInput,View} from 'react-native';
import i18n from '../../app/_dream/i18n';
import {initTheme,toggleTheme} from '../../app/_dream/utils/theme.native';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import More from '../../app/_dream/components/story-workspace/layout/MoreNavigationPage.native';
import Memory from '../../app/_dream/views/story-workspace/MemoryBehaviorSettings.native';
import Subscription from '../../app/_dream/views/story-workspace/StoryWorkspaceSubscriptionPage.native';
import About from '../../app/_dream/components/AboutView.native';
import InkLabel from '../../src/components/InkLabel.native';
import useInkColors from '../../src/components/useInkColors.native';
import useMemoryBehaviorSettings from '../../app/_dream/hooks/useMemoryBehaviorSettings';
import {nativeMemoryBehaviorPendingStore,newMemoryBehaviorRequestId} from '../../src/platform/memoryBehavior.native';
import {memorySnapshot,subscriptionContext,subscriptionPlans} from './settings-fixture-data';
const SERVER_KEY='ink-settings-qualification-server';
let snapshot=memorySnapshot;
try{const raw=Settings.get(SERVER_KEY);if(typeof raw==='string')snapshot=JSON.parse(raw);}catch{/* Explicit synthetic fixture data only. */}
let reads=0,writes=0,validUUID=false,mode:'normal'|'unknown'='unknown';
const json=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
const transport:typeof fetch=async(input,init={})=>{
  const path=String(input).split('?')[0];
  if(path==='/auth/session')return json({user:{id:'7',email:'settings@example.invalid',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'c'.repeat(43)});
  if(path==='/api/memory/behavior'&&(init.method??'GET')==='GET'){reads++;return json(snapshot);}
  if(path==='/api/memory/behavior'&&init.method==='PUT'){
    const requestId=new Headers(init.headers).get('X-Request-ID')??'';validUUID=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(requestId);writes++;
    const input=JSON.parse(String(init.body));snapshot={...snapshot,desired:input.desired,revision:snapshot.revision+1};Settings.set({[SERVER_KEY]:JSON.stringify(snapshot)});
    return mode==='unknown'?json({detail:{outcome_unknown:true}},503):json(snapshot);
  }
  if(path.startsWith('/api/memory/behavior/receipt/')){reads++;return json({status:'committed',result:snapshot});}
  if(path==='/api/story-workspace/subscription/context'){reads++;return json(subscriptionContext);}
  if(path==='/api/story-workspace/subscription/plans'){reads++;return json(subscriptionPlans);}
  throw Error('Unexpected synthetic Settings request');
};
initTheme();
function RuntimeContract(){
  const c=useInkColors(),text={color:c['color-text-primary']};
  const state=useMemoryBehaviorSettings({zh:true,transport,pendingStore:nativeMemoryBehaviorPendingStore,newRequestId:newMemoryBehaviorRequestId});
  const button=(label:string,action:()=>void,disabled=false)=><Pressable accessibilityRole="button" disabled={disabled} onPress={action} style={styles.button}><InkLabel style={[text,{opacity:disabled?0.5:1}]}>{label}</InkLabel></Pressable>;
  return <View style={[styles.fill,{padding:12,gap:12}]}>
    <InkLabel style={text}>Hermes shared-hook qualification</InkLabel>
    <InkLabel style={text}>{`Original desired enabled ${String(state.draft?.enabled)} · pending ${String(!!state.pending)}`}</InkLabel>
    {state.message?<InkLabel accessibilityRole={state.error?'alert':undefined} style={text}>{state.message}</InkLabel>:null}
    <View style={styles.actions}>
      {button('Toggle desired',()=>{if(state.draft)state.setDraft({...state.draft,enabled:!state.draft.enabled});},!state.draft||state.busy||!!state.pending)}
      {state.pending?<>{button('Check original receipt',()=>void state.check(),state.busy)}{button('Retry same command',()=>void state.submit(state.pending!),state.busy)}</>:button('Save original command',()=>void state.save(),!state.dirty||state.busy)}
      {button('Load original current',state.loadCurrent,state.busy)}
    </View>
  </View>;
}
function Page(){
  const c=useInkColors(),text={color:c['color-text-primary']};
  const [page,setPage]=useState('more'),[memoryMounted,setMemoryMounted]=useState(false),[draft,setDraft]=useState('Existing unsent Chat draft'),[appState,setAppState]=useState(AppState.currentState),[receipt,setReceipt]=useState('');
  useEffect(()=>{const listener=AppState.addEventListener('change',setAppState);return()=>listener.remove();},[]);
  const report=()=>setReceipt(`reads ${reads} · writes ${writes} · UUID v4 ${String(validUUID)} · mode ${mode}`);
  const button=(label:string,action:()=>void)=><Pressable accessibilityRole="button" onPress={action} style={styles.button}><InkLabel style={text}>{label}</InkLabel></Pressable>;
  return <SafeAreaView style={[styles.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={styles.receipt}><InkLabel style={text}>{`Settings qualification · ${appState}`}</InkLabel><TextInput accessibilityLabel="Source Chat draft" value={draft} onChangeText={setDraft} style={[text,styles.input]}/><View style={styles.actions}>{button('More menu',()=>setPage('more'))}{button('Memory responses',()=>{setMemoryMounted(true);setPage('memory');})}{button('Subscription',()=>setPage('subscription'))}{button('About',()=>setPage('about'))}{button('Read receipt',report)}{button('Normal save',()=>{mode='normal';report();})}{button('Unmount memory',()=>{setMemoryMounted(false);setPage('more');})}{button('Runtime contract',()=>{setMemoryMounted(false);setPage('contract');})}</View>{receipt?<InkLabel style={text}>{receipt}</InkLabel>:null}</View>
    <View style={[styles.fill,page!=='more'?styles.hidden:undefined]}>{page==='more'?<More onNavigate={id=>setReceipt(`Navigation intent ${id}`)} onToggleTheme={toggleTheme} onClose={()=>setPage('home')}/>:null}</View>
    {memoryMounted?<View accessibilityElementsHidden={page!=='memory'} style={[styles.fill,page!=='memory'?styles.hidden:undefined]}><Memory transport={transport} onBack={()=>setPage('more')}/></View>:null}
    {page==='contract'?<RuntimeContract/>:null}
    {page==='subscription'?<Subscription transport={transport} onBack={()=>setPage('more')}/>:null}
    {page==='about'?<About onBack={()=>setPage('more')} openLink={async()=>{setReceipt('Original repository link intent');}}/>:null}
  </SafeAreaView>;
}
function Boot(){const [ready,setReady]=useState(false);useEffect(()=>{void Promise.all([loadBrowserSession(transport),i18n.changeLanguage('zh')]).then(()=>setReady(true));},[]);return ready?<Page/>:<InkLabel>Preparing isolated Settings qualification</InkLabel>;}
AppRegistry.registerComponent('InkMemory',()=>Boot);
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},hidden:{display:'none'},receipt:{padding:12,gap:4},input:{minHeight:44,padding:8,fontFamily:'Excalifont'},actions:{flexDirection:'row',flexWrap:'wrap'},button:{minHeight:44,padding:8,justifyContent:'center'}});
