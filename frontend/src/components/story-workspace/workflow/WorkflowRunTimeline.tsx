// [Input] Server transition history and immutable retry/source references.
// [Output] Ordered workflow status timeline with safe reason codes.
// [Pos] Story Workspace workflow run detail timeline.
import type { WorkflowRunTransition } from '../../../api/storyWorkspaceApi';

export interface WorkflowRunTimelineProps {
  transitions: WorkflowRunTransition[];
  retryOfRunId?: string | null;
  resultRef?: string | null;
  onOpenRun?: (workflowRunId: string) => void;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '时间未知';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'medium',
  }).format(date);
}

export function WorkflowRunTimeline({
  transitions,
  retryOfRunId,
  resultRef,
  onOpenRun,
}: WorkflowRunTimelineProps) {
  const orderedTransitions = [...transitions].sort(
    (left, right) => left.transition_seq - right.transition_seq,
  );

  return (
    <section aria-labelledby="workflow-run-timeline-title" className="workflow-panel">
      <header className="workflow-panel__header">
        <div>
          <p className="workflow-panel__eyebrow">Run history</p>
          <h3 className="workflow-panel__title" id="workflow-run-timeline-title">运行时间线</h3>
        </div>
      </header>
      {orderedTransitions.length === 0 ? (
        <p className="workflow-panel__message">暂无可见状态记录。</p>
      ) : (
        <ol className="workflow-run-timeline">
          {orderedTransitions.map((transition) => (
            <li key={transition.transition_id}>
              <span aria-hidden="true" className="workflow-run-timeline__dot" />
              <div>
                <strong>{transition.to_status}</strong>
                <time dateTime={transition.occurred_at}>{formatTimestamp(transition.occurred_at)}</time>
                {transition.reason_code && <code>{transition.reason_code}</code>}
              </div>
            </li>
          ))}
        </ol>
      )}
      {(retryOfRunId || resultRef) && (
        <footer className="workflow-panel__footer workflow-panel__footer--stacked">
          {retryOfRunId && (
            <p>
              重试自：{' '}
              <button className="workflow-inline-button" onClick={() => onOpenRun?.(retryOfRunId)} type="button">
                {retryOfRunId}
              </button>
            </p>
          )}
          {resultRef && <p>结果引用：<code>{resultRef}</code></p>}
        </footer>
      )}
    </section>
  );
}
