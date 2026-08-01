// [Input] Workflow run REST mutations and ordered server events.
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
  type WorkflowRunEvent,
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
  eventTransport: 'idle' | 'connecting' | 'live' | 'polling';
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

  const onEvent = useCallback((event: WorkflowRunEvent) => {
    setRun((current) => {
      const eventRunId = event.workflow_run_id ?? event.aggregate_id;
      if (!current || current.workflow_run_id !== eventRunId) return current;
      if (event.aggregate_version <= current.status_version) return current;
      return {
        ...current,
        status: event.payload?.status ?? current.status,
        status_version: event.aggregate_version,
        failed_step: event.payload?.failed_step ?? current.failed_step,
        error_code: event.payload?.error_code ?? current.error_code,
        current_step: event.payload?.current_step ?? current.current_step,
        steps: event.payload?.steps ?? current.steps,
      };
    });
  }, []);

  const events = useWorkflowEvents({
    workflowRunId: run?.workflow_run_id,
    enabled: eventsEnabled,
    onEvent,
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
