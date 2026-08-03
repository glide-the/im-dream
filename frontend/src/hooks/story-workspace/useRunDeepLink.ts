// [Input] window.location.search (?run= deep link) + the existing actor-scoped
//         GET /api/story-workspace/workflow-runs/{id} read.
// [Output] useRunDeepLink(enabled) → {run, notice, dismissNotice}: a resolved
//          deep-linked run as the initial Dream selection, or a toast notice
//          when the run is missing/foreign (design_004 §4.3).
// [Pos] story-workspace hooks node - Dream page run deep-link seam (Task 4
//       Step 5, review annotation R2)
// [Sync] 2026-08-04: initial implementation. Query parsing is intentionally
//                    local URLSearchParams; Task 5 Step 0 unifies it into the
//                    story-workspace router. Deep links only do initial
//                    positioning — the resolved run never freezes selection
//                    (stale-review semantics stay with design_003).

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getWorkflowRun,
  type WorkflowRun,
} from '../../api/storyWorkspaceApi';

/**
 * Extract the `?run=` value from a location search string. Local
 * URLSearchParams parsing per Task 4 R2; returns null for absent/blank values.
 */
export function parseRunDeepLinkParam(search: string): string | null {
  if (!search) return null;
  const run = new URLSearchParams(search).get('run');
  return run && run.trim() ? run : null;
}

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
  search: string,
  options: ResolveRunDeepLinkOptions = {},
): Promise<StoryWorkspaceRunDeepLinkResolution> {
  const runId = parseRunDeepLinkParam(search);
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
 * Resolve the Dream page `?run=` deep link exactly once per mount (initial
 * positioning only — later selection changes are not frozen to this run).
 * `enabled` gates resolution to the dream route; without a usable `?run=`
 * value the hook stays inert and the default view is preserved.
 */
export function useRunDeepLink(enabled: boolean): StoryWorkspaceRunDeepLinkState {
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const resolvedRef = useRef(false);

  useEffect(() => {
    if (!enabled || resolvedRef.current) return;
    resolvedRef.current = true;

    let cancelled = false;
    void resolveRunDeepLink(window.location.search).then((resolution) => {
      if (cancelled) return;
      if (resolution.status === 'resolved') {
        setRun(resolution.run);
      } else if (resolution.status === 'missing') {
        setNotice(`链接指向的运行 ${resolution.runId} 不存在或无权查看，已回退到默认视图。`);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  const dismissNotice = useCallback(() => setNotice(null), []);

  return { run, notice, dismissNotice };
}
