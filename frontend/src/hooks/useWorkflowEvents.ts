// [Input] A workflow run id, the server event stream, and the run snapshot endpoint.
// [Output] Deduplicated, monotonically ordered workflow events with polling fallback.
// [Pos] Story Workspace workflow event transport adapter.
import { useEffect, useRef, useState } from 'react';
import {
  getWorkflowRun,
  workflowRunEventsUrl,
  type WorkflowRun,
  type WorkflowRunEvent,
} from '../api/storyWorkspaceApi';

export type WorkflowEventConnectionState = 'idle' | 'connecting' | 'live' | 'polling';

export interface UseWorkflowEventsOptions {
  workflowRunId?: string | null;
  enabled?: boolean;
  initialAggregateVersion?: number;
  pollIntervalMs?: number;
  onEvent?: (event: WorkflowRunEvent) => void;
  onSnapshot?: (run: WorkflowRun) => void;
}

export interface UseWorkflowEventsResult {
  connectionState: WorkflowEventConnectionState;
  lastEventId: string | null;
  aggregateVersion: number;
}

function isWorkflowRunEvent(value: unknown): value is WorkflowRunEvent {
  if (!value || typeof value !== 'object') return false;
  const event = value as Partial<WorkflowRunEvent>;
  return typeof event.event_id === 'string'
    && (typeof event.aggregate_id === 'string' || typeof event.workflow_run_id === 'string')
    && typeof event.aggregate_version === 'number'
    && Number.isInteger(event.aggregate_version);
}

export function useWorkflowEvents({
  workflowRunId,
  enabled = true,
  initialAggregateVersion = 0,
  pollIntervalMs = 5000,
  onEvent,
  onSnapshot,
}: UseWorkflowEventsOptions): UseWorkflowEventsResult {
  const [connectionState, setConnectionState] = useState<WorkflowEventConnectionState>('idle');
  const [lastEventId, setLastEventId] = useState<string | null>(null);
  const [aggregateVersion, setAggregateVersion] = useState(initialAggregateVersion);
  const onEventRef = useRef(onEvent);
  const onSnapshotRef = useRef(onSnapshot);

  useEffect(() => {
    onEventRef.current = onEvent;
    onSnapshotRef.current = onSnapshot;
  }, [onEvent, onSnapshot]);

  useEffect(() => {
    if (!workflowRunId || !enabled) return undefined;

    let closed = false;
    let pollingIntervalId: number | null = null;
    const seenEventIds = new Set<string>();
    let latestAggregateVersion = initialAggregateVersion;
    const source = new EventSource(workflowRunEventsUrl(workflowRunId), {
      withCredentials: true,
    });

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

    const startPolling = () => {
      if (closed || pollingIntervalId !== null) return;
      setConnectionState('polling');
      void pollSnapshot();
      pollingIntervalId = window.setInterval(() => {
        void pollSnapshot();
      }, pollIntervalMs);
    };

    setConnectionState('connecting');
    source.onopen = () => {
      if (!closed) setConnectionState('live');
    };
    source.onmessage = (message) => {
      if (closed) return;
      let parsed: unknown;
      try {
        parsed = JSON.parse(message.data) as unknown;
      } catch {
        return;
      }
      if (!isWorkflowRunEvent(parsed)) return;
      const eventRunId = parsed.workflow_run_id ?? parsed.aggregate_id;
      if (eventRunId !== workflowRunId) return;
      if (seenEventIds.has(parsed.event_id)) return;
      seenEventIds.add(parsed.event_id);
      if (parsed.aggregate_version <= latestAggregateVersion) return;

      latestAggregateVersion = parsed.aggregate_version;
      setAggregateVersion(parsed.aggregate_version);
      setLastEventId(parsed.event_id);
      onEventRef.current?.({ ...parsed, workflow_run_id: eventRunId });
    };
    source.onerror = () => {
      source.close();
      startPolling();
    };

    return () => {
      closed = true;
      source.close();
      if (pollingIntervalId !== null) window.clearInterval(pollingIntervalId);
    };
  }, [enabled, initialAggregateVersion, pollIntervalMs, workflowRunId]);

  return { connectionState, lastEventId, aggregateVersion };
}
