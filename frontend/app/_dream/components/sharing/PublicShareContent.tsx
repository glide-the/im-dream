// [Sync] 2026-11-13: reuse Chat message parts and the original message-surface padding.
'use client';
// [Input] Immutable, text-only public snapshot from the server's current active-state read.
// [Output] Read-only notes and the same user/assistant message presentation as Chat.
// [Pos] Anonymous content leaf; no account/provider/workspace owner is mounted.
import {useEffect} from 'react';
import '../../i18n';
import type {PublicShareSnapshot} from '../../api/publicShareSchema';
import NoteContent from '../notes/NoteContent';
import UserMessagePart from '../chat/UserMessagePart';
import AssistMessagePart from '../chat/AssistMessagePart';
import {CHAT_MESSAGE_LIST_STYLE, CHAT_MESSAGE_GROUP_STYLE} from '../chat/chatMessageLayout';
import {BRAND_NAME} from '../../constants/brand';
import {initTheme} from '../../utils/theme';
export default function PublicShareContent({snapshot}: {snapshot: PublicShareSnapshot}) {
  useEffect(() => {initTheme();}, []);
  if (snapshot.kind === 'note') return <NoteContent note={snapshot}/>;
  return <article style={{maxWidth: 880, margin: '0 auto', boxSizing: 'border-box', padding: '1rem 1rem 1.5rem', color: 'var(--color-text-primary)', overflowWrap: 'anywhere'}}>
    <header style={{marginBottom: '1.25rem'}}><p>{BRAND_NAME}</p><h1>{snapshot.title}</h1>{snapshot.created_at ? <time dateTime={snapshot.created_at}>{snapshot.created_at.slice(0, 10)}</time> : null}</header>
    <div style={CHAT_MESSAGE_LIST_STYLE}>
      {snapshot.messages.map((message, index) => (
        <div key={index} style={CHAT_MESSAGE_GROUP_STYLE}>
          {message.role === 'user' ? (
            <UserMessagePart text={message.content} publicView/>
          ) : (
            <AssistMessagePart
              part={{type: 'text', text: message.content}}
              message={{id: String(index), role: 'assistant', parts: [{type: 'text', text: message.content}]}}
              showActions
              readonly
              publicView
            />
          )}
        </div>
      ))}
    </div>
  </article>;
}
