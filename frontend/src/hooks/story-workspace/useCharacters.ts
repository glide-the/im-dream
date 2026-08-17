import type { StoryWorkspaceCharacter, StoryWorkspaceListQuery } from './contracts';
import { useStoryWorkspaceList } from './useStoryWorkspaceList';

export function useCharacters(query: StoryWorkspaceListQuery = {}) {
  return useStoryWorkspaceList<StoryWorkspaceCharacter>(
    '/api/story-workspace/characters',
    query,
  );
}
