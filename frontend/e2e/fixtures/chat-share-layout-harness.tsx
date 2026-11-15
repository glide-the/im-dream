// [Input] Identical synthetic text in the production Chat list, public reader and export card.
// [Output] Side-by-side message presentation and an actual PNG capture for style verification.
// [Pos] Provider-free fixture; Project/Episode/Artifact/Run/Hook/PostgreSQL and real accounts are out of scope.
import {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import type {UIMessage} from 'ai';
import ChatMessageList from '../../app/_dream/components/chat/ChatMessageList';
import PublicShareContent from '../../app/_dream/components/sharing/PublicShareContent';
import ThreadImageCard from '../../app/_dream/components/chat/ThreadImageCard';
import {renderThreadImage, releaseThreadImage, type RenderedThreadImage} from '../../app/_dream/components/chat/exportThreadImage';
import type {ExportChatMessage, ExportImageLabels} from '../../app/_dream/components/chat/chatImageProjection';
import {setThemeMode} from '../../app/_dream/utils/theme';
import i18n from '../../app/_dream/i18n';
import '../../app/_dream/index.css';
await i18n.changeLanguage('en');
const sample = [
  {role: 'user' as const, content: '今天想整理一下计划。\n\n**先做一件事**，保留 `draft` 和原来的换行。'},
  {role: 'assistant' as const, content: '先写下一个小目标，再继续行动。\n\n- 保留你的节奏\n- 看见已经完成的部分\n\n```ts\nconst memory = "hello";\n```\n\n公式：\\(x^2 + y^2 = 1\\)\n\n| 任务 | 状态 |\n| --- | --- |\n| 写一段 | 已完成 |'.replace('const memory = "hello";', 'const memory = "hello";\nconst draft = "' + 'draft'.repeat(40) + '";')},
];
const messages: UIMessage[] = sample.map((m,index) => ({id: String(index),role: m.role,parts: [{type: 'text',text: m.content}]}));
const projected: ExportChatMessage[] = sample.map(m => ({role:m.role,files:[],blocks:[{kind:'text',text:m.content}]}));
const labels: ExportImageLabels = {you:'You',assistant:'AI',footer:'Kastention',thinking:'Thinking',truncated:'Truncated',workspaceImageUnavailable:'Image unavailable'};
export function Fixture() {
  const [preview,setPreview] = useState<RenderedThreadImage|null>(null), [busy,setBusy] = useState(false);
  const [capturedDiagram, setCapturedDiagram] = useState('');
  useEffect(() => () => releaseThreadImage(preview), [preview]);
  async function capture(invalid = false) {
    setBusy(true);
    setCapturedDiagram('');
    const diagram = invalid ? 'invalid diagram' : 'graph LR\n  A[Plan] --> B[Write]';
    try {
      const next = await renderThreadImage({
        threadId:'style-fixture',title:'分享预览',
        messages:[...projected,{role:'assistant',files:[],blocks:[{kind:'text',text:`\`\`\`mermaid\n${diagram}\n\`\`\``}]}],labels,
      }, {onProgress: () => {
        const block = document.querySelector('.chat-share-image [data-markdown-media-kind="mermaid"]');
        setCapturedDiagram(`${block?.getAttribute('data-render-state')}:${Boolean(block?.querySelector('.markdown-media-block__preview svg'))}`);
      }});
      setPreview(next);
    } finally {setBusy(false);}
  }
  return <main style={{padding:16,minHeight:'100dvh',background:'var(--color-bg-app)',color:'var(--color-text-primary)'}}>
    <nav style={{display:'flex',flexWrap:'wrap',gap:12,marginBottom:16}}><button onClick={()=>setThemeMode('light')}>Light</button><button onClick={()=>setThemeMode('dark')}>Dark</button><button disabled={busy} onClick={()=>void capture()}>{busy?'Capturing':'Capture PNG'}</button><button disabled={busy} onClick={()=>void capture(true)}>Capture invalid diagram</button></nav>
    <output data-testid="capture-state">{capturedDiagram}</output>
    <div style={{display:'grid',gridTemplateColumns:'minmax(0, 1fr)',gap:24}}>
      <section data-testid="reference" style={{width:'100%',maxWidth:720,minWidth:0}}><h2>Chat 页面</h2><ChatMessageList messages={messages} threadId="" isLoading={false} addToolResult={()=>{}} readonly/></section>
      <section data-testid="public" style={{width:'100%',maxWidth:720,minWidth:0}}><PublicShareContent snapshot={{kind:'chat',title:'分享预览',created_at:null,messages:sample}}/></section>
      <section data-testid="image" style={{maxWidth:'100%',overflowX:'auto'}}><ThreadImageCard title="分享预览" messages={projected} labels={labels} dateText="2026-11-13"/></section>
      {preview ? <section data-testid="png">{preview.images.map(image=><img key={image} src={image} alt="Captured Chat preview" style={{maxWidth:'100%',height:'auto'}}/>)}</section> : null}
    </div>
  </main>;
}
createRoot(document.getElementById('root')!).render(<Fixture/>);
