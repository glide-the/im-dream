// [Input] Browser pathname/search strings.
// [Output] Pure story-workspace route resolution seams: static route table,
//          parameterized route patterns (C10-①/②), URLSearchParams query
//          parsing (C10-③), canonical path builders, and the unified ?run=
//          deep-link param seam (absorbing Task 4 R2's local parsing).
// [Pos] Story Workspace state-router path seams (Task 5 Step 0); the React
//       adapter in story-workspace.tsx consumes these and owns all
//       window/history side effects (C10-④/⑤).
// [Sync] 2026-08-04: initial implementation. Parameterized matching compares
//                    path segments literally outside `:param` slots; canonical
//                    builders stay byte-identical with the surface-link deep
//                    links (Task 4 handoff note).

export type StoryWorkspaceStaticRoute = 'dream' | 'stories' | 'characters' | 'scenes';

export type StoryWorkspaceParameterizedRoute = 'episode-review' | 'run-execution';

export type StoryWorkspaceRoute = StoryWorkspaceStaticRoute | StoryWorkspaceParameterizedRoute;

export const STORY_WORKSPACE_PATHS: Record<StoryWorkspaceStaticRoute, string> = {
  dream: '/story-workspace/dream',
  stories: '/story-workspace/stories',
  characters: '/story-workspace/characters',
  scenes: '/story-workspace/scenes',
};

/**
 * Parameterized route patterns (C10-①). `:param` segments capture one path
 * segment; every other segment matches literally. Keys are the route names.
 */
export const STORY_WORKSPACE_ROUTE_PATTERNS: Record<StoryWorkspaceParameterizedRoute, string> = {
  'episode-review': '/story-workspace/episodes/:storyWorkspaceEpisodeId/review',
  'run-execution': '/story-workspace/runs/:storyWorkspaceRunId/execution',
};

export interface StoryWorkspaceRouteMatch {
  canonicalPath: string;
  route: StoryWorkspaceRoute;
  /** Captured `:param` values (decoded); empty for static routes. */
  params: Record<string, string>;
  /** Parsed query string (C10-③); never null so callers can read uniformly. */
  query: URLSearchParams;
}

export type StoryWorkspaceDreamRouteStage = 'characters' | 'scenes';

export function trimStoryWorkspaceTrailingSlash(pathname: string): string {
  if (pathname === '/') return pathname;
  return pathname.replace(/\/+$/, '');
}

/**
 * Match a parameterized pattern against a pathname via prefix segment
 * comparison (C10-②). `:param` segments capture exactly one non-empty segment
 * (URI-decoded); segment counts must be equal. Returns null on any mismatch.
 */
export function matchStoryWorkspaceRoutePattern(
  pattern: string,
  pathname: string,
): Record<string, string> | null {
  const patternSegments = trimStoryWorkspaceTrailingSlash(pattern).split('/').filter(Boolean);
  const pathSegments = trimStoryWorkspaceTrailingSlash(pathname).split('/').filter(Boolean);
  if (patternSegments.length !== pathSegments.length) return null;

  const params: Record<string, string> = {};
  for (let index = 0; index < patternSegments.length; index += 1) {
    const patternSegment = patternSegments[index];
    const pathSegment = pathSegments[index];
    if (patternSegment.startsWith(':')) {
      if (!pathSegment) return null;
      let decoded = pathSegment;
      try {
        decoded = decodeURIComponent(pathSegment);
      } catch {
        // Malformed encodings keep their raw segment; the route still matches
        // and downstream readers see the verbatim value.
      }
      params[patternSegment.slice(1)] = decoded;
    } else if (patternSegment !== pathSegment) {
      return null;
    }
  }
  return params;
}

/**
 * Resolve a browser location into a story-workspace route match. Static
 * routes keep their pre-C10 exact-match semantics; parameterized routes fill
 * `params`. `search` is parsed into `query` (leading `?` optional).
 */
export function resolveStoryWorkspacePath(
  pathname: string,
  search = '',
): StoryWorkspaceRouteMatch | null {
  const normalizedPath = trimStoryWorkspaceTrailingSlash(pathname);
  const query = new URLSearchParams(search);

  if (
    normalizedPath === '/story-workspace'
    || normalizedPath === '/story-workspace/dashboard'
    || normalizedPath === STORY_WORKSPACE_PATHS.dream
  ) {
    return {
      canonicalPath: STORY_WORKSPACE_PATHS.dream,
      route: 'dream',
      params: {},
      query,
    };
  }

  const staticRoute = (Object.keys(STORY_WORKSPACE_PATHS) as StoryWorkspaceStaticRoute[])
    .find((candidate) => STORY_WORKSPACE_PATHS[candidate] === normalizedPath);
  if (staticRoute) {
    return {
      canonicalPath: STORY_WORKSPACE_PATHS[staticRoute],
      route: staticRoute,
      params: {},
      query,
    };
  }

  for (const route of Object.keys(STORY_WORKSPACE_ROUTE_PATTERNS) as StoryWorkspaceParameterizedRoute[]) {
    const params = matchStoryWorkspaceRoutePattern(STORY_WORKSPACE_ROUTE_PATTERNS[route], normalizedPath);
    if (params) {
      return { canonicalPath: normalizedPath, route, params, query };
    }
  }

  return null;
}

/** Concrete execution page path (canonical form of the run-execution route). */
export function storyWorkspaceExecutionPath(storyWorkspaceRunId: string): string {
  return `/story-workspace/runs/${encodeURIComponent(storyWorkspaceRunId)}/execution`;
}

/** Concrete episode review path (canonical form of the episode-review route). */
export function storyWorkspaceEpisodeReviewPath(storyWorkspaceEpisodeId: string): string {
  return `/story-workspace/episodes/${encodeURIComponent(storyWorkspaceEpisodeId)}/review`;
}

/**
 * Unified `?run=` deep-link param seam (C10-③; absorbs Task 4 R2's local
 * URLSearchParams parsing in useRunDeepLink). Returns null for absent/blank
 * values.
 */
export function parseStoryWorkspaceRunParam(search: string): string | null {
  if (!search) return null;
  const run = new URLSearchParams(search).get('run');
  return run && run.trim() ? run : null;
}

/** Read the unified run param from an already-parsed match query. */
export function readStoryWorkspaceRunParam(query: URLSearchParams): string | null {
  const run = query.get('run');
  return run && run.trim() ? run : null;
}

/** Optional Deck preselection is navigation intent only; it never authorizes a run. */
export function readStoryWorkspaceDeckParam(query: URLSearchParams): string | null {
  const deck = query.get('deck');
  return deck && deck.trim() ? deck : null;
}

/** Run-bound asset routes reuse the Dream file surface at the matching stage. */
export function storyWorkspaceDreamStageForRoute(
  match: StoryWorkspaceRouteMatch,
): StoryWorkspaceDreamRouteStage | null {
  if (!readStoryWorkspaceRunParam(match.query)) return null;
  if (match.route === 'characters') return 'characters';
  if (match.route === 'scenes') return 'scenes';
  return null;
}

/** Legacy review belongs only to resource-management routes, never Dream surfaces. */
export function storyWorkspaceAllowsLegacyReviewPanel(
  match: StoryWorkspaceRouteMatch,
): boolean {
  if (
    match.route === 'dream'
    || match.route === 'episode-review'
    || match.route === 'run-execution'
  ) return false;
  return storyWorkspaceDreamStageForRoute(match) === null;
}
