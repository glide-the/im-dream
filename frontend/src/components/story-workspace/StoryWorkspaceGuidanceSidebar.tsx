// [Input] Authoritative run snapshot, execution page state, authenticated
//         actor id, and reverse-looked guidance history.
// [Output] 360px Agent guidance sidebar (design_004 §5.3): preset actions
//          (重试失败步骤 / 补充约束) + free-text input, idempotent submit to
//          the Task 3 endpoint, result presentation including the
//          dispatched:false "已记录待拾取" state (R2), and the guidance
//          history list (指令 + 状态 + 时间).
// [Pos] Story Workspace execution page guidance sidebar (Task 5)
// [Sync] 2026-08-04: initial implementation. All presentation decisions come
//                    from executionState / useStoryWorkspaceGuidance seams;
//                    the server stays authoritative for guidability (client
//                    gating only pre-disables obvious cases; 409s render).

import { useEffect, useRef, useState } from 'react';
import type { WorkflowRun } from '../../api/storyWorkspaceApi';
import { getAuthToken, useAuth } from '../../contexts/AuthContext';
import { apiUrl } from '../../lib/apiBase';
import type {
  StoryWorkspaceExecutionPageState,
  StoryWorkspaceGuidanceHistoryEntry,
  StoryWorkspaceGuidanceKind,
} from '../../hooks/story-workspace/contracts';
import {
  buildStoryWorkspaceGuidancePayload,
  describeStoryWorkspaceGuidanceResult,
  newStoryWorkspaceGuidanceIdempotencyKey,
  storyWorkspaceGuidanceEndpoint,
  submitStoryWorkspaceGuidance,
} from '../../hooks/story-workspace/useStoryWorkspaceGuidance';
import {
  isStoryWorkspaceGuidableStatus,
  STORY_WORKSPACE_EXECUTION_STATE_COPY,
} from './executionState';

const CONSTRAINT_PRESET_PREFIX = '补充约束：';

const ERROR_TEXT: Record<string, string> = {
  WORKFLOW_RUN_NOT_GUIDABLE: '当前运行状态不可指导（仅执行中或失败的运行可指导）。',
  IDEMPOTENCY_CONFLICT: '相同幂等键但内容不同，服务端已拒绝；请修改后重试。',
  WORKFLOW_PERMISSION_DENIED: '身份校验失败，请重新登录后再试。',
};

function formatHistoryTime(value: string | null): string {
  if (!value) return '时间未知';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未知';
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

function historyKindLabel(entry: StoryWorkspaceGuidanceHistoryEntry): string {
  return entry.commandKind === 'retry-step' ? '重试步骤' : '自由指导';
}

export interface StoryWorkspaceGuidanceSidebarProps {
  run: WorkflowRun;
  state: StoryWorkspaceExecutionPageState;
  history: StoryWorkspaceGuidanceHistoryEntry[];
  historyLoading?: boolean;
  /** Called after an accepted submission so the page can refresh history/run. */
  onSubmitted?: () => void;
}

export function StoryWorkspaceGuidanceSidebar({
  run,
  state,
  history,
  historyLoading = false,
  onSubmitted,
}: StoryWorkspaceGuidanceSidebarProps) {
  const { user } = useAuth();
  const actorId = user ? String(user.id) : null;
  const guidable = isStoryWorkspaceGuidableStatus(run.status) && actorId !== null;

  const [text, setText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<'info' | 'error'>('info');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  // One in-flight idempotency key per logical submission: re-clicks while
  // submitting reuse it so the server replay path applies (202 replayed:true).
  const inFlightKeyRef = useRef<string | null>(null);

  const retryStepId = run.status === 'failed' ? run.failed_step : null;

  useEffect(() => {
    if (state === 'awaiting-guidance') textareaRef.current?.focus();
  }, [state]);

  const submit = async (kind: StoryWorkspaceGuidanceKind, stepId?: string | null) => {
    if (submitting || !guidable || !actorId) return;
    const payload = buildStoryWorkspaceGuidancePayload({
      kind,
      actor: actorId,
      text,
      stepId: stepId ?? undefined,
      idempotencyKey: inFlightKeyRef.current ?? newStoryWorkspaceGuidanceIdempotencyKey(),
    });
    if (!payload) {
      setFeedbackTone('error');
      setFeedback(kind === 'retry-step' ? '缺少要重试的步骤。' : '请先输入指导内容。');
      return;
    }
    inFlightKeyRef.current = payload.idempotency_key;
    setSubmitting(true);
    setFeedback(null);
    try {
      const outcome = await submitStoryWorkspaceGuidance(
        apiUrl(storyWorkspaceGuidanceEndpoint(run.workflow_run_id)),
        payload,
        { token: getAuthToken() },
      );
      if (outcome.ok) {
        setFeedbackTone('info');
        setFeedback(describeStoryWorkspaceGuidanceResult(outcome.result));
        if (!outcome.result.replayed) setText('');
        onSubmitted?.();
      } else {
        setFeedbackTone('error');
        setFeedback(
          (outcome.errorCode && ERROR_TEXT[outcome.errorCode])
            ?? `指导提交失败（${outcome.status || '网络异常'}），请稍后重试。`,
        );
      }
    } finally {
      inFlightKeyRef.current = null;
      setSubmitting(false);
    }
  };

  const applyConstraintPreset = () => {
    setText((current) => (current.trim() ? current : CONSTRAINT_PRESET_PREFIX));
    textareaRef.current?.focus();
  };

  return (
    <aside
      aria-label="Agent 指导"
      className="story-workspace-guidance-sidebar"
      data-awaiting={state === 'awaiting-guidance' || undefined}
    >
      <header className="story-workspace-guidance-sidebar__header">
        <p className="story-workspace-page__eyebrow">Guidance</p>
        <h2 className="story-workspace-guidance-sidebar__title">指导 Agent</h2>
        <p className="story-workspace-guidance-sidebar__status">
          {STORY_WORKSPACE_EXECUTION_STATE_COPY[state].badge}
          {state === 'awaiting-guidance' && ' · 主焦点'}
        </p>
      </header>

      <div aria-label="预设动作" className="story-workspace-guidance-sidebar__presets">
        <button
          className="workflow-button"
          disabled={!guidable || submitting || !retryStepId}
          onClick={() => void submit('retry-step', retryStepId)}
          title={retryStepId ? `重试步骤 ${retryStepId}` : '仅失败的运行可重试失败步骤'}
          type="button"
        >
          重试失败步骤
        </button>
        <button
          className="workflow-button"
          disabled={!guidable || submitting}
          onClick={applyConstraintPreset}
          type="button"
        >
          补充约束
        </button>
      </div>

      <label className="story-workspace-guidance-sidebar__input">
        指令输入
        <textarea
          aria-label="指导指令输入框"
          disabled={!guidable || submitting}
          onChange={(event) => setText(event.target.value)}
          placeholder={guidable ? '给执行中的 Agent 下达指导（多行）…' : '当前状态不可指导'}
          ref={textareaRef}
          rows={4}
          value={text}
        />
      </label>
      <button
        className="workflow-button workflow-button--primary"
        disabled={!guidable || submitting || !text.trim()}
        onClick={() => void submit('free-text')}
        type="button"
      >
        {submitting ? '提交中…' : '发送指导'}
      </button>

      {feedback && (
        <p
          className={`story-workspace-guidance-sidebar__feedback story-workspace-guidance-sidebar__feedback--${feedbackTone}`}
          role="status"
        >
          {feedback}
        </p>
      )}

      <section aria-label="指导历史" className="story-workspace-guidance-sidebar__history">
        <h3 className="story-workspace-guidance-sidebar__history-title">指导历史</h3>
        {historyLoading ? (
          <p className="story-workspace-table__secondary">正在加载指导历史…</p>
        ) : history.length === 0 ? (
          <p className="story-workspace-table__secondary">暂无指导记录。</p>
        ) : (
          <ol className="story-workspace-guidance-sidebar__history-list">
            {history.map((entry) => (
              <li key={entry.messageId}>
                <strong>{historyKindLabel(entry)}</strong>
                {entry.stepId && <code>{entry.stepId}</code>}
                {entry.textSummary && <span>{entry.textSummary}</span>}
                <time dateTime={entry.createdAt ?? undefined}>{formatHistoryTime(entry.createdAt)}</time>
              </li>
            ))}
          </ol>
        )}
      </section>
    </aside>
  );
}
