import { useCallback } from 'react';
import type { StoryWorkspaceScene, StoryWorkspaceSceneQuery } from './contracts';
import { useStoryWorkspaceList } from './useStoryWorkspaceList';

export function useScenes(query: StoryWorkspaceSceneQuery = {}) {
  const appendParams = useCallback((params: URLSearchParams) => {
    if (query.storyId) params.set('story_id', query.storyId);
  }, [query.storyId]);

  return useStoryWorkspaceList<StoryWorkspaceScene>(
    '/api/story-workspace/scenes',
    query,
    appendParams,
  );
}
