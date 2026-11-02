// [Input] Authenticated Story Workspace re-entry endpoint.
// [Output] Durable, server-ordered Dream run collection for the canonical workbench.
// [Pos] Dream re-entry adapter; it never reads browser persistence as run truth.
// [Sync] 2026-10-27: permit the owning view to omit the mobile-excluded Dream collection read.

import { useCallback, useEffect, useState } from 'react';
import {
  storyWorkspaceDreamRunsEndpoint,
  storyWorkspaceFetchDreamRuns,
  storyWorkspaceParseDreamRuns,
} from '../../api/storyWorkspaceApi';
import type { StoryWorkspaceDreamReentryCollection } from './contracts';

export { storyWorkspaceDreamRunsEndpoint, storyWorkspaceParseDreamRuns };

export interface StoryWorkspaceDreamRunsState {
  readonly data: StoryWorkspaceDreamReentryCollection | null;
  readonly error: Error | null;
  readonly isLoading: boolean;
  readonly refetch: () => void;
}

export function useStoryWorkspaceDreamRuns(enabled = true): StoryWorkspaceDreamRunsState {
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState<StoryWorkspaceDreamReentryCollection | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refetch = useCallback(() => setRefresh((value) => value + 1), []);

  useEffect(() => {
    if (!enabled) { setIsLoading(false); return; }
    let active = true;
    const controller = new AbortController();
    setIsLoading(true);
    void storyWorkspaceFetchDreamRuns({ signal: controller.signal }).then((next) => {
      if (!active) return;
      setData(next);
      setError(null);
    }).catch((reason: unknown) => {
      if (!active) return;
      setError(reason instanceof Error ? reason : new Error('Dream 列表暂时无法恢复。'));
    }).finally(() => {
      if (active) setIsLoading(false);
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [refresh, enabled]);

  return { data, error, isLoading, refetch };
}
