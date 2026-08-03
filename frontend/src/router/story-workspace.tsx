// [Input] Browser location/history, Story Workspace layout/sidebar, and route page skeletons.
// [Output] Resolve canonical Story Workspace paths and render synchronized route content.
// [Pos] Story Workspace state-router adapter for the existing App architecture.
// [Sync] 2026-08-04: Task 4 Step 5 (R2) — resolve the Dream page ?run= deep
//                    link locally (URLSearchParams) and surface the resolved
//                    run via WorkflowContextBar; missing/foreign runs show a
//                    dismissible notice and fall back to the default view.
//                    Task 5 Step 0 unifies query parsing into this router.
/* eslint-disable react-refresh/only-export-components -- This explicit route module intentionally exports route helpers for App integration. */
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { StoryWorkspaceLayout } from '../components/story-workspace/layout/StoryWorkspaceLayout';
import {
  StoryWorkspaceReviewDetail,
  type StoryWorkspaceReviewSelection,
} from '../components/story-workspace/layout/StoryWorkspaceReviewDetail';
import { StoryWorkspaceSidebar } from '../components/story-workspace/layout/StoryWorkspaceSidebar';
import { useRunDeepLink } from '../hooks/story-workspace';
import {
  subscribeStoryWorkspaceOutput,
  type StoryWorkspaceOutputReceipt,
} from '../lib/story-workspace-events';
import {
  StoryWorkspaceCharactersPage,
  StoryWorkspaceDreamPage,
  StoryWorkspaceScenesPage,
  StoryWorkspaceStoriesPage,
} from '../pages/story-workspace';

export type StoryWorkspaceRoute = 'dream' | 'stories' | 'characters' | 'scenes';

const STORY_WORKSPACE_SIDEBAR_COLLAPSED_KEY = 'ink-dream:story-workspace:sidebar-collapsed';

function readStoryWorkspaceSidebarCollapsed() {
  try {
    return window.localStorage.getItem(STORY_WORKSPACE_SIDEBAR_COLLAPSED_KEY) === '1';
  } catch {
    return false;
  }
}

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

function renderStoryWorkspaceRoute(
  route: StoryWorkspaceRoute,
  dreamContent: ReactNode,
  onReview: (selection: StoryWorkspaceReviewSelection) => void,
  refreshNonce: number,
) {
  switch (route) {
    case 'stories':
      return <StoryWorkspaceStoriesPage onReview={(story) => onReview({ resourceType: 'story', resourceId: story.id })} refreshNonce={refreshNonce} />;
    case 'characters':
      return <StoryWorkspaceCharactersPage onReview={(character) => onReview({ resourceType: 'character', resourceId: character.id })} refreshNonce={refreshNonce} />;
    case 'scenes':
      return <StoryWorkspaceScenesPage onReview={(scene) => onReview({ resourceType: 'scene', resourceId: scene.id })} refreshNonce={refreshNonce} />;
    case 'dream':
    default:
      return <StoryWorkspaceDreamPage>{dreamContent}</StoryWorkspaceDreamPage>;
  }
}

export interface StoryWorkspaceRouterProps {
  onOpenSettings: () => void;
  dreamContent: ReactNode;
}

export function StoryWorkspaceRouter({ onOpenSettings, dreamContent }: StoryWorkspaceRouterProps) {
  const initialMatch = resolveStoryWorkspacePath(window.location.pathname)
    ?? { canonicalPath: STORY_WORKSPACE_PATHS.dream, route: 'dream' as const };
  const [activeRoute, setActiveRoute] = useState<StoryWorkspaceRoute>(initialMatch.route);
  const [reviewSelection, setReviewSelection] = useState<StoryWorkspaceReviewSelection | null>(null);
  const [reviewSource, setReviewSource] = useState<StoryWorkspaceOutputReceipt | null>(null);
  const [reviewPanelOpen, setReviewPanelOpen] = useState(false);
  const [resourceRefreshNonce, setResourceRefreshNonce] = useState(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readStoryWorkspaceSidebarCollapsed);

  // Dream page ?run= deep link (design_004 §4.3, Task 4 R2): local
  // URLSearchParams resolution, initial positioning only — the selected run is
  // surfaced through the existing WorkflowContextBar mount and never frozen.
  const runDeepLink = useRunDeepLink(activeRoute === 'dream');

  const handleToggleSidebarCollapse = useCallback(() => {
    setSidebarCollapsed((collapsed) => {
      const next = !collapsed;
      try {
        window.localStorage.setItem(STORY_WORKSPACE_SIDEBAR_COLLAPSED_KEY, next ? '1' : '0');
      } catch {
        // localStorage unavailable; collapse state simply stays session-local.
      }
      return next;
    });
  }, []);

  useEffect(() => subscribeStoryWorkspaceOutput((receipt) => {
    setReviewSource(receipt);
    setReviewSelection({ resourceType: 'story', resourceId: receipt.story_id });
    setReviewPanelOpen(true);
    setResourceRefreshNonce((value) => value + 1);
  }), []);

  const handleOpenReview = useCallback((selection: StoryWorkspaceReviewSelection) => {
    setReviewSource(null);
    setReviewSelection(selection);
    setReviewPanelOpen(true);
  }, []);

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
      reviewPanel={reviewSelection ? (
        <StoryWorkspaceReviewDetail
          key={`${reviewSelection.resourceType}:${reviewSelection.resourceId}`}
          onChanged={() => setResourceRefreshNonce((value) => value + 1)}
          onSelectResource={(selection) => {
            setReviewSelection(selection);
            setReviewPanelOpen(true);
          }}
          selection={reviewSelection}
          sourceReceipt={reviewSource}
        />
      ) : null}
      reviewPanelOpen={reviewPanelOpen}
      onReviewPanelOpenChange={setReviewPanelOpen}
      reviewPanelTitle="Agent 产出审阅"
      sidebar={(
        <StoryWorkspaceSidebar
          collapsed={sidebarCollapsed}
          currentPath={currentPath}
          onNavigate={handleNavigate}
          onOpenSettings={onOpenSettings}
          onToggleCollapse={handleToggleSidebarCollapse}
        />
      )}
      sidebarCollapsed={sidebarCollapsed}
      workflowContext={runDeepLink.run ? {
        state: runDeepLink.run.status,
        deckPluginDisplayName: runDeepLink.run.deck_plugin_display_name,
        deckPluginVersion: runDeepLink.run.deck_plugin_version,
        workflowRunId: runDeepLink.run.workflow_run_id,
        workflowSummary: runDeepLink.run.workflow_summary,
      } : null}
    >
      {runDeepLink.notice && (
        <div className="story-workspace-deep-link-notice" role="status">
          <span>{runDeepLink.notice}</span>
          <button className="workflow-button" onClick={runDeepLink.dismissNotice} type="button">知道了</button>
        </div>
      )}
      {renderStoryWorkspaceRoute(
        activeRoute,
        dreamContent,
        handleOpenReview,
        resourceRefreshNonce,
      )}
    </StoryWorkspaceLayout>
  );
}
