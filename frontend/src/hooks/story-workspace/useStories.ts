import { useCallback } from 'react';
import type { StoryWorkspaceStory, StoryWorkspaceStoryQuery } from './contracts';
import { useStoryWorkspaceList } from './useStoryWorkspaceList';

export function useStories(query: StoryWorkspaceStoryQuery = {}) {
  const appendParams = useCallback((params: URLSearchParams) => {
    if (query.type?.length) params.set('type', query.type.join(','));
  }, [query.type]);

  return useStoryWorkspaceList<StoryWorkspaceStory>(
    '/api/story-workspace/stories',
    query,
    appendParams,
  );
}
