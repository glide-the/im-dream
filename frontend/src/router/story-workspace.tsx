// [Input] Browser location/history, Story Workspace layout/sidebar, and route page skeletons.
// [Output] Resolve canonical Story Workspace paths and render synchronized route content.
// [Pos] Story Workspace state-router adapter for the existing App architecture.
// [Sync] 2026-08-04: Task 5 Step 0 (C10) — path resolution moved to the pure
//                    storyWorkspacePath.ts seams: parameterized routes
//                    (/runs/:storyWorkspaceRunId/execution, /episodes/:id/review),
//                    URLSearchParams query parsing, and query-retaining
//                    pushState/replaceState. The Dream ?run= deep link now
//                    consumes the router-parsed query (Task 4 R2 absorbed);
//                    route switches clear the deep-link notice (Task 4 review
//                    leftover), and the surface link button routes in-app via
//                    handleNavigate (no full-page load).
// [Sync] 2026-08-04: Dream routes project every selected run to the fixed
//                    story_workspace_dream context state; raw WorkflowRun
//                    statuses never reach WorkflowContextBar.
/* eslint-disable react-refresh/only-export-components -- This explicit route module intentionally exports route helpers for App integration. */
import { useCallback, useEffect, useState } from 'react';
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
  StoryWorkspaceExecutionPage,
  StoryWorkspaceScenesPage,
  StoryWorkspaceStoriesPage,
} from '../pages/story-workspace';
import {
  readStoryWorkspaceRunParam,
  readStoryWorkspaceDeckParam,
  resolveStoryWorkspacePath,
  storyWorkspaceAllowsLegacyReviewPanel,
  storyWorkspaceDreamStageForRoute,
  STORY_WORKSPACE_PATHS,
  trimStoryWorkspaceTrailingSlash,
  type StoryWorkspaceRoute,
  type StoryWorkspaceRouteMatch,
} from './storyWorkspacePath';
import { storyWorkspaceDreamWorkflowContext } from './storyWorkspaceDreamContext';

export {
  resolveStoryWorkspacePath,
  STORY_WORKSPACE_PATHS,
  storyWorkspaceEpisodeReviewPath,
  storyWorkspaceExecutionPath,
  STORY_WORKSPACE_ROUTE_PATTERNS,
} from './storyWorkspacePath';
export type { StoryWorkspaceRoute, StoryWorkspaceRouteMatch } from './storyWorkspacePath';

const STORY_WORKSPACE_SIDEBAR_COLLAPSED_KEY = 'ink-dream:story-workspace:sidebar-collapsed';

const DEFAULT_MATCH: StoryWorkspaceRouteMatch = {
  canonicalPath: STORY_WORKSPACE_PATHS.dream,
  route: 'dream',
  params: {},
  query: new URLSearchParams(),
};

function readStoryWorkspaceSidebarCollapsed() {
  try {
    return window.localStorage.getItem(STORY_WORKSPACE_SIDEBAR_COLLAPSED_KEY) === '1';
  } catch {
    return false;
  }
}

function storyWorkspaceHistoryState() {
  const currentState = window.history.state;
  const safeCurrentState = currentState && typeof currentState === 'object'
    ? currentState
    : {};

  return { ...safeCurrentState, inkDreamView: 'story-workspace' };
}

function replaceWithCanonicalPath(canonicalPath: string) {
  // The URL object keeps search/hash untouched (C10-④): canonicalization only
  // rewrites the pathname, so deep links (?run=) survive it.
  const canonicalUrl = new URL(window.location.href);
  canonicalUrl.pathname = canonicalPath;
  window.history.replaceState(storyWorkspaceHistoryState(), '', canonicalUrl);
}

/** Split an in-app href into pathname + search (query preserved, C10-⑤). */
function splitStoryWorkspaceHref(href: string): { pathname: string; search: string } {
  const queryIndex = href.indexOf('?');
  return queryIndex >= 0
    ? { pathname: href.slice(0, queryIndex), search: href.slice(queryIndex) }
    : { pathname: href, search: '' };
}

function renderStoryWorkspaceRoute(
  match: StoryWorkspaceRouteMatch,
  onReview: (selection: StoryWorkspaceReviewSelection) => void,
  refreshNonce: number,
  onNavigate: (path: string, notice?: string) => void,
) {
  const runId = readStoryWorkspaceRunParam(match.query);
  const initialDeckId = readStoryWorkspaceDeckParam(match.query);
  const dreamStage = storyWorkspaceDreamStageForRoute(match);
  switch (match.route) {
    case 'stories':
      return <StoryWorkspaceStoriesPage onReview={(story) => onReview({ resourceType: 'story', resourceId: story.id })} refreshNonce={refreshNonce} />;
    case 'characters':
      if (dreamStage) {
        return (
          <StoryWorkspaceDreamPage
            initialStage={dreamStage}
            initialDeckId={initialDeckId}
            onNavigate={onNavigate}
            runId={runId}
          />
        );
      }
      return <StoryWorkspaceCharactersPage onReview={(character) => onReview({ resourceType: 'character', resourceId: character.id })} refreshNonce={refreshNonce} />;
    case 'scenes':
      if (dreamStage) {
        return (
          <StoryWorkspaceDreamPage
            initialStage={dreamStage}
            initialDeckId={initialDeckId}
            onNavigate={onNavigate}
            runId={runId}
          />
        );
      }
      return <StoryWorkspaceScenesPage onReview={(scene) => onReview({ resourceType: 'scene', resourceId: scene.id })} refreshNonce={refreshNonce} />;
    case 'run-execution':
      return (
        <StoryWorkspaceExecutionPage
          key={match.params.storyWorkspaceRunId}
          onNavigate={onNavigate}
          runId={match.params.storyWorkspaceRunId}
        />
      );
    case 'episode-review':
    case 'dream':
    default:
      return (
        <StoryWorkspaceDreamPage
          initialDeckId={initialDeckId}
          onNavigate={onNavigate}
          runId={runId}
        />
      );
  }
}

export interface StoryWorkspaceRouterProps {
  onOpenSettings: () => void;
}

export function StoryWorkspaceRouter({ onOpenSettings }: StoryWorkspaceRouterProps) {
  const [activeMatch, setActiveMatch] = useState<StoryWorkspaceRouteMatch>(
    () => resolveStoryWorkspacePath(window.location.pathname, window.location.search) ?? DEFAULT_MATCH,
  );
  const [reviewSelection, setReviewSelection] = useState<StoryWorkspaceReviewSelection | null>(null);
  const [reviewSource, setReviewSource] = useState<StoryWorkspaceOutputReceipt | null>(null);
  const [reviewPanelOpen, setReviewPanelOpen] = useState(false);
  const [resourceRefreshNonce, setResourceRefreshNonce] = useState(0);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readStoryWorkspaceSidebarCollapsed);
  // One-shot notice carried by a navigation (e.g. the execution page Gate
  // redirect, §5.5); cleared by the next location sync.
  const [routeNotice, setRouteNotice] = useState<string | null>(null);

  const activeRoute: StoryWorkspaceRoute = activeMatch.route;
  const isDreamRoute = activeRoute === 'dream'
    || activeRoute === 'episode-review'
    || storyWorkspaceDreamStageForRoute(activeMatch) !== null;

  // Dream page ?run= deep link (design_004 §4.3): the router parses the query
  // (C10-③), the hook resolves it actor-scoped; initial positioning only —
  // the selected run is surfaced through the WorkflowContextBar mount and
  // never frozen. Leaving the Dream routes clears run + notice (Task 5).
  const runDeepLink = useRunDeepLink(
    isDreamRoute,
    isDreamRoute ? readStoryWorkspaceRunParam(activeMatch.query) : null,
  );

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
    setResourceRefreshNonce((value) => value + 1);
    if (!storyWorkspaceAllowsLegacyReviewPanel(activeMatch)) return;
    setReviewSource(receipt);
    setReviewSelection({ resourceType: 'story', resourceId: receipt.story_id });
    setReviewPanelOpen(true);
  }), [activeMatch]);

  const handleOpenReview = useCallback((selection: StoryWorkspaceReviewSelection) => {
    setReviewSource(null);
    setReviewSelection(selection);
    setReviewPanelOpen(true);
  }, []);

  const syncFromLocation = useCallback(() => {
    const match = resolveStoryWorkspacePath(window.location.pathname, window.location.search);
    if (!match) return;

    if (trimStoryWorkspaceTrailingSlash(window.location.pathname) !== match.canonicalPath) {
      replaceWithCanonicalPath(match.canonicalPath);
    }
    setActiveMatch(match);
    setRouteNotice(null);
  }, []);

  useEffect(() => {
    syncFromLocation();
    window.addEventListener('popstate', syncFromLocation);
    return () => window.removeEventListener('popstate', syncFromLocation);
  }, [syncFromLocation]);

  const handleNavigate = useCallback((path: string, notice?: string) => {
    const { pathname, search } = splitStoryWorkspaceHref(path);
    const match = resolveStoryWorkspacePath(pathname, search);
    if (!match) return;

    const target = match.canonicalPath + search;
    if (window.location.pathname + window.location.search !== target) {
      // pushState carries the query string (C10-⑤) — deep links survive
      // in-app navigation.
      window.history.pushState(storyWorkspaceHistoryState(), '', target);
    }
    setActiveMatch(match);
    setRouteNotice(notice ?? null);
  }, []);

  // DEC-030: the execution page keeps the Dream entry selected in the app
  // chrome (it is a Dream surface page, not a fifth sidebar entry).
  const currentPath = activeRoute in STORY_WORKSPACE_PATHS
    ? STORY_WORKSPACE_PATHS[activeRoute as keyof typeof STORY_WORKSPACE_PATHS]
    : STORY_WORKSPACE_PATHS.dream;

  return (
    <StoryWorkspaceLayout
      reviewPanel={storyWorkspaceAllowsLegacyReviewPanel(activeMatch) && reviewSelection ? (
        <StoryWorkspaceReviewDetail
          key={`${reviewSelection.resourceType}:${reviewSelection.resourceId}`}
          onChanged={() => setResourceRefreshNonce((value) => value + 1)}
          onSelectResource={(selection) => {
            setReviewSelection(selection);
            setReviewPanelOpen(true);
          }}
          onSurfaceLinkNavigate={handleNavigate}
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
      workflowContext={isDreamRoute
        ? null
        : storyWorkspaceDreamWorkflowContext(runDeepLink.run)}
    >
      {runDeepLink.notice && (
        <div className="story-workspace-deep-link-notice" role="status">
          <span>{runDeepLink.notice}</span>
          <button className="workflow-button" onClick={runDeepLink.dismissNotice} type="button">知道了</button>
        </div>
      )}
      {routeNotice && (
        <div className="story-workspace-deep-link-notice" role="status">
          <span>{routeNotice}</span>
          <button className="workflow-button" onClick={() => setRouteNotice(null)} type="button">知道了</button>
        </div>
      )}
      {renderStoryWorkspaceRoute(
        activeMatch,
        handleOpenReview,
        resourceRefreshNonce,
        handleNavigate,
      )}
    </StoryWorkspaceLayout>
  );
}
