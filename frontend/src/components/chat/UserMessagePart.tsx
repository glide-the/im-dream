// [Input] User-authored text message part from the chat message stream/history.
// [Output] Right-aligned user chat bubble with GFM Markdown rendering.
// [Pos] user-message-part component node in frontend/src/components/chat
// [Sync] 2026-06-02: created to render user prompt text as Markdown in ChatMessageList.
// [Sync] 2026-07-20: Markdown rendering delegated to shared ChatMarkdown so user messages
//                    render ```mermaid blocks through the same chain as assistant messages.
import { memo } from 'react';
import ChatMarkdown from './ChatMarkdown';

interface UserMessagePartProps {
  text: string;
}

export default memo(function UserMessagePart({ text }: UserMessagePartProps) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
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
          <ChatMarkdown text={text} />
        </div>
      </div>
    </div>
  );
});
