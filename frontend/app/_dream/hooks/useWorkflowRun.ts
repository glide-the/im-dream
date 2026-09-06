// [Input] Workflow run REST mutations and actor-scoped status snapshots.
// [Output] Server-authoritative run state plus create/retry/cancel/refresh commands.
// [Pos] Story Workspace workflow run state adapter.
import { useCallback, useState } from 'react';
import {
  cancelWorkflowRun,
  createWorkflowRun,
  getWorkflowRun,
  retryWorkflowRun,
  type CreateWorkflowRunInput,
  type RetryWorkflowRunInput,
  type WorkflowRun,
} from '../api/storyWorkspaceApi';
import { useWorkflowEvents } from './useWorkflowEvents';

export interface UseWorkflowRunOptions {
  initialRun?: WorkflowRun | null;
  eventsEnabled?: boolean;
}

export interface UseWorkflowRunResult {
  run: WorkflowRun | null;
  error: Error | null;
  isMutating: boolean;
  eventTransport: 'idle' | 'polling';
  startRun: (input: CreateWorkflowRunInput) => Promise<WorkflowRun>;
  retryRun: (input: RetryWorkflowRunInput) => Promise<WorkflowRun>;
  cancelRun: () => Promise<WorkflowRun | null>;
  refreshRun: () => Promise<WorkflowRun | null>;
  selectRun: (workflowRunId: string) => Promise<WorkflowRun>;
}

export function useWorkflowRun({
  initialRun = null,
  eventsEnabled = true,
}: UseWorkflowRunOptions = {}): UseWorkflowRunResult {
  const [run, setRun] = useState<WorkflowRun | null>(initialRun);
  const [error, setError] = useState<Error | null>(null);
  const [isMutating, setIsMutating] = useState(false);

  const refreshById = useCallback(async (workflowRunId: string) => {
    try {
      const next = await getWorkflowRun(workflowRunId);
      setRun(next);
      setError(null);
      return next;
    } catch (cause) {
      const nextError = cause instanceof Error ? cause : new Error('运行状态读取失败');
      setError(nextError);
      throw nextError;
    }
  }, []);

  const refreshRun = useCallback(async () => {
    if (!run) return null;
    return refreshById(run.workflow_run_id);
  }, [refreshById, run]);

  const events = useWorkflowEvents({
    workflowRunId: run?.workflow_run_id,
    enabled: eventsEnabled,
    onSnapshot: setRun,
  });

  const runMutation = useCallback(async (operation: () => Promise<WorkflowRun>) => {
    setIsMutating(true);
    setError(null);
    try {
      const next = await operation();
      setRun(next);
      return next;
    } catch (cause) {
      const nextError = cause instanceof Error ? cause : new Error('工作流操作失败');
      setError(nextError);
      throw nextError;
    } finally {
      setIsMutating(false);
    }
  }, []);

  const startRun = useCallback(
    (input: CreateWorkflowRunInput) => runMutation(() => createWorkflowRun(input)),
    [runMutation],
  );

  const retryRun = useCallback((input: RetryWorkflowRunInput) => {
    if (!run) return Promise.reject(new Error('没有可重试的运行'));
    return runMutation(() => retryWorkflowRun(run.workflow_run_id, input));
  }, [run, runMutation]);

  const cancelRun = useCallback(() => {
    if (!run) return Promise.resolve(null);
    return runMutation(() => cancelWorkflowRun(run.workflow_run_id));
  }, [run, runMutation]);

  return {
    run,
    error,
    isMutating,
    eventTransport: events.connectionState,
    startRun,
    retryRun,
    cancelRun,
    refreshRun,
    selectRun: refreshById,
  };
}
