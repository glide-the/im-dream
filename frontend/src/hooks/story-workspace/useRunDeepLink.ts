// [Input] Router-parsed `?run=` deep-link param (Task 5 Step 0 unified query
//         parsing) + the existing actor-scoped GET
//         /api/story-workspace/workflow-runs/{id} read.
// [Output] useRunDeepLink(enabled, runId) → {run, notice, dismissNotice}: a
//          resolved deep-linked run as the initial Dream selection, or a toast
//          notice when the run is missing/foreign (design_004 §4.3).
// [Pos] story-workspace hooks node - Dream page run deep-link seam (Task 4
//       Step 5; Task 5 Step 0 absorbed query parsing into the router)
// [Sync] 2026-08-04: Task 5 Step 0 — the hook no longer reads
//                    window.location.search; the router parses `?run=` via
//                    storyWorkspacePath.ts and passes it in. Route switches
//                    (enabled → false) now clear the run and the notice
//                    (Task 4 review leftover: notice persisted across routes).
//                    Deep links only do initial positioning — the resolved run
//                    never freezes selection (stale-review semantics stay with
//                    design_003).

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getWorkflowRun,
  type WorkflowRun,
} from '../../api/storyWorkspaceApi';

export type StoryWorkspaceRunDeepLinkResolution =
  | { status: 'none' }
  | { status: 'resolved'; run: WorkflowRun }
  | { status: 'missing'; runId: string };

export interface ResolveRunDeepLinkOptions {
  getRun?: (runId: string) => Promise<WorkflowRun>;
}

/**
 * Resolve a `?run=` deep link against the actor-scoped run read: owned runs
 * resolve as the initial selection (replacing the default); unknown/foreign
 * runs (the backend read is actor-scoped, so both surface as failures) degrade
 * to `missing` so the caller can toast and fall back to the default view.
 */
export async function resolveRunDeepLink(
  runId: string | null,
  options: ResolveRunDeepLinkOptions = {},
): Promise<StoryWorkspaceRunDeepLinkResolution> {
  if (!runId) return { status: 'none' };

  const getRun = options.getRun ?? getWorkflowRun;
  try {
    const run = await getRun(runId);
    return run && run.workflow_run_id
      ? { status: 'resolved', run }
      : { status: 'missing', runId };
  } catch {
    return { status: 'missing', runId };
  }
}

export interface StoryWorkspaceRunDeepLinkState {
  /** The deep-linked run selected as initial context; null = default view. */
  run: WorkflowRun | null;
  /** Toast text when the deep-linked run is missing or not viewable. */
  notice: string | null;
  dismissNotice: () => void;
}

/**
 * Resolve the Dream page `?run=` deep link once per distinct run id (initial
 * positioning only — later selection changes are not frozen to this run).
 * `enabled` gates resolution to routes that surface the Dream review flow;
 * leaving such a route clears both the resolved run and any notice (Task 4
 * review leftover). Without a usable run id the hook stays inert and the
 * default view is preserved.
 */
export function useRunDeepLink(
  enabled: boolean,
  runId: string | null,
): StoryWorkspaceRunDeepLinkState {
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const resolvedKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      resolvedKeyRef.current = null;
      setRun(null);
      setNotice(null);
      return;
    }
    if (!runId || resolvedKeyRef.current === runId) return;
    resolvedKeyRef.current = runId;

    let cancelled = false;
    void resolveRunDeepLink(runId).then((resolution) => {
      if (cancelled) return;
      if (resolution.status === 'resolved') {
        setRun(resolution.run);
        setNotice(null);
      } else if (resolution.status === 'missing') {
        setRun(null);
        setNotice(`链接指向的运行 ${resolution.runId} 不存在或无权查看，已回退到默认视图。`);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [enabled, runId]);

  const dismissNotice = useCallback(() => setNotice(null), []);

  return { run, notice, dismissNotice };
}
