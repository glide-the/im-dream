// [Input] User-authored text message part from the chat message stream/history and an optional leading action.
// [Output] Right-aligned user chat bubble with an anchored provenance action, GFM Markdown and copy.
// [Pos] user-message-part component node in frontend/app/_dream/components/chat
// [Sync] 2026-06-02: created to render user prompt text as Markdown in ChatMessageList.
// [Sync] 2026-07-20: Markdown rendering delegated to shared ChatMarkdown so user messages
//                    render ```mermaid blocks through the same chain as assistant messages.
// [Sync] 2026-07-26: add bottom-right copy button under the bubble via shared useCopy hook
//                    and shared IconCopy/IconCheck, matching the assistant action style.
// [Sync] 2026-08-22: accept the owning Chat Thread for explicit workspace:// rendering.
// [Sync] 2026-09-01: render a lightweight source label for persisted Dream auto-repair messages.
// [Sync] 2026-09-27: anchor a created Thread's source navigation above its first user bubble.
import { memo, type ReactNode } from 'react';
import { useCopy } from '../../hooks/useCopy';
import { IconCheck, IconCopy } from './Icons';
import ChatMarkdown from './ChatMarkdown';

interface UserMessagePartProps {
  text: string;
  workspaceSessionId?: string;
  sourceLabel?: string;
  leadingAction?: ReactNode;
}

export default memo(function UserMessagePart({ text, workspaceSessionId, sourceLabel, leadingAction }: UserMessagePartProps) {
  const { copied, copy } = useCopy();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
      {leadingAction}
      {sourceLabel ? (
        <span
          style={{
            paddingRight: '0.35rem',
            color: 'var(--color-text-muted)',
            fontSize: '0.72rem',
            lineHeight: 1.4,
          }}
        >
          {sourceLabel}
        </span>
      ) : null}
      <div
        style={{
          maxWidth: '85%',
          minWidth: 0,
          overflowWrap: 'anywhere',
          borderRadius: '18px',
          padding: '0.9rem 1rem',
          background: 'var(--color-bg-paper)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        }}
      >
        <div className="prose prose-chat" style={{ color: 'var(--color-text-primary)', fontSize: '0.92rem', lineHeight: 1.7 }}>
          <ChatMarkdown text={text} workspaceSessionId={workspaceSessionId} />
        </div>
      </div>
      <button
        type="button"
        title="Copy"
        onClick={() => copy(text)}
        style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '1.9rem', height: '1.9rem', borderRadius: '0.5rem', border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer' }}
      >
        {copied ? <IconCheck style={{ width: '0.95rem', height: '0.95rem' }} /> : <IconCopy style={{ width: '0.95rem', height: '0.95rem' }} />}
      </button>
    </div>
  );
});
