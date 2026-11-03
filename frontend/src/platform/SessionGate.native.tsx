// [Sync] 2026-11-02: adopt display-only Kastention naming; existing behavior and technical identities remain.
// [Sync] 2026-11-02: connect original account failures to runtime diagnostics and align the packaged native callback.
// [Sync] 2026-11-02: expose the scene-owned diagnostics button after login and over the existing login sheet; keep session ownership unchanged.
// [Sync] 2026-10-31: release current Native documents before account loss/change/logout; original Cookie/CSRF/login semantics remain.
// [Sync] 2026-10-30: wait for login-sheet dismissal before showing the native home; coalesce login taps and treat closing as cancellation.
// [Sync] 2026-10-29: pass the validated public user to account-scoped native navigation; authentication and session refresh retain their owners.
// [Input] Application-owned backend readiness and normal Web login completion.
// [Sync] 2026-10-29: follow the native local appearance while retaining original session/refresh ownership.
// [Output] Native application session using original BFF Cookie/CSRF semantics.
// [Pos] Native session boundary; the Web view is limited to the existing authentication flow.
// [Sync] 2026-11-01: keep diagnostics reachable while startup/session is pending, without releasing the original account view.
// [Sync] 2026-11-01: retain original session-read errors for the existing diagnostics page.
// [Sync] 2026-11-02: show themed vector/wordmark and a separate preparation footer; diagnostics pauses motion.
// [Sync] 2026-11-03: overlay entry artwork for one visible second on launch/background return, retaining the account subtree.
// [Sync] 2026-10-28: coalesce foreground/401 session reads and apply only the canonical current snapshot.
import { BRAND_NAME } from '../../app/_dream/constants/brand';
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,AppState,Keyboard,NativeEventEmitter,NativeModules,Pressable,Text,View} from 'react-native';
import useInkColors from '../components/useInkColors.native';
import RuntimeDiagnostics from '../components/RuntimeDiagnostics.native';
import StartupScreen from '../components/StartupScreen.native';
import useStartupPresentation from './useStartupPresentation.native';
import {isBrowserSessionCurrent,loadBrowserSession,revokeBrowserSession,type BrowserSession,type BrowserUser} from '../../app/_dream/lib/browserSession';
import {BackendRuntimeManager} from '../runtime/BackendRuntimeManager';
import {clientFetch} from './transport';
export default function SessionGate({children,beforeRelease}: {beforeRelease?:()=>Promise<void>;children: (logout: () => Promise<void>,refresh:()=>Promise<void>,user:BrowserUser) => ReactNode}) {
  const [session, setSession] = useState<BrowserSession | null>(null);
  const currentSession=useRef(session),release=useRef(beforeRelease);currentSession.current=session;release.current=beforeRelease;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [loggingIn,setLoggingIn]=useState(false);
  const [diagnostics,setDiagnostics]=useState(false);
  const [runtimeFailed,setRuntimeFailed]=useState(false);
  const [checkingSession,setCheckingSession]=useState(false);
  const presentation=useStartupPresentation(!diagnostics&&!loggingIn);
  const showStartup=presentation.visible||(!session&&loading);
  const loginPending=useRef(false);
  const inFlight=useRef<Promise<void>|null>(null),mounted=useRef(true);
  const colors=useInkColors(),foreground=colors['color-text-primary'];
  const background=colors['color-bg-app'],surface=colors['color-bg-paper'],border=colors['color-border-paper'];
  const diagnosticsAccess=(session!==null||loggingIn)&&!diagnostics;
  useEffect(()=>{
    NativeModules.InkRuntime?.configureDiagnosticsOverlay?.({enabled:diagnosticsAccess,background,surface,foreground,border});
  },[diagnosticsAccess,background,surface,foreground,border]);
  useEffect(()=>()=>{NativeModules.InkRuntime?.configureDiagnosticsOverlay?.({enabled:false});},[]);
  const startupError=()=>BackendRuntimeManager.getSnapshot().errorCode==='CAPABILITY_UNAVAILABLE'?'当前端侧运行能力尚未就绪。':'本地服务启动失败，请关闭后重新打开应用。';
  function refresh():Promise<void> {
    if(loginPending.current)return Promise.resolve();
    if(inFlight.current)return inFlight.current;
    if(BackendRuntimeManager.getSnapshot().state==='failed') {
      if(mounted.current){setRuntimeFailed(true);setLoading(false);setError(startupError());}
      return Promise.resolve();
    }
    const operation=(async()=>{
      if(mounted.current){setLoading(true);setError('');setCheckingSession(false);}
      try {await BackendRuntimeManager.ensureStarted();if(mounted.current)setCheckingSession(true);BackendRuntimeManager.recordSessionRead('reading');const next=await loadBrowserSession(clientFetch);if(mounted.current && !loginPending.current && isBrowserSessionCurrent(next)){
        BackendRuntimeManager.recordSessionRead(next?'available':'signed_out');
        if(currentSession.current&&currentSession.current.user.id!==next?.user.id)await release.current?.().catch(()=>undefined);
        if(mounted.current&&!loginPending.current&&isBrowserSessionCurrent(next))setSession(next);
      }}
      catch (cause) {
        const failed=BackendRuntimeManager.getSnapshot().state==='failed';
        if(!failed){BackendRuntimeManager.recordSessionRead('unavailable');BackendRuntimeManager.recordError('session',cause);}
        if(mounted.current){setRuntimeFailed(failed);setError(failed?startupError():'工作区暂时无法打开，请重试。');}
      }
      finally {if(mounted.current)setLoading(false);}
    })();
    inFlight.current=operation;void operation.finally(()=>{if(inFlight.current===operation)inFlight.current=null;});return operation;
  }
  useEffect(()=>{mounted.current=true;void refresh();const listener=AppState.addEventListener('change',next=>{presentation.onAppState(next);if(next==='active')void refresh();});return()=>{mounted.current=false;listener.remove();};},[]);
  useEffect(()=>{
    if(typeof NativeModules.InkRuntime?.addListener!=='function'||typeof NativeModules.InkRuntime?.removeListeners!=='function')return;
    const listener=new NativeEventEmitter(NativeModules.InkRuntime).addListener('InkAccountError',(value:unknown)=>{
      if(!value||typeof value!=='object'||!('source' in value)||!('error' in value))return;
      if(value.source==='login'||value.source==='registration'||value.source==='google')BackendRuntimeManager.recordError(value.source,value.error);
    });
    return()=>listener.remove();
  },[]);
  async function login() {
    if(loginPending.current)return;
    loginPending.current=true;setLoggingIn(true);setError('');
    try {
      if(inFlight.current)await inFlight.current;
      await NativeModules.InkRuntime.presentLogin();
      loginPending.current=false;await refresh();
    }
    catch(cause) {
      if(!(cause&&typeof cause==='object'&&'code' in cause&&cause.code==='LOGIN_CANCELLED'))BackendRuntimeManager.recordError('login',cause);
      if(mounted.current&&!(cause&&typeof cause==='object'&&'code' in cause&&cause.code==='LOGIN_CANCELLED'))setError('登录未完成，可重新打开登录页面。');
    }
    finally {loginPending.current=false;if(mounted.current)setLoggingIn(false);}
  }
  async function logout() { await release.current?.().catch(()=>undefined); await revokeBrowserSession(clientFetch); setSession(null); }
  const openDiagnostics=()=>{Keyboard.dismiss();setDiagnostics(true);};
  const content=session?children(logout,refresh,session.user):loading?null:<View style={{flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 20}}>
    <Text style={{fontSize: 24, color:foreground}}>{BRAND_NAME}</Text>
    {loading||loggingIn ? <><ActivityIndicator color={foreground} /><Text style={{color:foreground}}>{loggingIn?'正在登录':checkingSession?'正在检查登录状态':'正在准备本地服务'}</Text></> : !runtimeFailed?<Pressable accessibilityRole="button" onPress={() => void (error ? refresh() : login())} style={{padding: 16}}><Text style={{color:foreground}}>{error ? '重试' : '登录'}</Text></Pressable>:null}
    {error ? <Text accessibilityRole="alert" style={{color:foreground}}>{error}</Text> : null}
    {error && !runtimeFailed && !loading && !loggingIn ? <Pressable accessibilityRole="button" onPress={() => void login()}><Text style={{color:foreground}}>重新登录</Text></Pressable> : null}
    <Pressable accessibilityRole="button" onPress={openDiagnostics} style={{padding:12,minHeight:44}}><Text style={{color:foreground}}>开发者控制页</Text></Pressable>
  </View>;
  return <View style={{flex:1}}>
    <View style={{flex:1}} pointerEvents={diagnostics||showStartup?'none':'auto'} aria-hidden={diagnostics||showStartup} accessibilityElementsHidden={diagnostics||showStartup} importantForAccessibility={diagnostics||showStartup?'no-hide-descendants':'auto'}>{content}</View>
    {showStartup?<View style={{position:'absolute',top:0,bottom:0,left:0,right:0}} pointerEvents={diagnostics?'none':'auto'} aria-hidden={diagnostics} accessibilityElementsHidden={diagnostics} importantForAccessibility={diagnostics?'no-hide-descendants':'auto'}><StartupScreen visible={!diagnostics} checkingSession={checkingSession} onDiagnostics={openDiagnostics}/></View>:null}
    {diagnostics?<View style={{position:'absolute',top:0,bottom:0,left:0,right:0}}><RuntimeDiagnostics onBack={()=>setDiagnostics(false)}/></View>:null}
  </View>;
}
