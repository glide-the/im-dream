// [Input] Workflow preflight REST operations and a fixed polling interval.
// [Output] Server-authoritative preflight state plus start/refresh commands.
// [Pos] Story Workspace workflow preflight state adapter.
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createWorkflowPreflight,
  getWorkflowPreflight,
  type CreateWorkflowPreflightInput,
  type WorkflowPreflight,
} from '../api/storyWorkspaceApi';

export interface UseWorkflowPreflightOptions {
  pollIntervalMs?: number;
}

export interface UseWorkflowPreflightResult {
  preflight: WorkflowPreflight | null;
  error: Error | null;
  isSubmitting: boolean;
  startPreflight: (input: CreateWorkflowPreflightInput) => Promise<WorkflowPreflight>;
  refreshPreflight: () => Promise<WorkflowPreflight | null>;
  clearPreflight: () => void;
}

export function useWorkflowPreflight({
  pollIntervalMs = 1500,
}: UseWorkflowPreflightOptions = {}): UseWorkflowPreflightResult {
  const [preflight, setPreflight] = useState<WorkflowPreflight | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const activePreflightIdRef = useRef<string | null>(null);

  const refreshPreflight = useCallback(async () => {
    const preflightId = activePreflightIdRef.current;
    if (!preflightId) return null;

    try {
      const next = await getWorkflowPreflight(preflightId);
      if (activePreflightIdRef.current === preflightId) {
        setPreflight(next);
        setError(null);
      }
      return next;
    } catch (cause) {
      if (activePreflightIdRef.current === preflightId) {
        setError(cause instanceof Error ? cause : new Error('预检状态读取失败'));
      }
      throw cause;
    }
  }, []);

  useEffect(() => {
    if (!preflight || preflight.status !== 'checking') return undefined;
    const intervalId = window.setInterval(() => {
      void refreshPreflight().catch(() => undefined);
    }, pollIntervalMs);
    return () => window.clearInterval(intervalId);
  }, [pollIntervalMs, preflight, refreshPreflight]);

  const startPreflight = useCallback(async (input: CreateWorkflowPreflightInput) => {
    setIsSubmitting(true);
    setError(null);
    try {
      const next = await createWorkflowPreflight(input);
      activePreflightIdRef.current = next.workflow_preflight_id;
      setPreflight(next);
      return next;
    } catch (cause) {
      const nextError = cause instanceof Error ? cause : new Error('无法开始工作流预检');
      setError(nextError);
      throw nextError;
    } finally {
      setIsSubmitting(false);
    }
  }, []);

  const clearPreflight = useCallback(() => {
    activePreflightIdRef.current = null;
    setPreflight(null);
    setError(null);
  }, []);

  return {
    preflight,
    error,
    isSubmitting,
    startPreflight,
    refreshPreflight,
    clearPreflight,
  };
}
