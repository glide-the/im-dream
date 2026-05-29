// [Input] UIMessage[] from useChat; ToolMessagePart, AssistMessagePart, FileMessagePart sub-components.
// [Output] Scrollable chat message list with tool, text, reasoning, and file part rendering.
// [Pos] chat-message-list component node in frontend/src/components/chat
// [Sync] 2026-05-27: add threadId prop; propagate to ToolMessagePart; render AskUserQuestion tool parts directly (not collapsed) so the question form is immediately visible.
// [Sync] 2026-05-27: add toolChoice prop; render non-completed tool parts in manual mode directly with isManualToolInvocation=true so Approve/Cancel UI is shown.
// [Sync] 2026-05-29: import isEditorWriteTool; render editor write tool parts directly (not collapsed) with isManualToolInvocation=true so specialized approval UI shows immediately.
// [Sync] 2026-05-29: render completed editor write tool parts as EditorWriteCompletedCard instead of Terminal card.
// [Sync] 2026-05-29: add onEditorWriteConfirmed prop; forward to ToolMessagePart for editor write tools.
// [Sync] 2026-05-29: let the message list fill the available chat page width.
// [Sync] 2026-05-29: fix history-replay regression — history-loaded DynamicToolUIPart may lack toolName field causing getToolName() to return 'invocation'; add resolveToolName() with direct field fallback and hoist editor write completed check above Terminal block, decoupled from outputText.
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getToolName, isToolUIPart, type DynamicToolUIPart, type FileUIPart, type ToolUIPart, type UIMessage } from 'ai';
import type { UseChatHelpers } from '@ai-sdk/react';
import FileMessagePart from './FileMessagePart';
import AssistMessagePart from './AssistMessagePart';
import ToolMessagePart from './ToolMessagePart';
import { isEditorWriteTool, EditorWriteCompletedCard, type EditorWriteOutput } from './EditorWriteApprovalUI';

interface ChatMessageListProps {
  messages: UIMessage[];
  threadId: string;
  isLoading: boolean;
  error?: Error | null;
  addToolResult: (args: { tool: string; toolCallId: string; output: unknown }) => void;
  shouldShowLoadingIndicator?: boolean;
  readonly?: boolean;
  toolChoice?: string;
  setMessages?: UseChatHelpers<UIMessage>['setMessages'];
  sendMessage?: UseChatHelpers<UIMessage>['sendMessage'];
  /** Forwarded to ToolMessagePart for editor write tools — triggers Writing view reload. */
  onEditorWriteConfirmed?: () => void;
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

const ASK_USER_TOOL_NAMES = new Set(['askuserquestion', 'ask_user_question', 'ask_user', 'askuser']);

function isAskUserQuestionTool(part: ToolUIPart | DynamicToolUIPart): boolean {
  const name = getToolName(part).toLowerCase();
  return ASK_USER_TOOL_NAMES.has(name) || name.endsWith('__ask_user') || name.endsWith('__askuserquestion');
}

/**
 * Robustly resolve the tool name from a part.
 *
 * History-loaded DynamicToolUIPart objects can lose their `toolName` field after
 * DB serialization. When that happens, the AI SDK's `getToolName()` falls back to
 * stripping the 'tool-' prefix from `type`, yielding 'invocation' instead of the
 * real tool name. This helper retries with a direct field read so that
 * `isEditorWriteTool` works correctly for both live-stream and history-replay paths.
 */
function resolveToolName(part: ToolUIPart | DynamicToolUIPart): string {
  try {
    const name = getToolName(part);
    if (name && name !== 'invocation') return name;
  } catch {
    // getToolName may throw if the part has an unexpected structure
  }
  const raw = part as unknown as Record<string, unknown>;
  if (typeof raw.toolName === 'string' && raw.toolName) return raw.toolName;
  return '';
}

export default function ChatMessageList({ messages, threadId, isLoading, error, addToolResult, shouldShowLoadingIndicator = false, readonly = false, toolChoice, setMessages, sendMessage, onEditorWriteConfirmed }: ChatMessageListProps) {
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
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
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
                  <div key={partKey} style={{ paddingLeft: '0.85rem', borderLeft: '2px solid var(--color-action-link)' }}>
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
                      <div style={{ maxWidth: '85%', borderRadius: '18px', padding: '0.9rem 1rem', background: 'var(--color-bg-paper)', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
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
                  <div key={partKey} style={{ width: '100%' }}>
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
                const toolName = resolveToolName(toolPart);
                const displayTitle = title || toolName || getToolName(toolPart);

                // Editor write tools always render as EditorWriteCompletedCard when
                // completed — this check is independent of outputText so that history-
                // replay parts (which may lack output after DB serialization) still get
                // the correct UI instead of falling through to the Terminal block.
                if (isCompleted && isEditorWriteTool(toolName)) {
                  const rawInput = 'input' in toolPart ? (toolPart as { input?: unknown }).input : undefined;
                  const rawOutput = 'output' in toolPart ? (toolPart as { output?: unknown }).output : undefined;
                  return (
                    <div key={partKey}>
                      <EditorWriteCompletedCard
                        toolName={toolName}
                        input={(rawInput ?? {}) as Record<string, unknown>}
                        output={(rawOutput ?? {}) as EditorWriteOutput}
                      />
                    </div>
                  );
                }

                if (isCompleted && outputText) {
                  const { command, output, exitCode } = parseTerminalOutput(outputText);
                  const exitCodeNumber = exitCode != null ? Number(exitCode) : null;
                  return (
                    <div key={partKey} style={{ overflow: 'hidden', borderRadius: '12px', background: '#1a1a1a', color: '#f3eee6' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.65rem 1rem', fontSize: '0.75rem', color: '#b0b0b0' }}>
                        <span>‹ Terminal</span>
                        <button type="button" onClick={() => void handleCopy(partKey, outputText)} title="Copy" style={{ border: 'none', background: 'transparent', color: copiedPartId === partKey ? '#22c55e' : '#f3eee6', cursor: 'pointer' }}>{copiedPartId === partKey ? 'Copied!' : <IconCopy />}</button>
                      </div>
                      <div style={{ padding: '0 1rem 0.9rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.8rem', lineHeight: 1.65 }}>
                        {command ? <p style={{ margin: '0 0 0.45rem' }}><span style={{ color: 'var(--color-action-link)' }}>$</span> <span>{command}</span></p> : null}
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', maxHeight: '20rem', overflow: 'auto', color: '#c9c9c9' }}>{output || outputText}</pre>
                      </div>
                      {exitCodeNumber != null ? <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', padding: '0.55rem 1rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.75rem', color: exitCodeNumber === 0 ? '#22c55e' : '#d9534f' }}>Exit code: {exitCode}</div> : null}
                      {isError && exitCodeNumber == null ? <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', padding: '0.55rem 1rem', fontSize: '0.75rem', color: '#d9534f' }}>Error</div> : null}
                    </div>
                  );
                }

                // AskUserQuestion tools that are waiting for user input are rendered
                // directly (not collapsed) so the question form is immediately visible.
                const needsUserInput = isAskUserQuestionTool(toolPart) && !isCompleted;
                if (needsUserInput) {
                  return (
                    <div key={partKey}>
                      <ToolMessagePart part={toolPart} threadId={threadId} isLast={isLastMessage} isLoading={isLoading} isManualToolInvocation={false} addToolResult={addToolResult} />
                    </div>
                  );
                }

                // Editor write tools (write_segment, delete_segment, insert_widget,
                // reply_to_comment) are always-confirm tools — render directly with
                // isManualToolInvocation=true so the specialized approval UI shows immediately.
                const needsEditorWriteApproval = isEditorWriteTool(toolName) && !isCompleted;
                if (needsEditorWriteApproval) {
                  return (
                    <div key={partKey}>
                      <ToolMessagePart part={toolPart} threadId={threadId} isLast={isLastMessage} isLoading={isLoading} isManualToolInvocation={true} addToolResult={addToolResult} onEditorWriteConfirmed={onEditorWriteConfirmed} />
                    </div>
                  );
                }

                // In manual mode, non-completed tool calls are waiting for user
                // approval — render them directly (not collapsed) with the
                // Approve/Cancel UI visible immediately.
                const needsManualApproval = toolChoice === 'manual' && !isCompleted;
                if (needsManualApproval) {
                  return (
                    <div key={partKey}>
                      <ToolMessagePart part={toolPart} threadId={threadId} isLast={isLastMessage} isLoading={isLoading} isManualToolInvocation={true} addToolResult={addToolResult} />
                    </div>
                  );
                }

                return (
                  <div key={partKey} style={{ paddingLeft: '0.85rem', borderLeft: '2px solid var(--color-action-link)' }}>
                    <button type="button" onClick={toggleExpanded} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.55rem', border: 'none', background: 'transparent', padding: 0, color: 'var(--color-text-secondary)', fontSize: '0.88rem', cursor: 'pointer' }}>
                      {toolStatus === 'executing' ? <span style={{ width: '0.7rem', height: '0.7rem', borderRadius: '999px', border: '2px solid var(--color-action-link)', borderTopColor: 'transparent', display: 'inline-block' }} /> : null}
                      <span style={{ flex: 1, textAlign: 'left', fontStyle: 'italic', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{displayTitle}</span>
                      <span style={{ color: 'var(--color-text-muted)' }}>{isExpanded ? '‹' : '›'}</span>
                    </button>
                    {isExpanded ? <div style={{ marginTop: '0.6rem' }}><ToolMessagePart part={toolPart} threadId={threadId} isLast={isLastMessage} isLoading={isLoading} isManualToolInvocation={false} addToolResult={addToolResult} /></div> : null}
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

      {shouldShowLoadingIndicator ? <div style={{ alignSelf: 'flex-start', borderRadius: '12px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '0.8rem 0.95rem', color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>Thinking…</div> : null}
      {error ? <div style={{ alignSelf: 'flex-start', maxWidth: '80%', borderRadius: '18px', padding: '0.8rem 0.95rem', background: 'rgba(217,83,79,0.1)', color: '#d9534f', fontSize: '0.85rem' }}>Error: {error.message}</div> : null}
    </div>
  );
}
