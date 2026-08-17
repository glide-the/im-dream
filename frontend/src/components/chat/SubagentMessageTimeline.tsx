// [Input] Normalized readonly SubAgent messages from useThreadSubagents.
// [Output] Conversation-first task timeline reusing Chat user/assistant Markdown renderers.
// [Pos] Shared readonly message surface for SubagentPanel task details.
// [Sync] 2026-08-05: initial conversation timeline with paired tool events and legacy/status notices.

import { useState } from 'react';
import type { UIMessage } from 'ai';
import { useTranslation } from 'react-i18next';
import { getDateLocale } from '../../i18n';
import type { ThreadSubagentMessage, ThreadSubagentStatus } from '../../hooks/useThreadSubagents';
import AssistMessagePart from './AssistMessagePart';
import UserMessagePart from './UserMessagePart';

interface SubagentMessageTimelineProps {
  messages: ThreadSubagentMessage[];
  taskStatus: ThreadSubagentStatus;
  legacy: boolean;
  truncated: boolean;
}

interface PairedToolMessage {
  call: ThreadSubagentMessage;
  result: ThreadSubagentMessage | null;
}

function parseToolSummary(value: string | null): unknown {
  if (!value) return null;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return value;
  }
}

function pairSubagentToolMessages(messages: ThreadSubagentMessage[]): Map<string, ThreadSubagentMessage> {
  const results = new Map<string, ThreadSubagentMessage>();
  for (const message of messages) {
    if (message.kind === 'tool_result' && message.toolCallId) results.set(message.toolCallId, message);
  }
  return results;
}

function formatTimestamp(value: string | null, language: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat(getDateLocale(language), {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function MessageMeta({ label, timestamp }: { label: string; timestamp: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', marginBottom: '0.4rem', color: 'var(--color-text-muted)', fontSize: '0.72rem', lineHeight: 1.4 }}>
      <span style={{ fontWeight: 650 }}>{label}</span>
      {timestamp ? <time style={{ fontVariantNumeric: 'tabular-nums' }}>{timestamp}</time> : null}
    </div>
  );
}

function ToolEvent({ tool }: { tool: PairedToolMessage }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const result = tool.result;
  const failed = result?.status === 'failed';
  const status = result?.status ?? tool.call.status ?? 'started';
  const input = parseToolSummary(tool.call.input);
  const output = parseToolSummary(result?.output ?? null);
  const contentId = `subagent-tool-${tool.call.id}`;

  return (
    <section style={{ borderLeft: `2px solid ${failed ? 'var(--color-state-error)' : 'var(--color-action-link)'}`, paddingLeft: '0.85rem' }}>
      <button
        type="button"
        aria-expanded={expanded}
        aria-controls={contentId}
        onClick={() => setExpanded((value) => !value)}
        style={{ width: '100%', minHeight: '2.75rem', display: 'flex', alignItems: 'center', gap: '0.55rem', border: 'none', background: 'transparent', padding: 0, color: 'var(--color-text-secondary)', cursor: 'pointer', textAlign: 'left' }}
      >
        <span aria-hidden="true" style={{ width: '0.52rem', height: '0.52rem', flexShrink: 0, borderRadius: '999px', background: failed ? 'var(--color-state-error)' : status === 'started' ? 'var(--color-action-link)' : 'var(--color-state-success)' }} />
        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.84rem', fontWeight: 600 }}>
          {t('chat.subagents.timeline.toolUsed', { tool: tool.call.toolName || t('chat.subagents.toolFallback') })}
        </span>
        <span style={{ flexShrink: 0, fontSize: '0.72rem', color: failed ? 'var(--color-state-error)' : 'var(--color-text-muted)' }}>
          {t(`chat.subagents.activityStatus.${status}`, { defaultValue: status })}
        </span>
        <span aria-hidden="true" style={{ flexShrink: 0, color: 'var(--color-text-muted)' }}>{expanded ? '⌄' : '›'}</span>
      </button>
      {expanded ? (
        <div id={contentId} style={{ display: 'grid', gap: '0.65rem', padding: '0.25rem 0 0.65rem' }}>
          {input != null ? (
            <div style={{ borderRadius: '0.65rem', background: 'var(--color-bg-surface)', padding: '0.7rem 0.8rem' }}>
              <div style={{ marginBottom: '0.35rem', color: 'var(--color-text-muted)', fontSize: '0.7rem', fontWeight: 650 }}>{t('chat.subagents.timeline.toolInput')}</div>
              <pre style={{ margin: 0, overflowX: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', color: 'var(--color-text-secondary)', fontSize: '0.74rem', lineHeight: 1.55 }}>{typeof input === 'string' ? input : JSON.stringify(input, null, 2)}</pre>
            </div>
          ) : null}
          {output != null ? (
            <div style={{ borderRadius: '0.65rem', background: 'var(--color-bg-surface)', padding: '0.7rem 0.8rem' }}>
              <div style={{ marginBottom: '0.35rem', color: failed ? 'var(--color-state-error)' : 'var(--color-text-muted)', fontSize: '0.7rem', fontWeight: 650 }}>{failed ? t('chat.subagents.errorTitle') : t('chat.subagents.timeline.toolOutput')}</div>
              <pre style={{ margin: 0, overflowX: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', color: failed ? 'var(--color-state-error)' : 'var(--color-text-secondary)', fontSize: '0.74rem', lineHeight: 1.55 }}>{typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</pre>
            </div>
          ) : null}
          {tool.call.redacted || result?.redacted ? <div style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>{t('chat.subagents.timeline.redacted')}</div> : null}
          {tool.call.truncated || result?.truncated ? <div style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>{t('chat.subagents.timeline.truncated')}</div> : null}
        </div>
      ) : null}
    </section>
  );
}

function StatusMessage({ message }: { message: ThreadSubagentMessage }) {
  const { t, i18n } = useTranslation();
  const failed = message.status === 'failed';
  const cancelled = message.status === 'cancelled';
  const color = failed ? 'var(--color-state-error)' : cancelled ? 'var(--color-text-muted)' : message.status === 'completed' ? 'var(--color-state-success)' : 'var(--color-action-link)';
  return (
    <div role="status" style={{ display: 'flex', alignItems: 'flex-start', gap: '0.55rem', padding: '0.3rem 0', color, fontSize: '0.8rem', lineHeight: 1.55 }}>
      <span aria-hidden="true" style={{ width: '0.48rem', height: '0.48rem', marginTop: '0.35rem', borderRadius: '999px', background: 'currentColor', flexShrink: 0 }} />
      <span style={{ flex: 1 }}>
        {t(`chat.subagents.status.${message.status}`, { defaultValue: message.status ?? t('chat.subagents.timeline.statusUpdate') })}
        {message.text ? <span style={{ display: 'block', marginTop: '0.2rem', color: 'var(--color-text-secondary)' }}>{message.text}</span> : null}
      </span>
      <time style={{ flexShrink: 0, color: 'var(--color-text-muted)', fontSize: '0.7rem', fontVariantNumeric: 'tabular-nums' }}>{formatTimestamp(message.timestamp, i18n.language)}</time>
    </div>
  );
}

export default function SubagentMessageTimeline({ messages, taskStatus, legacy, truncated }: SubagentMessageTimelineProps) {
  const { t, i18n } = useTranslation();
  const toolResults = pairSubagentToolMessages(messages);
  const consumedResults = new Set<string>();

  if (messages.length === 0) {
    return <div style={{ padding: '1.25rem 0', color: 'var(--color-text-muted)', fontSize: '0.84rem' }}>{t('chat.subagents.timeline.empty')}</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem', minWidth: 0 }}>
      {legacy ? <div style={{ borderRadius: '0.65rem', background: 'var(--color-bg-surface)', padding: '0.65rem 0.75rem', color: 'var(--color-text-muted)', fontSize: '0.76rem', lineHeight: 1.55 }}>{t('chat.subagents.timeline.legacy')}</div> : null}
      {truncated ? <div style={{ borderRadius: '0.65rem', background: 'var(--color-bg-surface)', padding: '0.65rem 0.75rem', color: 'var(--color-text-muted)', fontSize: '0.76rem', lineHeight: 1.55 }}>{t('chat.subagents.timeline.projectionTruncated')}</div> : null}
      {messages.map((message, index) => {
        const timestamp = formatTimestamp(message.timestamp, i18n.language);
        if (message.kind === 'tool_result' && message.toolCallId && consumedResults.has(message.toolCallId)) return null;
        if (message.kind === 'tool_call') {
          const result = message.toolCallId ? toolResults.get(message.toolCallId) ?? null : null;
          if (message.toolCallId && result) consumedResults.add(message.toolCallId);
          return <ToolEvent key={message.id} tool={{ call: message, result }} />;
        }
        if (message.kind === 'tool_result') return <ToolEvent key={message.id} tool={{ call: { ...message, kind: 'tool_call', input: null }, result: message }} />;
        if (message.kind === 'status') return <StatusMessage key={message.id} message={message} />;
        if (message.kind === 'system') {
          return <div key={message.id} style={{ borderRadius: '0.65rem', background: 'var(--color-bg-surface)', padding: '0.65rem 0.75rem', color: 'var(--color-text-muted)', fontSize: '0.76rem' }}>{t('chat.subagents.timeline.unknownEvent', { event: message.text || t('chat.subagents.unknown') })}</div>;
        }
        if (!message.text) return null;
        if (message.kind === 'task') {
          return (
            <section key={message.id}>
              <MessageMeta label={t('chat.subagents.timeline.taskDispatch')} timestamp={timestamp} />
              <UserMessagePart text={message.text} />
            </section>
          );
        }
        const uiMessage = { id: message.id, role: 'assistant', parts: [{ type: 'text', text: message.text }] } as UIMessage;
        return (
          <section key={message.id}>
            <MessageMeta label={message.kind === 'final' ? t('chat.subagents.timeline.finalReply') : t('chat.subagents.timeline.agentUpdate')} timestamp={timestamp} />
            <AssistMessagePart part={{ type: 'text', text: message.text }} message={uiMessage} prevMessage={undefined} isLast={index === messages.length - 1} isLoading={taskStatus === 'running'} showActions readonly />
          </section>
        );
      })}
    </div>
  );
}
