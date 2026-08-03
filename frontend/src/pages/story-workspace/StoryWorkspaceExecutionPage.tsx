// [Input] Route run id param + router navigation callback.
// [Output] Standalone execution page (design_004 §5, DEC-030): breadcrumb
//          (Dream / Runs / <runId> / 执行) + left read-only data tabs
//          (任务进度 / 资产 / 运行记录) + right 360px guidance sidebar; Gate
//          redirect for unconfirmed runs (§5.5); five-state UI (§5.4).
// [Pos] /story-workspace/runs/:storyWorkspaceRunId/execution page (Task 5)
// [Sync] 2026-08-04: initial implementation. AppHeader/sidebar chrome with
//                    the Dream selected state is provided by the router's
//                    StoryWorkspaceLayout; this page owns only the §5.1
//                    two-zone content. All presentation decisions come from
//                    the executionState seams.

import { useCallback, useEffect, useState } from 'react';
import {
  getWorkflowRun,
  type WorkflowRun,
} from '../../api/storyWorkspaceApi';
import {
  StoryWorkspaceExecutionAssetPanel,
  StoryWorkspaceExecutionProgressTable,
  StoryWorkspaceGuidanceSidebar,
} from '../../components/story-workspace';
import {
  resolveStoryWorkspaceExecutionRedirect,
  resolveStoryWorkspaceExecutionState,
  STORY_WORKSPACE_EXECUTION_STATE_COPY,
} from '../../components/story-workspace/executionState';
import type {
  StoryWorkspaceExecutionProjection,
  StoryWorkspaceGuidanceHistoryEntry,
} from '../../hooks/story-workspace/contracts';
import { useStoryWorkspaceGuidanceHistory } from '../../hooks/story-workspace/useStoryWorkspaceGuidance';

type ExecutionTab = 'progress' | 'assets' | 'records';

const EXECUTION_TABS: Array<{ id: ExecutionTab; label: string }> = [
  { id: 'progress', label: '任务进度' },
  { id: 'assets', label: '资产' },
  { id: 'records', label: '运行记录' },
];

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

interface RunRecordItem {
  key: string;
  label: string;
  at: string | null;
}

function buildRunRecords(
  run: WorkflowRun,
  guidance: StoryWorkspaceGuidanceHistoryEntry[],
): RunRecordItem[] {
  const records: RunRecordItem[] = [
    { key: 'created', label: '运行创建', at: run.created_at },
  ];
  if (run.started_at) records.push({ key: 'started', label: '执行开始', at: run.started_at });
  for (const entry of guidance) {
    records.push({
      key: entry.messageId,
      label: `提交指导（${entry.commandKind === 'retry-step' ? `重试步骤 ${entry.stepId ?? ''}` : entry.textSummary ?? '自由指导'}）`,
      at: entry.createdAt,
    });
  }
  if (run.completed_at) {
    records.push({
      key: 'completed',
      label: run.status === 'failed'
        ? `执行失败（${run.failed_step ?? '未知步骤'}${run.error_code ? ` · ${run.error_code}` : ''}）`
        : run.status === 'cancelled' ? '运行取消' : '执行完成',
      at: run.completed_at,
    });
  }
  return records;
}

export interface StoryWorkspaceExecutionPageProps {
  runId: string;
  /**
   * Episode binding for the gate redirect's review deep link. No
   * proposal↔run aggregation endpoint exists yet, so callers omit it and the
   * redirect degrades to the Dream entry route with ?run= (§4.4).
   */
  episodeId?: string | null;
  /**
   * Optional execution projection injection seam (Task 3 contract). No
   * projection endpoint exists yet; when absent the page degrades per the
   * Task 5 record (progress/assets empty states, no awaiting-guidance).
   */
  projection?: StoryWorkspaceExecutionProjection | null;
  /** Router navigation; falls back to full-page navigation when absent. */
  onNavigate?: (href: string, notice?: string) => void;
}

export function StoryWorkspaceExecutionPage({
  runId,
  episodeId,
  projection = null,
  onNavigate,
}: StoryWorkspaceExecutionPageProps) {
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ExecutionTab>('progress');

  const loadRun = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      setRun(await getWorkflowRun(runId));
    } catch (reason) {
      setRun(null);
      setLoadError(reason instanceof Error ? reason.message : '运行加载失败。');
    } finally {
      setIsLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    void loadRun();
  }, [loadRun]);

  const state = run ? resolveStoryWorkspaceExecutionState(run, projection) : null;
  const guidanceHistory = useStoryWorkspaceGuidanceHistory(run?.source_voice_thread_id);

  // Gate redirect (§5.5): the execution page only serves runs past Gate
  // step 4; anything else goes to the review deep link with a notice.
  useEffect(() => {
    if (!run || state !== 'not-confirmed') return;
    const target = resolveStoryWorkspaceExecutionRedirect(run.workflow_run_id, episodeId);
    const notice = STORY_WORKSPACE_EXECUTION_STATE_COPY['not-confirmed'].banner;
    if (onNavigate) {
      onNavigate(target, notice);
    } else if (typeof window !== 'undefined') {
      window.location.assign(target);
    }
  }, [run, state, episodeId, onNavigate]);

  const handleRefresh = useCallback(() => {
    guidanceHistory.refetch();
    void loadRun();
  }, [guidanceHistory, loadRun]);

  if (isLoading) {
    return (
      <section className="story-workspace-page story-workspace-execution-page">
        <div className="story-workspace-table-message">正在加载运行…</div>
      </section>
    );
  }

  if (loadError || !run || !state) {
    return (
      <section className="story-workspace-page story-workspace-execution-page">
        <div className="story-workspace-table-message story-workspace-table-message--error">
          {loadError ?? '运行不存在或无权查看。'}
        </div>
      </section>
    );
  }

  const copy = STORY_WORKSPACE_EXECUTION_STATE_COPY[state];
  const dreamHref = `/story-workspace/dream?run=${encodeURIComponent(run.workflow_run_id)}`;
  const records = buildRunRecords(run, guidanceHistory.entries);

  return (
    <section
      aria-labelledby="story-workspace-execution-title"
      className="story-workspace-page story-workspace-execution-page"
      data-execution-state={state}
    >
      <header className="story-workspace-execution-page__header">
        <nav aria-label="面包屑" className="story-workspace-execution-page__breadcrumb">
          <a
            href="/story-workspace/dream"
            onClick={onNavigate
              ? (event) => {
                event.preventDefault();
                onNavigate('/story-workspace/dream');
              }
              : undefined}
          >
            Dream
          </a>
          <span aria-hidden="true"> / </span>
          <span>Runs</span>
          <span aria-hidden="true"> / </span>
          <code>{run.workflow_run_id}</code>
          <span aria-hidden="true"> / </span>
          <span>执行</span>
        </nav>
        <div className="story-workspace-execution-page__title-row">
          <h1 className="story-workspace-page__title" id="story-workspace-execution-title">
            {run.workflow_summary?.trim() || 'Dream 后续执行'}
          </h1>
          <span
            className="story-workspace-execution-page__badge"
            data-execution-state={state}
          >
            {copy.badge}
          </span>
        </div>
        <p className="story-workspace-execution-page__banner" role={state === 'not-confirmed' ? 'alert' : undefined}>
          {copy.banner}
        </p>
        {run.status === 'failed' && run.failed_step && (
          <p className="story-workspace-execution-page__failure">
            失败阶段：{run.failed_step}（{run.error_code ?? '未知错误'}）
          </p>
        )}
      </header>

      <div className="story-workspace-execution-page__grid">
        <div className="story-workspace-execution-page__data">
          <div aria-label="数据层" className="story-workspace-execution-page__tabs" role="tablist">
            {EXECUTION_TABS.map((tab) => (
              <button
                aria-selected={activeTab === tab.id}
                className="story-workspace-execution-page__tab"
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                role="tab"
                type="button"
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'progress' && (
            <StoryWorkspaceExecutionProgressTable projection={projection} run={run} />
          )}
          {activeTab === 'assets' && (
            <StoryWorkspaceExecutionAssetPanel
              onNavigate={onNavigate}
              projection={projection}
              run={run}
            />
          )}
          {activeTab === 'records' && (
            <section aria-label="运行记录" className="story-workspace-execution-records">
              {records.length === 0 ? (
                <p className="story-workspace-table__secondary">暂无运行记录。</p>
              ) : (
                <ol className="story-workspace-execution-records__list">
                  {records.map((record) => (
                    <li key={record.key}>
                      <span>{record.label}</span>
                      <time dateTime={record.at ?? undefined}>{formatTimestamp(record.at)}</time>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          )}
        </div>

        <StoryWorkspaceGuidanceSidebar
          history={guidanceHistory.entries}
          historyLoading={guidanceHistory.isLoading}
          onSubmitted={handleRefresh}
          run={run}
          state={state}
        />
      </div>

      {state === 'completed' && (
        <footer className="story-workspace-execution-page__footer">
          <a
            href={dreamHref}
            onClick={onNavigate
              ? (event) => {
                event.preventDefault();
                onNavigate(dreamHref);
              }
              : undefined}
          >
            返回 Dream 查看产物
          </a>
        </footer>
      )}
    </section>
  );
}
