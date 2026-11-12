// [Input] Production note share components and synthetic prose/clipboard/save boundaries.
// [Output] Visible share journey with actual PNG capture and deterministic failure controls.
// [Pos] Provider-free technical fixture; no accounts, models, database or normal services.
import {StrictMode, useState} from 'react';
import {createRoot} from 'react-dom/client';
import NoteShareDialog from '../../app/_dream/components/notes/NoteShareDialog';
import NoteContent from '../../app/_dream/components/notes/NoteContent';
import {projectNote} from '../../app/_dream/components/notes/noteShare';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';
import i18n from '../../app/_dream/i18n';
import '../../app/_dream/styles/tokens.css';
await i18n.changeLanguage('en');
await loadBrowserSession((async () => Response.json({user: {id: '42', email: 'fixture@example.com', display_name: null, avatar_url: null, role: 'user', created_at: null}, csrf_token: 'c'.repeat(43)})) as typeof fetch);
const source = projectNote({id: 'private-session', createdAt: '2026-11-12T09:00:00+08:00', cells: [{type: 'text', content: '河边的记录\n正文保留换行。'}, {type: 'widget', content: 'private chat'}, {type: 'writing-suggestion', content: 'private Agent suggestion'}, {type: 'text', content: '<script>window.bad=true</script> 😀'}]});
const facts = {saves: 0, failSave: false, copied: [] as string[], failCopy: false, empty: false, setNote: (id: string) => {void id;}};
export type NoteShareFixture = typeof facts;
(window as unknown as {noteShareFixture: NoteShareFixture}).noteShareFixture = facts;
Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async (text: string) => {if (facts.failCopy) throw Error('fixture clipboard'); facts.copied.push(text);}}});
export function Fixture() {
  const [open, setOpen] = useState(false), [id, setId] = useState(source.sessionId);
  facts.setNote = setId;
  const current = {...source, sessionId: id, snapshot: {...source.snapshot, paragraphs: facts.empty ? [] : source.snapshot.paragraphs}};
  return <main><button onClick={() => setOpen(true)}>Share current note</button><button onClick={() => void i18n.changeLanguage('zh')}>中文</button><NoteContent note={source.snapshot}/>{open && <NoteShareDialog key={id} source={current} save={async () => {facts.saves++; if (facts.failSave) throw Error('fixture save');}} onClose={() => setOpen(false)}/>}</main>;
}
createRoot(document.getElementById('root')!).render(<StrictMode><Fixture/></StrictMode>);
