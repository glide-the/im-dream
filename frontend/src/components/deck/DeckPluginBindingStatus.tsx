// [Input] Deck Plugin request state and optional current Workflow Run reference.
// [Output] Always-visible next-run semantics plus safe loading, save, conflict, and result notices.
// [Pos] Status strip beneath the Deck Editor Plugin binding card.

import type { DeckPluginBindingConflict } from '../../hooks/useDeckPluginBinding';

interface Props {
  loading: boolean;
  saving: boolean;
  error: string | null;
  successMessage: string | null;
  conflict: DeckPluginBindingConflict | null;
  currentWorkflowRunId?: string | null;
}

export default function DeckPluginBindingStatus({
  loading,
  saving,
  error,
  successMessage,
  conflict,
  currentWorkflowRunId,
}: Props) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }} aria-live="polite">
      <div style={{ color: 'var(--color-state-warning)', fontSize: 12, lineHeight: 1.45 }}>
        ⚠️ 选择变更仅影响下一次运行；历史和当前运行不变
      </div>
      {currentWorkflowRunId && (
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 12 }}>
          当前运行使用中：<code>{currentWorkflowRunId}</code>；新选择供下一次运行使用。
        </div>
      )}
      {(loading || saving) && (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>
          {saving ? '正在保存下一次运行的插件版本…' : '正在加载 Deck 工作流插件…'}
        </div>
      )}
      {successMessage && (
        <div style={{ color: 'var(--color-state-success)', fontSize: 12 }}>
          {successMessage}
        </div>
      )}
      {conflict && (
        <div
          role="alert"
          style={{
            color: 'var(--color-state-warning)',
            background: 'var(--color-bg-surface)',
            border: '1px solid var(--color-state-warning)',
            borderRadius: 8,
            padding: '8px 10px',
            fontSize: 12,
            lineHeight: 1.45,
          }}
        >
          {conflict.message}
          {conflict.currentRevision !== null && ` 当前 revision：${conflict.currentRevision}。`}
          {' '}
          {conflict.selectionStillAvailable
            ? '原选择仍可用，已为你保留，请再次确认。'
            : '原选择已不可用，请选择其他版本。'}
        </div>
      )}
      {error && (
        <div role="alert" style={{ color: 'var(--color-state-error)', fontSize: 12 }}>
          {error}
        </div>
      )}
    </div>
  );
}
