// [Input] Authenticated Story Workspace re-entry endpoint.
// [Output] Durable, server-ordered Dream run collection for the canonical workbench.
// [Pos] Dream re-entry adapter; it never reads browser persistence as run truth.

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

export function useStoryWorkspaceDreamRuns(): StoryWorkspaceDreamRunsState {
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState<StoryWorkspaceDreamReentryCollection | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refetch = useCallback(() => setRefresh((value) => value + 1), []);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    void storyWorkspaceFetchDreamRuns().then((next) => {
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
    };
  }, [refresh]);

  return { data, error, isLoading, refetch };
}
