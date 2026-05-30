// [Input] AskUserQuestionUI, EditorWriteApprovalUI, Icons, AuthContext token; part shape from @ai-sdk/react DynamicToolUIPart/ToolUIPart.
// [Output] Rendered tool invocation card with inline AskUserQuestion form, EditorWriteApproval UI, or generic Approve/Reject UI.
// [Pos] tool-message-part component node in frontend/src/components/chat
// [Sync] 2026-05-27: add threadId prop; fix confirmToolCall body to send thread_id+tool_call_id (snake_case) matching ToolConfirmRequestBody; accept ok|success response flag.
// [Sync] 2026-05-27: when shouldShowAskUserUI is true, render only AskUserQuestionUI (no collapsible header) for clean UX.
// [Sync] 2026-05-27: add !isCompleted guard to shouldShowApprovalUI so Approve/Cancel disappears after tool completes in manual mode.
// [Sync] 2026-05-29: integrate EditorWriteApprovalUI for mcp__editor__ write tools; detect by isEditorWriteTool().
// [Sync] 2026-05-29: add onEditorWriteConfirmed prop; call after successful editor write approve to trigger Writing view reload.
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getToolName, type DynamicToolUIPart, type ToolUIPart } from 'ai';
import AskUserQuestionUI, { type AskUserQuestionInput } from './AskUserQuestionUI';
import EditorWriteApprovalUI, { isEditorWriteTool } from './EditorWriteApprovalUI';
import { IconCheck, IconChevronDown, IconChevronUp, IconLoader, IconX } from './Icons';
import { getAuthToken } from '../../contexts/AuthContext';

const API_BASE = '/ink-and-memory';

type AnyToolUIPart = ToolUIPart | DynamicToolUIPart;

function IconTool() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ width: '0.95rem', height: '0.95rem' }}>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function IconAlert() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ width: '0.95rem', height: '0.95rem' }}>
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

async function confirmToolCall(
  threadId: string,
  toolCallId: string,
  approved: boolean,
  reason?: string,
  answers?: Record<string, unknown>,
) {
  const response = await fetch(`${API_BASE}/api/claude-agent/tool-confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getAuthToken()}` },
    body: JSON.stringify({ thread_id: threadId, tool_call_id: toolCallId, approved, reason, answers }),
  });
  return (await response.json()) as { ok?: boolean; success?: boolean; message?: string };
}

interface ToolMessagePartProps {
  part: AnyToolUIPart;
  threadId: string;
  isLast?: boolean;
  isLoading?: boolean;
  isManualToolInvocation?: boolean;
  addToolResult?: (params: { tool: string; toolCallId: string; output: unknown }) => void;
  /** Called after an editor write tool is successfully confirmed so the Writing view can reload. */
  onEditorWriteConfirmed?: () => void;
}

export function ToolMessagePart({ part, threadId, isLast, isLoading, isManualToolInvocation, addToolResult, onEditorWriteConfirmed }: ToolMessagePartProps) {
  const [expanded, setExpanded] = useState(false);
  const [confirmationStatus, setConfirmationStatus] = useState<'idle' | 'confirming' | 'confirmed' | 'rejected'>('idle');
  const toolCallId = part.toolCallId;
  const toolName = getToolName(part);
  const input = 'input' in part ? part.input : undefined;
  const output = 'output' in part ? part.output : undefined;
  const state = part.state;
  const title = 'title' in part ? (part as { title?: string }).title : undefined;
  const providerExecuted = 'providerExecuted' in part ? (part as { providerExecuted?: boolean }).providerExecuted : undefined;
  const partType = part.type;

  const isCompleted = useMemo(() => state === 'output-available' || state === 'output-error', [state]);
  const isExecuting = useMemo(() => !isCompleted && Boolean(isLast && isLoading), [isCompleted, isLast, isLoading]);
  const isError = useMemo(() => state === 'output-error', [state]);
  const isAskUserQuestion = useMemo(() => {
    const normalizedType = partType?.toLowerCase() || '';
    const normalizedName = toolName?.toLowerCase() || '';
    return normalizedType === 'tool-askuserquestion' || ['askuserquestion', 'ask_user_question', 'ask_user', 'askuser'].includes(normalizedName) || normalizedName.endsWith('__ask_user') || normalizedName.endsWith('__askuserquestion');
  }, [partType, toolName]);
  const shouldShowAskUserUI = useMemo(() => isAskUserQuestion && !isCompleted && (state === 'input-available' || state === 'approval-requested' || !state || state === 'input-streaming'), [isAskUserQuestion, isCompleted, state]);
  const isEditorWrite = useMemo(() => isEditorWriteTool(toolName), [toolName]);
  const shouldShowEditorWriteUI = useMemo(() => isEditorWrite && !isCompleted && (state === 'input-available' || state === 'approval-requested' || !state || state === 'input-streaming'), [isEditorWrite, isCompleted, state]);
  // Only show Approve/Cancel while the tool is still pending — once the output
  // arrives (isCompleted) the card transitions to the normal completed view.
  const shouldShowApprovalUI = Boolean(isManualToolInvocation) && !shouldShowAskUserUI && !shouldShowEditorWriteUI && !isCompleted;

  const inputDisplay = useMemo(() => {
    try { return JSON.stringify(input, null, 2); } catch { return String(input); }
  }, [input]);
  const outputDisplay = useMemo(() => {
    if (output == null) return null;
    try { return JSON.stringify(output, null, 2); } catch { return String(output); }
  }, [output]);

  const handleApprove = useCallback(async () => {
    if (confirmationStatus !== 'idle') return;
    setConfirmationStatus('confirming');
    try {
      const result = await confirmToolCall(threadId, toolCallId, true);
      if (result.ok ?? result.success) {
        addToolResult?.({ tool: toolName, toolCallId, output: { approved: true } });
        setConfirmationStatus('confirmed');
        return;
      }
    } catch {
      // fall through
    }
    setConfirmationStatus('idle');
  }, [addToolResult, confirmationStatus, threadId, toolCallId, toolName]);

  const handleReject = useCallback(async () => {
    if (confirmationStatus !== 'idle') return;
    setConfirmationStatus('confirming');
    try {
      const result = await confirmToolCall(threadId, toolCallId, false, '用户拒绝执行工具');
      if (result.ok ?? result.success) {
        addToolResult?.({ tool: toolName, toolCallId, output: { approved: false } });
        setConfirmationStatus('rejected');
        return;
      }
    } catch {
      // fall through
    }
    setConfirmationStatus('idle');
  }, [addToolResult, confirmationStatus, threadId, toolCallId, toolName]);

  useEffect(() => {
    if (!shouldShowApprovalUI) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        void handleApprove();
      }
      if ((event.metaKey || event.ctrlKey) && event.key === 'Escape') {
        event.preventDefault();
        void handleReject();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleApprove, handleReject, shouldShowApprovalUI]);

  const handleAskUserSubmit = useCallback(async (answers: Record<string, unknown>) => {
    if (confirmationStatus !== 'idle') return;
    setConfirmationStatus('confirming');
    try {
      const result = await confirmToolCall(threadId, toolCallId, true, undefined, answers);
      if (result.ok ?? result.success) {
        addToolResult?.({ tool: toolName, toolCallId, output: answers });
        setConfirmationStatus('confirmed');
        return;
      }
    } catch {
      // fall through
    }
    setConfirmationStatus('idle');
  }, [addToolResult, confirmationStatus, threadId, toolCallId, toolName]);

  const handleAskUserCancel = useCallback(async () => {
    if (confirmationStatus !== 'idle') return;
    setConfirmationStatus('confirming');
    try {
      const result = await confirmToolCall(threadId, toolCallId, false, '用户取消了问题回答');
      if (result.ok ?? result.success) {
        addToolResult?.({ tool: toolName, toolCallId, output: { cancelled: true } });
        setConfirmationStatus('rejected');
        return;
      }
    } catch {
      // fall through
    }
    setConfirmationStatus('idle');
  }, [addToolResult, confirmationStatus, threadId, toolCallId, toolName]);

  const handleEditorWriteApprove = useCallback(async () => {
    if (confirmationStatus !== 'idle') return;
    setConfirmationStatus('confirming');
    try {
      const result = await confirmToolCall(threadId, toolCallId, true);
      if (result.ok ?? result.success) {
        addToolResult?.({ tool: toolName, toolCallId, output: { approved: true } });
        setConfirmationStatus('confirmed');
        onEditorWriteConfirmed?.();
        return;
      }
    } catch {
      // fall through
    }
    setConfirmationStatus('idle');
  }, [addToolResult, confirmationStatus, onEditorWriteConfirmed, threadId, toolCallId, toolName]);

  const handleEditorWriteReject = useCallback(async (reason?: string) => {
    if (confirmationStatus !== 'idle') return;
    setConfirmationStatus('confirming');
    try {
      const result = await confirmToolCall(threadId, toolCallId, false, reason || '用户拒绝了编辑器写操作');
      if (result.ok ?? result.success) {
        addToolResult?.({ tool: toolName, toolCallId, output: { approved: false } });
        setConfirmationStatus('rejected');
        return;
      }
    } catch {
      // fall through
    }
    setConfirmationStatus('idle');
  }, [addToolResult, confirmationStatus, threadId, toolCallId, toolName]);

  // When the AskUserQuestion form is active, render only the question UI (no
  // collapsible header) so the user sees the clean form immediately.
  if (shouldShowAskUserUI) {
    return (
      <div style={{ width: '100%' }}>
        {confirmationStatus === 'idle' && input !== undefined ? (
          <AskUserQuestionUI
            input={input as AskUserQuestionInput}
            toolCallId={toolCallId}
            toolName={toolName}
            isProcessing={false}
            onSubmit={handleAskUserSubmit}
            onCancel={handleAskUserCancel}
          />
        ) : confirmationStatus === 'idle' ? (
          <div style={{ borderRadius: '14px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '1.25rem', color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center' }}>
            <IconLoader style={{ width: '1rem', height: '1rem', display: 'inline-block', marginRight: '0.5rem' }} />
            加载中…
          </div>
        ) : confirmationStatus === 'confirming' ? (
          <StatusRow tone="warning" label="提交中…" />
        ) : confirmationStatus === 'confirmed' ? (
          <StatusRow tone="success" label="答案已提交" icon={<IconCheck style={{ width: '1rem', height: '1rem' }} />} />
        ) : (
          <StatusRow tone="danger" label="已取消" icon={<IconX style={{ width: '1rem', height: '1rem' }} />} />
        )}
      </div>
    );
  }

  // Editor write tools (write_segment, delete_segment, insert_widget, reply_to_comment)
  // are always-confirm tools; render the specialized approval UI directly.
  if (shouldShowEditorWriteUI) {
    return (
      <div style={{ width: '100%' }}>
        {confirmationStatus === 'idle' && input !== undefined ? (
          <EditorWriteApprovalUI
            toolName={toolName}
            toolCallId={toolCallId}
            input={input as Record<string, unknown>}
            isProcessing={false}
            onApprove={() => void handleEditorWriteApprove()}
            onReject={(reason) => void handleEditorWriteReject(reason)}
          />
        ) : confirmationStatus === 'idle' ? (
          <div style={{ borderRadius: '14px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', padding: '1.25rem', color: 'var(--color-text-muted)', fontSize: '0.85rem', textAlign: 'center' }}>
            <IconLoader style={{ width: '1rem', height: '1rem', display: 'inline-block', marginRight: '0.5rem' }} />
            加载中…
          </div>
        ) : confirmationStatus === 'confirming' ? (
          <StatusRow tone="warning" label="处理中…" />
        ) : confirmationStatus === 'confirmed' ? (
          <StatusRow tone="success" label="操作已接受" icon={<IconCheck style={{ width: '1rem', height: '1rem' }} />} />
        ) : (
          <StatusRow tone="danger" label="操作已拒绝" icon={<IconX style={{ width: '1rem', height: '1rem' }} />} />
        )}
      </div>
    );
  }

  return (
    <div style={{ width: '100%' }}>
      <div style={{ display: 'flex', flexDirection: 'column', borderRadius: '12px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}>
        <div onClick={() => setExpanded((value) => !value)} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 0.9rem', cursor: 'pointer' }}>
          <div style={{ display: 'grid', placeItems: 'center', width: '1.9rem', height: '1.9rem', borderRadius: '10px', background: 'var(--color-bg-surface)', color: isError ? '#d9534f' : isExecuting ? 'var(--color-action-link)' : 'var(--color-text-secondary)' }}>
            {isExecuting ? <IconLoader style={{ width: '0.95rem', height: '0.95rem' }} /> : isError ? <IconAlert /> : <IconTool />}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>{title || toolName}</div>
            <div style={{ marginTop: '0.15rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{partType}{providerExecuted !== undefined ? ` • ${providerExecuted ? 'provider' : 'local'} execution` : ''}</div>
          </div>
          <div style={{ color: 'var(--color-text-muted)' }}>{expanded ? <IconChevronUp style={{ width: '1rem', height: '1rem' }} /> : <IconChevronDown style={{ width: '1rem', height: '1rem' }} />}</div>
        </div>

        {expanded ? (
          <div style={{ padding: '0 0.9rem 0.9rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <section style={{ borderRadius: '10px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', padding: '0.85rem' }}>
              <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Tool info</h5>
              <div style={{ display: 'grid', gap: '0.3rem', fontSize: '0.78rem', color: 'var(--color-text-secondary)' }}>
                <div>Type: {partType}</div>
                <div>Tool: {toolName}</div>
                <div>Call ID: <code>{toolCallId}</code></div>
                <div>Status: {state || 'pending'}</div>
                {title ? <div>Title: {title}</div> : null}
              </div>
            </section>
            <section style={{ borderRadius: '10px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', padding: '0.85rem' }}>
              <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Input</h5>
              <pre style={{ margin: 0, fontSize: '0.76rem', whiteSpace: 'pre-wrap', overflowX: 'auto', color: 'var(--color-text-secondary)' }}>{inputDisplay}</pre>
            </section>
            {outputDisplay ? (
              <section style={{ borderRadius: '10px', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', padding: '0.85rem' }}>
                <h5 style={{ margin: '0 0 0.5rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{isError ? 'Error' : 'Output'}</h5>
                <pre style={{ margin: 0, fontSize: '0.76rem', whiteSpace: 'pre-wrap', overflowX: 'auto', color: isError ? '#d9534f' : 'var(--color-text-secondary)' }}>{outputDisplay}</pre>
              </section>
            ) : null}
          </div>
        ) : null}

        {shouldShowApprovalUI && confirmationStatus === 'idle' ? (
          <div style={{ display: 'flex', gap: '0.75rem', padding: '0 0.9rem 0.9rem' }}>
            <button type="button" onClick={() => void handleApprove()} style={{ flex: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', border: 'none', borderRadius: '999px', padding: '0.8rem 1rem', background: 'var(--color-action-link)', color: '#fff', fontWeight: 600, cursor: 'pointer' }}><IconCheck style={{ width: '1rem', height: '1rem' }} />Approve</button>
            <button type="button" onClick={() => void handleReject()} style={{ flex: 1, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', borderRadius: '999px', padding: '0.8rem 1rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-paper)', color: 'var(--color-text-secondary)', fontWeight: 600, cursor: 'pointer' }}><IconX style={{ width: '1rem', height: '1rem' }} />Cancel</button>
          </div>
        ) : null}
        {shouldShowApprovalUI && confirmationStatus === 'confirming' ? <StatusRow tone="warning" label="Processing…" /> : null}
        {shouldShowApprovalUI && confirmationStatus === 'confirmed' ? <StatusRow tone="success" label="Confirmed" icon={<IconCheck style={{ width: '1rem', height: '1rem' }} />} /> : null}
        {shouldShowApprovalUI && confirmationStatus === 'rejected' ? <StatusRow tone="danger" label="Cancelled" icon={<IconX style={{ width: '1rem', height: '1rem' }} />} /> : null}
        {isExecuting ? <StatusRow tone="warning" label="Executing…" /> : null}
      </div>
    </div>
  );
}

function StatusRow({ tone, label, icon }: { tone: 'warning' | 'success' | 'danger'; label: string; icon?: ReactNode }) {
  const color = tone === 'success' ? '#22c55e' : tone === 'danger' ? '#d9534f' : 'var(--color-action-link)';
  return <div style={{ padding: '0 0.9rem 0.9rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color, fontSize: '0.85rem' }}>{icon || <IconLoader style={{ width: '1rem', height: '1rem' }} />}{label}</div>;
}

export default ToolMessagePart;
