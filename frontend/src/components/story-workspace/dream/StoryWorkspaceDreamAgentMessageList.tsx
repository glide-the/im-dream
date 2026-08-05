// [Input] Server-allowlisted Dream Agent messages and transient safe content.
// [Output] Ordered text and collapsed activity entries for Dream-owned surfaces.
// [Pos] Shared Dream-only message renderer; it never consumes generic Chat parts.

import ChatMarkdown from '../../chat/ChatMarkdown';
import type {
  StoryWorkspaceDreamAgentContent,
  StoryWorkspaceDreamAgentMessage,
} from '../../../hooks/story-workspace/contracts';
import './StoryWorkspaceDreamAgentMessageList.css';

const STORY_WORKSPACE_DREAM_ACTIVITY_PRESENTATION = {
  running: { icon: '◌', label: '进行中' },
  completed: { icon: '✓', label: '已完成' },
  stopped: { icon: '◇', label: '已停止' },
} as const;

export interface StoryWorkspaceDreamAgentMessageListProps {
  readonly messages: readonly StoryWorkspaceDreamAgentMessage[];
  readonly streamContent: readonly StoryWorkspaceDreamAgentContent[];
  readonly streamText: string;
}

function StoryWorkspaceDreamAgentContentList({
  content,
  idPrefix,
}: {
  readonly content: readonly StoryWorkspaceDreamAgentContent[];
  readonly idPrefix: string;
}) {
  return (
    <div className="story-workspace-dream-agent-message-list__content">
      {content.map((part, index) => {
        if (part.kind === 'text') {
          return (
            <div className="story-workspace-dream-agent-message-list__text" key={`${idPrefix}-text-${index}`}>
              <ChatMarkdown text={`${part.text}${part.truncated ? '…' : ''}`} />
            </div>
          );
        }
        const presentation = STORY_WORKSPACE_DREAM_ACTIVITY_PRESENTATION[part.status];
        return (
          <details className="story-workspace-dream-agent-message-list__activity" key={part.id}>
            <summary>
              <span aria-hidden="true">{presentation.icon}</span>
              <span>{part.label}</span>
              <small>{presentation.label}</small>
            </summary>
            <p>仅展示 Dream Agent 的安全过程摘要。</p>
          </details>
        );
      })}
    </div>
  );
}

export function StoryWorkspaceDreamAgentMessageList({
  messages,
  streamContent,
  streamText,
}: StoryWorkspaceDreamAgentMessageListProps) {
  const visibleStreamContent: readonly StoryWorkspaceDreamAgentContent[] = streamContent.length > 0
    ? streamContent
    : streamText
      ? [{ kind: 'text', text: streamText, truncated: false }]
      : [];

  if (messages.length === 0 && visibleStreamContent.length === 0) {
    return (
      <p className="story-workspace-dream-agent-message-list__empty">
        正在准备可展示的 Dream Agent 消息。
      </p>
    );
  }

  return (
    <div className="story-workspace-dream-agent-message-list">
      {messages.map((message) => (
        <article
          className={`story-workspace-dream-agent-message-list__message story-workspace-dream-agent-message-list__message--${message.role}`}
          key={message.id}
        >
          <small>{message.role === 'assistant' ? 'Dream Agent' : '你'}</small>
          <StoryWorkspaceDreamAgentContentList content={message.content} idPrefix={message.id} />
        </article>
      ))}
      {visibleStreamContent.length > 0 && (
        <article className="story-workspace-dream-agent-message-list__message story-workspace-dream-agent-message-list__message--assistant story-workspace-dream-agent-message-list__message--streaming">
          <small>Dream Agent 正在输出</small>
          <StoryWorkspaceDreamAgentContentList content={visibleStreamContent} idPrefix="stream" />
        </article>
      )}
    </div>
  );
}
