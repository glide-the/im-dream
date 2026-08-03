// [Input] Authoritative run snapshot + optional execution projection.
// [Output] Read-only execution progress table (design_004 §5.2 任务进度):
//          step / status / duration / failure reason / retry count columns.
// [Pos] Story Workspace execution page data-layer leaf (Task 5); hook-free
//       pure render so node-side tests can direct-call it.
// [Sync] 2026-08-04: initial implementation. The run read exposes no step
//                    rows and no projection endpoint exists yet — without
//                    projection steps the table degrades to an explicit empty
//                    state plus run-level failure facts (see the Task 5
//                    implementation record).

import type { WorkflowRun } from '../../api/storyWorkspaceApi';
import type {
  StoryWorkspaceExecutionProjection,
  StoryWorkspaceExecutionStep,
} from '../../hooks/story-workspace/contracts';

const STEP_STATUS_LABELS: Record<string, string> = {
  waiting: '等待',
  running: '运行中',
  completed: '完成',
  failed: '失败',
  blocked: '阻塞',
};

function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds < 0) return '—';
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.floor(seconds % 60);
  return minutes > 0 ? `${minutes} 分 ${remainder} 秒` : `${remainder} 秒`;
}

function stepRows(
  projection: StoryWorkspaceExecutionProjection | null | undefined,
): StoryWorkspaceExecutionStep[] {
  return projection?.steps ?? [];
}

export interface StoryWorkspaceExecutionProgressTableProps {
  run: WorkflowRun;
  projection?: StoryWorkspaceExecutionProjection | null;
}

/** 任务进度 tab — read-only step table (§5.2; zero write affordances). */
export function StoryWorkspaceExecutionProgressTable({
  run,
  projection,
}: StoryWorkspaceExecutionProgressTableProps) {
  const steps = stepRows(projection);

  return (
    <section aria-label="任务进度" className="story-workspace-execution-progress">
      {steps.length === 0 ? (
        <div className="story-workspace-table-message">
          <p>暂无步骤数据：执行事实投影尚未透出，步骤级进度以 Chat 执行过程为准。</p>
          {run.current_step && <p>当前步骤：{run.current_step}</p>}
          {run.status === 'failed' && run.failed_step && (
            <p>失败步骤：{run.failed_step}（{run.error_code ?? '未知错误'}）</p>
          )}
        </div>
      ) : (
        <table className="story-workspace-execution-progress__table">
          <thead>
            <tr>
              <th scope="col">步骤</th>
              <th scope="col">状态</th>
              <th scope="col">耗时</th>
              <th scope="col">失败原因</th>
              <th scope="col">重试次数</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step, index) => (
              <tr data-blocked={step.blocked === true || step.status === 'blocked' || undefined} key={step.name ?? index}>
                <td>{step.name ?? `步骤 ${index + 1}`}</td>
                <td>{STEP_STATUS_LABELS[step.status ?? ''] ?? step.status ?? '—'}</td>
                <td>{formatDuration(step.duration_seconds)}</td>
                <td>{step.failure_reason ?? '—'}</td>
                <td>{step.retry_count ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
