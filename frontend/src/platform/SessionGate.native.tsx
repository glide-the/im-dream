// [Sync] 2026-10-30: wait for login-sheet dismissal before showing the native home; coalesce login taps and treat closing as cancellation.
// [Sync] 2026-10-29: pass the validated public user to account-scoped native navigation; authentication and session refresh retain their owners.
// [Input] Application-owned backend readiness and normal Web login completion.
// [Sync] 2026-10-29: follow the native local appearance while retaining original session/refresh ownership.
// [Output] Native application session using original BFF Cookie/CSRF semantics.
// [Pos] Native session boundary; the Web view is limited to the existing authentication flow.
// [Sync] 2026-10-28: coalesce foreground/401 session reads and apply only the canonical current snapshot.
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,AppState,NativeModules,Pressable,Text,View} from 'react-native';
import useInkColors from '../components/useInkColors.native';
import {isBrowserSessionCurrent,loadBrowserSession,revokeBrowserSession,type BrowserSession,type BrowserUser} from '../../app/_dream/lib/browserSession';
import {BackendRuntimeManager} from '../runtime/BackendRuntimeManager';
import {clientFetch} from './transport';
export default function SessionGate({children}: {children: (logout: () => Promise<void>,refresh:()=>Promise<void>,user:BrowserUser) => ReactNode}) {
  const [session, setSession] = useState<BrowserSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [loggingIn,setLoggingIn]=useState(false);
  const loginPending=useRef(false);
  const inFlight=useRef<Promise<void>|null>(null),mounted=useRef(true);
  const foreground=useInkColors()['color-text-primary'];
  function refresh():Promise<void> {
    if(loginPending.current)return Promise.resolve();
    if(inFlight.current)return inFlight.current;
    const operation=(async()=>{
      if(mounted.current){setLoading(true);setError('');}
      try {await BackendRuntimeManager.ensureStarted();const next=await loadBrowserSession(clientFetch);if(mounted.current && !loginPending.current && isBrowserSessionCurrent(next))setSession(next);}
      catch {if(mounted.current)setError('工作区暂时无法打开，请重试。');}
      finally {if(mounted.current)setLoading(false);}
    })();
    inFlight.current=operation;void operation.finally(()=>{if(inFlight.current===operation)inFlight.current=null;});return operation;
  }
  useEffect(()=>{mounted.current=true;void refresh();const listener=AppState.addEventListener('change',next=>{if(next==='active')void refresh();});return()=>{mounted.current=false;listener.remove();};},[]);
  async function login() {
    if(loginPending.current)return;
    loginPending.current=true;setLoggingIn(true);setError('');
    try {
      if(inFlight.current)await inFlight.current;
      await NativeModules.InkRuntime.presentLogin();
      loginPending.current=false;await refresh();
    }
    catch(cause) {
      if(mounted.current&&!(cause&&typeof cause==='object'&&'code' in cause&&cause.code==='LOGIN_CANCELLED'))setError('登录未完成，可重新打开登录页面。');
    }
    finally {loginPending.current=false;if(mounted.current)setLoggingIn(false);}
  }
  async function logout() { await revokeBrowserSession(clientFetch); setSession(null); }
  if (session) return children(logout,refresh,session.user);
  return <View style={{flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 20}}>
    <Text style={{fontSize: 24, color:foreground}}>Ink &amp; Memory</Text>
    {loading||loggingIn ? <ActivityIndicator color={foreground} /> : <Pressable accessibilityRole="button" onPress={() => void (error ? refresh() : login())} style={{padding: 16}}><Text style={{color:foreground}}>{error ? '重试' : '登录'}</Text></Pressable>}
    {error ? <Text accessibilityRole="alert" style={{color:foreground}}>{error}</Text> : null}
    {error && !loading && !loggingIn ? <Pressable accessibilityRole="button" onPress={() => void login()}><Text style={{color:foreground}}>重新登录</Text></Pressable> : null}
  </View>;
}
