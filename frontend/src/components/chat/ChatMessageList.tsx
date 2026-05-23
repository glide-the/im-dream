import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getToolName, isToolUIPart, type DynamicToolUIPart, type FileUIPart, type ToolUIPart, type UIMessage } from 'ai';
import type { UseChatHelpers } from '@ai-sdk/react';
import ToolMessagePart from './ToolMessagePart';
import FileMessagePart from './FileMessagePart';
import AssistMessagePart from './AssistMessagePart';

interface ChatMessageListProps {
  messages: UIMessage[];
  isLoading: boolean;
  error?: Error | null;
  addToolResult: (args: { tool: string; toolCallId: string; output: unknown }) => void;
  shouldShowLoadingIndicator?: boolean;
  readonly?: boolean;
  setMessages?: UseChatHelpers<UIMessage>['setMessages'];
  sendMessage?: UseChatHelpers<UIMessage>['sendMessage'];
}

type ToolStatus = 'executing' | 'completed' | 'error';

const TOOL_COMPLETED_STATES = new Set(['output-available', 'output-error']);
const REASONING_PREVIEW_LENGTH = 80;

function getToolStatus(part: ToolUIPart | DynamicToolUIPart, isLoading: boolean): ToolStatus {
  if (part.state === 'output-error') return 'error';
  if (TOOL_COMPLETED_STATES.has(part.state ?? '')) return 'completed';
  return isLoading ? 'executing' : 'completed';
}

function getToolOutputText(part: ToolUIPart | DynamicToolUIPart): string | null {
  if ('output' in part && part.output != null) return typeof part.output === 'string' ? part.output : JSON.stringify(part.output, null, 2);
  if ('error' in part && part.error != null) return typeof part.error === 'string' ? part.error : JSON.stringify(part.error, null, 2);
  return null;
}

function parseTerminalOutput(raw: string): { command: string | null; output: string; exitCode: string | null } {
  const lines = raw.split('\n');
  let command: string | null = null;
  let exitCode: string | null = null;
  const outputLines: string[] = [];

  lines.forEach((line) => {
    const commandMatch = line.match(/^\$\s+(.+)/);
    const exitMatch = line.match(/^Exit code:\s*(\d+)/i);
    if (commandMatch && !command) command = commandMatch[1];
    else if (exitMatch) exitCode = exitMatch[1];
    else outputLines.push(line);
  });

  return { command, output: outputLines.join('\n').trim(), exitCode };
}

function IconCopy() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ width: '1rem', height: '1rem' }}>
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

export default function ChatMessageList({ messages, isLoading, error, addToolResult, shouldShowLoadingIndicator = false, readonly = false, setMessages, sendMessage }: ChatMessageListProps) {
  const [expandedParts, setExpandedParts] = useState<Record<string, boolean>>({});
  const [copiedPartId, setCopiedPartId] = useState<string | null>(null);

  const handleCopy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedPartId(id);
      window.setTimeout(() => setCopiedPartId((current) => (current === id ? null : current)), 1800);
    } catch {
      setCopiedPartId(null);
    }
  };

  return (
    <div style={{ width: '100%', maxWidth: '48rem', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {messages.map((message, index) => {
        const isLastMessage = index === messages.length - 1;
        return (
          <div key={message.id} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {message.parts?.map((part, partIndex) => {
              const partKey = `${message.id}-${partIndex}`;
              const isExpanded = expandedParts[partKey] ?? false;
              const toggleExpanded = () => setExpandedParts((current) => ({ ...current, [partKey]: !isExpanded }));

              if (part.type === 'reasoning') {
                const reasoningText = (part as { text?: string }).text ?? '';
                return (
                  <div key={partKey} style={{ paddingLeft: '0.85rem', borderLeft: '2px solid var(--color-state-warning)' }}>
                    <button type="button" onClick={toggleExpanded} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', border: 'none', background: 'transparent', padding: 0, color: 'var(--color-text-muted)', fontSize: '0.85rem', fontStyle: 'italic', cursor: 'pointer' }}>
                      <span style={{ flex: 1, textAlign: 'left', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{reasoningText.slice(0, REASONING_PREVIEW_LENGTH) || 'Thinking…'}</span>
                      <span>{isExpanded ? '‹' : '›'}</span>
                    </button>
                    {isExpanded ? <div style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: 1.7, color: 'var(--color-text-secondary)' }}>{reasoningText}</div> : null}
                  </div>
                );
              }

              if (part.type === 'step-start') return null;

              if (part.type === 'text' && part.text) {
                const isUser = message.role === 'user';
                if (isUser) {
                  return (
                    <div key={partKey} style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <div style={{ maxWidth: '85%', borderRadius: '18px', padding: '0.9rem 1rem', background: 'var(--color-bg-surface)', boxShadow: '0 6px 18px var(--color-shadow-soft)' }}>
                        <div className="prose prose-chat" style={{ color: 'var(--color-text-primary)', fontSize: '0.92rem', lineHeight: 1.7 }}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{part.text}</ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  );
                }

                const isLastPart = partIndex === (message.parts?.length ?? 0) - 1;
                const previousMessage = index > 0 ? messages[index - 1] : undefined;
                return (
                  <div key={partKey} style={{ maxWidth: '48rem' }}>
                    <AssistMessagePart
                      part={part}
                      isLast={isLastMessage && isLastPart}
                      isLoading={isLoading}
                      message={message}
                      prevMessage={previousMessage}
                      showActions={isLastMessage ? isLastPart && !isLoading : isLastPart}
                      readonly={readonly}
                      setMessages={setMessages}
                      sendMessage={sendMessage}
                    />
                  </div>
                );
              }

              if (isToolUIPart(part)) {
                const toolPart = part as ToolUIPart | DynamicToolUIPart;
                const toolStatus = getToolStatus(toolPart, isLoading);
                const isCompleted = toolStatus !== 'executing';
                const isError = toolStatus === 'error';
                const outputText = getToolOutputText(toolPart);
                const title = 'title' in toolPart ? (toolPart as { title?: string }).title : undefined;
                const displayTitle = title || getToolName(toolPart);

                if (isCompleted && outputText) {
                  const { command, output, exitCode } = parseTerminalOutput(outputText);
                  const exitCodeNumber = exitCode != null ? Number(exitCode) : null;
                  return (
                    <div key={partKey} style={{ overflow: 'hidden', borderRadius: '12px', background: '#1a1a1a', color: '#f3eee6' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.65rem 1rem', fontSize: '0.75rem', color: '#b0b0b0' }}>
                        <span>‹ Terminal</span>
                        <button type="button" onClick={() => void handleCopy(partKey, outputText)} title="Copy" style={{ border: 'none', background: 'transparent', color: copiedPartId === partKey ? '#7bcf8f' : '#f3eee6', cursor: 'pointer' }}>{copiedPartId === partKey ? 'Copied!' : <IconCopy />}</button>
                      </div>
                      <div style={{ padding: '0 1rem 0.9rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.8rem', lineHeight: 1.65 }}>
                        {command ? <p style={{ margin: '0 0 0.45rem' }}><span style={{ color: '#f7c96a' }}>$</span> <span>{command}</span></p> : null}
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', maxHeight: '20rem', overflow: 'auto', color: '#c9c9c9' }}>{output || outputText}</pre>
                      </div>
                      {exitCodeNumber != null ? <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', padding: '0.55rem 1rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.75rem', color: exitCodeNumber === 0 ? '#7bcf8f' : '#ff7a70' }}>Exit code: {exitCode}</div> : null}
                      {isError && exitCodeNumber == null ? <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', padding: '0.55rem 1rem', fontSize: '0.75rem', color: '#ff7a70' }}>Error</div> : null}
                    </div>
                  );
                }

                return (
                  <div key={partKey} style={{ paddingLeft: '0.85rem', borderLeft: '2px solid var(--color-state-warning)' }}>
                    <button type="button" onClick={toggleExpanded} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.55rem', border: 'none', background: 'transparent', padding: 0, color: 'var(--color-text-secondary)', fontSize: '0.88rem', cursor: 'pointer' }}>
                      {toolStatus === 'executing' ? <span style={{ width: '0.7rem', height: '0.7rem', borderRadius: '999px', border: '2px solid var(--color-state-warning)', borderTopColor: 'transparent', display: 'inline-block' }} /> : null}
                      <span style={{ flex: 1, textAlign: 'left', fontStyle: 'italic', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{displayTitle}</span>
                      <span style={{ color: 'var(--color-text-muted)' }}>{isExpanded ? '‹' : '›'}</span>
                    </button>
                    {isExpanded ? <div style={{ marginTop: '0.6rem' }}><ToolMessagePart part={toolPart} isLast={isLastMessage} isLoading={isLoading} isManualToolInvocation={false} addToolResult={addToolResult} /></div> : null}
                  </div>
                );
              }

              if (part.type === 'file') {
                const isUser = message.role === 'user';
                return <div key={partKey} style={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}><div style={{ maxWidth: '80%' }}><FileMessagePart part={part as FileUIPart} isUserMessage={isUser} /></div></div>;
              }

              return null;
            })}
          </div>
        );
      })}

      {shouldShowLoadingIndicator ? <div style={{ alignSelf: 'flex-start', borderRadius: '12px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', padding: '0.8rem 0.95rem', color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>Thinking…</div> : null}
      {error ? <div style={{ alignSelf: 'flex-start', maxWidth: '80%', borderRadius: '18px', padding: '0.8rem 0.95rem', background: 'rgba(244,67,54,0.12)', color: 'var(--color-state-error)', fontSize: '0.85rem' }}>Error: {error.message}</div> : null}
    </div>
  );
}
