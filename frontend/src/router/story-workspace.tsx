// [Input] Browser location/history, Story Workspace layout/sidebar, and route page skeletons.
// [Output] Resolve canonical Story Workspace paths and render synchronized route content.
// [Pos] Story Workspace state-router adapter for the existing App architecture.
/* eslint-disable react-refresh/only-export-components -- This explicit route module intentionally exports route helpers for App integration. */
import { useCallback, useEffect, useState } from 'react';
import { StoryWorkspaceLayout } from '../components/story-workspace/layout/StoryWorkspaceLayout';
import { StoryWorkspaceSidebar } from '../components/story-workspace/layout/StoryWorkspaceSidebar';
import {
  StoryWorkspaceCharactersPage,
  StoryWorkspaceDreamPage,
  StoryWorkspaceScenesPage,
  StoryWorkspaceStoriesPage,
} from '../pages/story-workspace';

export type StoryWorkspaceRoute = 'dream' | 'stories' | 'characters' | 'scenes';

export const STORY_WORKSPACE_PATHS: Record<StoryWorkspaceRoute, string> = {
  dream: '/story-workspace/dream',
  stories: '/story-workspace/stories',
  characters: '/story-workspace/characters',
  scenes: '/story-workspace/scenes',
};

export interface StoryWorkspaceRouteMatch {
  canonicalPath: string;
  route: StoryWorkspaceRoute;
}

function trimTrailingSlash(pathname: string) {
  if (pathname === '/') return pathname;
  return pathname.replace(/\/+$/, '');
}

export function resolveStoryWorkspacePath(pathname: string): StoryWorkspaceRouteMatch | null {
  const normalizedPath = trimTrailingSlash(pathname);

  if (
    normalizedPath === '/story-workspace'
    || normalizedPath === '/story-workspace/dashboard'
    || normalizedPath === STORY_WORKSPACE_PATHS.dream
  ) {
    return { canonicalPath: STORY_WORKSPACE_PATHS.dream, route: 'dream' };
  }

  const route = (Object.keys(STORY_WORKSPACE_PATHS) as StoryWorkspaceRoute[])
    .find((candidate) => STORY_WORKSPACE_PATHS[candidate] === normalizedPath);

  return route ? { canonicalPath: STORY_WORKSPACE_PATHS[route], route } : null;
}

function storyWorkspaceHistoryState() {
  const currentState = window.history.state;
  const safeCurrentState = currentState && typeof currentState === 'object'
    ? currentState
    : {};

  return { ...safeCurrentState, inkDreamView: 'story-workspace' };
}

function replaceWithCanonicalPath(canonicalPath: string) {
  const canonicalUrl = new URL(window.location.href);
  canonicalUrl.pathname = canonicalPath;
  window.history.replaceState(storyWorkspaceHistoryState(), '', canonicalUrl);
}

function renderStoryWorkspaceRoute(route: StoryWorkspaceRoute) {
  switch (route) {
    case 'stories':
      return <StoryWorkspaceStoriesPage />;
    case 'characters':
      return <StoryWorkspaceCharactersPage />;
    case 'scenes':
      return <StoryWorkspaceScenesPage />;
    case 'dream':
    default:
      return <StoryWorkspaceDreamPage />;
  }
}

export interface StoryWorkspaceRouterProps {
  onOpenSettings: () => void;
}

export function StoryWorkspaceRouter({ onOpenSettings }: StoryWorkspaceRouterProps) {
  const initialMatch = resolveStoryWorkspacePath(window.location.pathname)
    ?? { canonicalPath: STORY_WORKSPACE_PATHS.dream, route: 'dream' as const };
  const [activeRoute, setActiveRoute] = useState<StoryWorkspaceRoute>(initialMatch.route);

  const syncFromLocation = useCallback(() => {
    const match = resolveStoryWorkspacePath(window.location.pathname);
    if (!match) return;

    if (trimTrailingSlash(window.location.pathname) !== match.canonicalPath) {
      replaceWithCanonicalPath(match.canonicalPath);
    }
    setActiveRoute(match.route);
  }, []);

  useEffect(() => {
    syncFromLocation();
    window.addEventListener('popstate', syncFromLocation);
    return () => window.removeEventListener('popstate', syncFromLocation);
  }, [syncFromLocation]);

  const handleNavigate = useCallback((path: string) => {
    const match = resolveStoryWorkspacePath(path);
    if (!match) return;

    if (window.location.pathname !== match.canonicalPath) {
      window.history.pushState(storyWorkspaceHistoryState(), '', match.canonicalPath);
    }
    setActiveRoute(match.route);
  }, []);

  const currentPath = STORY_WORKSPACE_PATHS[activeRoute];

  return (
    <StoryWorkspaceLayout
      defaultReviewPanelOpen={false}
      sidebar={(
        <StoryWorkspaceSidebar
          currentPath={currentPath}
          onNavigate={handleNavigate}
          onOpenSettings={onOpenSettings}
        />
      )}
    >
      {renderStoryWorkspaceRoute(activeRoute)}
    </StoryWorkspaceLayout>
  );
}
