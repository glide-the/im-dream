// [Input] PendingToolConfirmation descriptor from ChatPanel; confirmToolCall from toolConfirmation;
//         AskUserQuestionUI (unframed variant) for askuser questions; toolInputSummary helpers.
// [Output] Floating confirmation panel rendered above AIInputDock: generic tool approvals show
//          拒绝/同意, AskUserQuestion prompts show the option form with 取消/提交.
// [Pos] tool-confirmation-dock component node in frontend/src/components/chat
// [Sync] 2026-07-20: created — tool confirmations moved out of the message list into this
//        floating dock (design: claude-agent-tool-confirmation-flow.md §8).
// [Sync] 2026-07-20: cap panel height at min(46vh, 24rem) with internal scroll and mount the
//        AskUserQuestion form in compact density so the dock never fills the chat viewport.
// [Sync] 2026-07-20: the dock now RENDERS IN PLACE OF AIInputDock (input dock hidden while a
//        confirmation is pending) instead of floating above it — the panel occupies the
//        composer slot in normal flow.
import { useCallback, useEffect, useMemo, useState } from 'react';
import AskUserQuestionUI, { type AskUserQuestionInput } from './AskUserQuestionUI';
import { confirmToolCall, type PendingToolConfirmation } from './toolConfirmation';
import { isShellTool, resolveToolInputSummary, summarizeToolInvocation } from './toolInputSummary';
import { IconCheck, IconLoader, IconX } from './Icons';

type DockStatus = 'idle' | 'confirming' | 'confirmed' | 'rejected';

interface ToolConfirmationDockProps {
  confirmation: PendingToolConfirmation;
  threadId: string;
  addToolResult?: (params: { tool: string; toolCallId: string; output: unknown }) => void;
}

function KbdHint({ label }: { label: string }) {
  return (
    <span style={{ marginLeft: '0.4rem', fontSize: '0.68rem', opacity: 0.55, fontWeight: 500, letterSpacing: '0.02em' }}>{label}</span>
  );
}

export default function ToolConfirmationDock({ confirmation, threadId, addToolResult }: ToolConfirmationDockProps) {
  const [status, setStatus] = useState<DockStatus>('idle');
  const { kind, toolCallId, toolName, input } = confirmation;

  const summaryText = useMemo(() => summarizeToolInvocation(toolName, input), [toolName, input]);
  const commandText = useMemo(() => (isShellTool(toolName) ? resolveToolInputSummary(input).command : ''), [toolName, input]);
  const detailText = useMemo(() => {
    if (commandText) return commandText;
    if (input == null) return '';
    try {
      const json = JSON.stringify(input);
      return json.length > 240 ? `${json.slice(0, 240)}…` : json;
    } catch {
      return String(input);
    }
  }, [commandText, input]);

  const runConfirm = useCallback(async (approved: boolean, reason?: string, answers?: Record<string, unknown>) => {
    if (status !== 'idle') return;
    setStatus('confirming');
    try {
      const result = await confirmToolCall(threadId, toolCallId, approved, reason, answers);
      if (result.ok ?? result.success) {
        addToolResult?.({
          tool: toolName,
          toolCallId,
          output: answers ?? (approved ? { approved: true } : { approved: false, cancelled: true }),
        });
        setStatus(approved ? 'confirmed' : 'rejected');
        return;
      }
    } catch {
      // fall through — restore the panel so the user can retry
    }
    setStatus('idle');
  }, [addToolResult, status, threadId, toolCallId, toolName]);

  const handleApprove = useCallback(() => void runConfirm(true), [runConfirm]);
  const handleReject = useCallback(() => void runConfirm(false, '用户拒绝执行工具'), [runConfirm]);
  const handleAskUserSubmit = useCallback((answers: Record<string, unknown>) => void runConfirm(true, undefined, answers), [runConfirm]);
  const handleAskUserCancel = useCallback(() => void runConfirm(false, '用户取消了问题回答'), [runConfirm]);

  // Keyboard shortcuts for the generic confirm variant: Esc = 拒绝, ⌘/Ctrl+⏎ = 同意.
  // The askuser variant keeps its own shortcuts inside AskUserQuestionUI.
  useEffect(() => {
    if (kind !== 'confirm' || status !== 'idle') return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
        event.preventDefault();
        handleApprove();
      } else if (event.key === 'Escape') {
        event.preventDefault();
        handleReject();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleApprove, handleReject, kind, status]);

  const isAskUser = kind === 'askuser';
  const title = isAskUser
    ? 'I&M 需要你的回答'
    : `是否允许 I&M 调用 ${toolName || '未知'} 工具${summaryText ? `，${summaryText}` : ''}`;

  return (
    <div
      role="alertdialog"
      aria-label={title}
      style={{
        width: '100%',
        boxSizing: 'border-box',
        borderRadius: '18px',
        border: '1px solid var(--color-border-paper)',
        background: 'var(--color-bg-paper)',
        boxShadow: '0 12px 32px var(--color-shadow-soft, rgba(0,0,0,0.12))',
        padding: '0.85rem 1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.55rem',
        // Cap the panel height so long AskUserQuestion forms never dominate the
        // chat viewport — the content scrolls internally instead.
        maxHeight: 'min(46vh, 24rem)',
        overflowY: 'auto',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem' }}>
        <span aria-hidden="true" style={{ marginTop: '0.35rem', width: '0.55rem', height: '0.55rem', borderRadius: '999px', background: '#f59e0b', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0, fontSize: '0.95rem', fontWeight: 600, lineHeight: 1.5, color: 'var(--color-text-primary)', wordBreak: 'break-word' }}>
          {title}
        </div>
        <span style={{ flexShrink: 0, borderRadius: '999px', padding: '0.15rem 0.55rem', fontSize: '0.72rem', fontWeight: 600, color: '#b45309', background: 'color-mix(in srgb, #f59e0b 16%, transparent)' }}>
          {isAskUser ? '待回答' : '待授权'}
        </span>
      </div>

      {status === 'idle' && isAskUser ? (
        <AskUserQuestionUI
          input={(input ?? {}) as AskUserQuestionInput}
          toolCallId={toolCallId}
          toolName={toolName}
          isProcessing={false}
          framed={false}
          showHeader={false}
          compact
          submitLabel="提交"
          cancelLabel="取消"
          onSubmit={handleAskUserSubmit}
          onCancel={handleAskUserCancel}
        />
      ) : status === 'idle' && detailText ? (
        <div
          style={{
            fontSize: '0.85rem',
            lineHeight: 1.65,
            color: 'var(--color-text-muted)',
            fontFamily: commandText ? 'ui-monospace, SFMono-Regular, Menlo, monospace' : undefined,
            wordBreak: 'break-all',
            display: '-webkit-box',
            WebkitBoxOrient: 'vertical',
            WebkitLineClamp: 4,
            overflow: 'hidden',
          }}
        >
          {commandText ? `命令：${detailText}` : `参数：${detailText}`}
        </div>
      ) : null}

      {status === 'idle' && !isAskUser ? (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.6rem' }}>
          <button
            type="button"
            onClick={handleReject}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', borderRadius: '999px', padding: '0.5rem 1.05rem', border: '1px solid var(--color-border-paper)', background: 'var(--color-bg-surface)', color: 'var(--color-text-secondary)', fontSize: '0.86rem', fontWeight: 600, cursor: 'pointer' }}
          >
            拒绝
            <KbdHint label="ESC" />
          </button>
          <button
            type="button"
            onClick={handleApprove}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', borderRadius: '999px', padding: '0.5rem 1.05rem', border: 'none', background: 'var(--color-action-link)', color: 'var(--color-text-on-action)', fontSize: '0.86rem', fontWeight: 600, cursor: 'pointer' }}
          >
            同意
            <KbdHint label="⌘⏎" />
          </button>
        </div>
      ) : null}

      {status === 'confirming' ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--color-action-link)', fontSize: '0.85rem' }}>
          <IconLoader style={{ width: '1rem', height: '1rem' }} />
          {isAskUser ? '提交中…' : '处理中…'}
        </div>
      ) : null}
      {status === 'confirmed' ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: '#22c55e', fontSize: '0.85rem' }}>
          <IconCheck style={{ width: '1rem', height: '1rem' }} />
          {isAskUser ? '答案已提交' : '已同意'}
        </div>
      ) : null}
      {status === 'rejected' ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--color-state-error)', fontSize: '0.85rem' }}>
          <IconX style={{ width: '1rem', height: '1rem' }} />
          {isAskUser ? '已取消' : '已拒绝'}
        </div>
      ) : null}
    </div>
  );
}
