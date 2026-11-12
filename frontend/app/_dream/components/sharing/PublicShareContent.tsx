'use client';
// [Input] Immutable, text-only public snapshot from the server's current active-state read.
// [Output] Read-only note or AI conversation using the original prose/Markdown/math presenters.
// [Pos] Anonymous content leaf; no account/provider/workspace owner is mounted.
import {useEffect} from 'react';
import '../../i18n';
import type {PublicShareSnapshot} from '../../api/publicShareSchema';
import NoteContent from '../notes/NoteContent';
import ChatMarkdown from '../chat/ChatMarkdown';
import {BRAND_NAME} from '../../constants/brand';
import {initTheme} from '../../utils/theme';
export default function PublicShareContent({snapshot}: {snapshot: PublicShareSnapshot}) {
  useEffect(() => {initTheme();}, []);
  if (snapshot.kind === 'note') return <NoteContent note={snapshot}/>;
  return <article style={{maxWidth: 880, margin: '0 auto', padding: 'clamp(20px, 5vw, 48px)', color: 'var(--color-text-primary)', overflowWrap: 'anywhere'}}>
    <header><p>{BRAND_NAME}</p><h1>{snapshot.title}</h1>{snapshot.created_at ? <time dateTime={snapshot.created_at}>{snapshot.created_at.slice(0, 10)}</time> : null}</header>
    {snapshot.messages.map((message, index) => <section key={index} style={{padding: '24px 0', borderBottom: '1px dashed var(--color-border-paper)'}}>
      <p style={{fontSize: 13, color: 'var(--color-text-muted)'}}>{message.role === 'user' ? 'You · 用户' : 'AI'}</p>
      <ChatMarkdown text={message.content} publicView/>
    </section>)}
  </article>;
}
