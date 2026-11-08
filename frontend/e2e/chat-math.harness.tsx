// [Input] Production Web message parts and Native Markdown with synthetic message text.
// [Output] Visible controls for stream snapshots, stop/error presentation, theme and historical remount.
// [Pos] Technical fixture; Project/Episode/artifacts/Run/Hook/database/model are out of scope and receive no writes.
// [Sync] 2026-11-08: exercise actual message renderers without a separate Markdown implementation.
import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import '../app/_dream/i18n';
import '../app/_dream/styles/tokens.css';
import '../app/_dream/styles/markdown.css';
import UserMessagePart from '../app/_dream/components/chat/UserMessagePart';
import {AssistMessagePart} from '../app/_dream/components/chat/AssistMessagePart';
import NativeMarkdown from '../app/_dream/components/chat/ChatMarkdown.native';
import {initTheme, setThemeMode} from '../app/_dream/utils/theme';
import {setThemeMode as setNativeTheme} from '../app/_dream/utils/theme.native';
export interface MathViewControl {
  props: {current: {onMessage: (event: {nativeEvent: {url: string; data: string}}) => void}};
  fail: () => void;
}
declare global {
  interface Window {
    __mathParseDiagram: (source: string) => Promise<unknown>;
    __mathViews?: Record<string, MathViewControl>;
    __mathCopied?: string;
    __mathLinks?: string[];
    __mathWorkspaceLinks?: string[];
  }
}
initTheme();
window.__mathParseDiagram=async(source:string)=>(await import('mermaid')).default.parse(source);
const initial = String.raw`A formula \(x^2 + y^2 = z^2\) inside a sentence.

\[\frac{1}{2} + \sum_{i=1}^n i\]

$$E=mc^2$$`;
// eslint-disable-next-line react-refresh/only-export-components -- This isolated entry owns createRoot rather than a reusable component export.
function Harness() {
  const [text,setText]=useState(initial),[running,setRunning]=useState(false),[error,setError]=useState(false),[revision,setRevision]=useState(0),[visible,setVisible]=useState(true);
  const [theme,setTheme]=useState<'light'|'dark'|'system'>('light');
  return <main>
    <label>Message source<textarea aria-label="Message source" value={text} onChange={event=>setText(event.target.value)}/></label>
    <nav>
      <button onClick={()=>{setRunning(true);setError(false);}}>Stream</button>
      <button onClick={()=>setRunning(false)}>Stop</button>
      <button onClick={()=>{setRunning(false);setError(true);}}>Show error</button>
      <button onClick={()=>{setRunning(false);setError(false);setRevision(value=>value+1);}}>Reload history</button>
      <button onClick={()=>setVisible(value=>!value)}>Toggle message</button>
      <button onClick={()=>{const next=theme==='light'?'dark':theme==='dark'?'system':'light';setTheme(next);setThemeMode(next);setNativeTheme(next);}}>Theme: {theme}</button>
      <button onClick={()=>Object.values(window.__mathViews??{}).forEach(view=>view.fail())}>Fail native document</button>
    </nav>
    <output aria-label="Message state">{running?'running':error?'error':'stopped'}</output>
    {visible?<div key={revision} id="messages" style={{height:460,overflowY:'auto',minWidth:0}}>
      <section id="web-user"><UserMessagePart text={text}/></section>
      <section id="web-assistant"><AssistMessagePart part={{type:'text',text}} message={{id:'math-assistant',role:'assistant',parts:[{type:'text',text}]}} isLoading={running} isLast showActions={!running} isError={error}/></section>
      <section id="native"><NativeMarkdown text={text} workspaceSessionId="fixture-thread" workspaceAvailability="enabled" onOpenLink={value=>(window.__mathLinks??=[]).push(value)} onOpenWorkspace={value=>(window.__mathWorkspaceLinks??=[]).push(value)}/></section>
    </div>:null}
  </main>;
}
createRoot(document.getElementById('root')!).render(<Harness/>);
