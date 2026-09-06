// [Input] A workflow run id and the actor-scoped run snapshot endpoint.
// [Output] Monotonically ordered workflow status snapshots through REST polling.
// [Pos] Story Workspace workflow run transport adapter.
// [Sync] 2026-08-06: stop probing the unavailable run-scoped SSE route; REST remains authoritative.
import { useEffect, useRef, useState } from 'react';
import {
  getWorkflowRun,
  type WorkflowRun,
} from '../api/storyWorkspaceApi';

export type WorkflowEventConnectionState = 'idle' | 'polling';

export interface UseWorkflowEventsOptions {
  workflowRunId?: string | null;
  enabled?: boolean;
  initialAggregateVersion?: number;
  pollIntervalMs?: number;
  onSnapshot?: (run: WorkflowRun) => void;
}

export interface UseWorkflowEventsResult {
  connectionState: WorkflowEventConnectionState;
  lastEventId: string | null;
  aggregateVersion: number;
}

export function useWorkflowEvents({
  workflowRunId,
  enabled = true,
  initialAggregateVersion = 0,
  pollIntervalMs = 5000,
  onSnapshot,
}: UseWorkflowEventsOptions): UseWorkflowEventsResult {
  const [connectionState, setConnectionState] = useState<WorkflowEventConnectionState>('idle');
  const [lastEventId] = useState<string | null>(null);
  const [aggregateVersion, setAggregateVersion] = useState(initialAggregateVersion);
  const onSnapshotRef = useRef(onSnapshot);

  useEffect(() => {
    onSnapshotRef.current = onSnapshot;
  }, [onSnapshot]);

  useEffect(() => {
    if (!workflowRunId || !enabled) return undefined;

    let closed = false;
    let latestAggregateVersion = initialAggregateVersion;

    const pollSnapshot = async () => {
      try {
        const snapshot = await getWorkflowRun(workflowRunId);
        if (closed) return;
        latestAggregateVersion = Math.max(latestAggregateVersion, snapshot.status_version);
        setAggregateVersion(latestAggregateVersion);
        onSnapshotRef.current?.(snapshot);
      } catch {
        // Keep the last authoritative snapshot and retry on the next interval.
      }
    };

    setConnectionState('polling');
    void pollSnapshot();
    const pollingIntervalId = window.setInterval(() => {
      void pollSnapshot();
    }, Math.max(5000, pollIntervalMs));

    return () => {
      closed = true;
      window.clearInterval(pollingIntervalId);
    };
  }, [enabled, initialAggregateVersion, pollIntervalMs, workflowRunId]);

  return { connectionState, lastEventId, aggregateVersion };
}
