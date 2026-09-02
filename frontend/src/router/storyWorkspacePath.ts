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
// [Sync] 2026-08-14: parse stable Deck/Agent Chat intent; neither parameter
//                    declares or authorizes Dream mode.
// [Sync] 2026-08-16: add the canonical Settings / Work route while retaining resource/plugin deep links.
// [Sync] 2026-08-31: register the run-independent creation guide as a static route.
// [Sync] 2026-08-31: authenticated root resolves to canonical Chat; unsupported historical prefixes are not routes.
// [Sync] 2026-09-02: carry one opaque Episode UID in the Execution query string.

export type StoryWorkspaceStaticRoute =
  | 'dream'
  | 'writing'
  | 'timeline'
  | 'analysis'
  | 'chat'
  | 'stories'
  | 'characters'
  | 'scenes'
  | 'decks'
  | 'creation-guide'
  | 'subscription'
  | 'settings'
  | 'settings-work'
  | 'settings-resources'
  | 'settings-plugins'
  | 'settings-model'
  | 'settings-about';

export type StoryWorkspaceParameterizedRoute = 'episode-review' | 'run-execution' | 'dream-legacy';

export type StoryWorkspaceRoute = StoryWorkspaceStaticRoute | StoryWorkspaceParameterizedRoute;

export const STORY_WORKSPACE_PATHS: Record<StoryWorkspaceStaticRoute, string> = {
  dream: '/story-workspace/dream',
  writing: '/story-workspace/writing',
  timeline: '/story-workspace/timeline',
  analysis: '/story-workspace/analysis',
  chat: '/story-workspace/chat',
  stories: '/story-workspace/stories',
  characters: '/story-workspace/characters',
  scenes: '/story-workspace/scenes',
  decks: '/story-workspace/decks',
  'creation-guide': '/story-workspace/creation-guide',
  subscription: '/story-workspace/subscription',
  settings: '/story-workspace/settings',
  'settings-work': '/story-workspace/settings/work',
  'settings-resources': '/story-workspace/settings/resources',
  'settings-plugins': '/story-workspace/settings/plugins',
  'settings-model': '/story-workspace/settings/model',
  'settings-about': '/story-workspace/settings/about',
};

/**
 * Parameterized route patterns (C10-①). `:param` segments capture one path
 * segment; every other segment matches literally. Keys are the route names.
 */
export const STORY_WORKSPACE_ROUTE_PATTERNS: Record<StoryWorkspaceParameterizedRoute, string> = {
  'episode-review': '/story-workspace/episodes/:storyWorkspaceEpisodeId/review',
  'run-execution': '/story-workspace/runs/:storyWorkspaceRunId/execution',
  'dream-legacy': '/story-workspace/runs/:storyWorkspaceRunId',
};

export interface StoryWorkspaceRouteMatch {
  canonicalPath: string;
  route: StoryWorkspaceRoute;
  /** Captured `:param` values (decoded); empty for static routes. */
  params: Record<string, string>;
  /** Parsed query string (C10-③); never null so callers can read uniformly. */
  query: URLSearchParams;
}

export interface StoryWorkspaceNavigationTarget {
  href: string;
  match: StoryWorkspaceRouteMatch;
  /** Legacy routes are URL normalization, never a new browser-history entry. */
  replace: boolean;
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
    normalizedPath === '/'
  ) {
    return {
      canonicalPath: STORY_WORKSPACE_PATHS.chat,
      route: 'chat',
      params: {},
      query,
    };
  }

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
      if (route === 'dream-legacy' && !/^run_[0-9a-f]{32}$/.test(params.storyWorkspaceRunId)) {
        continue;
      }
      return { canonicalPath: normalizedPath, route, params, query };
    }
  }

  return null;
}

/** Concrete execution page path (canonical form of the run-execution route). */
export function storyWorkspaceExecutionPath(storyWorkspaceRunId: string): string {
  return `/story-workspace/runs/${encodeURIComponent(storyWorkspaceRunId)}/execution`;
}

/** Execution path for either the Episode index or one stable registry member. */
export function storyWorkspaceExecutionEpisodePath(
  storyWorkspaceRunId: string,
  storyWorkspaceEpisodeId?: string | null,
): string {
  const path = storyWorkspaceExecutionPath(storyWorkspaceRunId);
  if (!storyWorkspaceEpisodeId) return path;
  const query = new URLSearchParams({ episode: storyWorkspaceEpisodeId });
  return `${path}?${query.toString()}`;
}

/** Convert a former run URL into the one Dream workbench route without new state ownership. */
export function storyWorkspaceDreamLegacyRunRedirectPath(
  storyWorkspaceRunId: string,
  search = '',
): string {
  const query = new URLSearchParams(search);
  query.set('run', storyWorkspaceRunId);
  return `${STORY_WORKSPACE_PATHS.dream}?${query.toString()}`;
}

/** Remove only an untrusted deep-link run while retaining harmless navigation intent such as Deck. */
export function storyWorkspaceDreamPathWithoutRun(search = ''): string {
  const query = new URLSearchParams(search);
  query.delete('run');
  const suffix = query.toString();
  return suffix ? `?${suffix}` : '';
}

/** A Dream page may use only the actor-scoped run read that completed successfully. */
export function storyWorkspaceDreamResolvedRunId(
  run: { workflow_run_id?: unknown } | null | undefined,
): string | null {
  return typeof run?.workflow_run_id === 'string' && run.workflow_run_id.trim()
    ? run.workflow_run_id
    : null;
}

/** Resolve a Story Workspace navigation request before the React router mutates browser history. */
export function storyWorkspaceNavigationTarget(
  pathname: string,
  search = '',
): StoryWorkspaceNavigationTarget | null {
  let match = resolveStoryWorkspacePath(pathname, search);
  if (!match) return null;
  let nextSearch = search;
  let replace = false;
  if (match.route === 'dream-legacy') {
    const redirect = storyWorkspaceDreamLegacyRunRedirectPath(
      match.params.storyWorkspaceRunId,
      search,
    );
    const questionMark = redirect.indexOf('?');
    const nextPathname = questionMark >= 0 ? redirect.slice(0, questionMark) : redirect;
    nextSearch = questionMark >= 0 ? redirect.slice(questionMark) : '';
    match = resolveStoryWorkspacePath(nextPathname, nextSearch);
    if (!match) return null;
    replace = true;
  }
  return { href: match.canonicalPath + nextSearch, match, replace };
}

/** Write a previously-resolved in-app navigation through the appropriate History API method. */
export function storyWorkspaceCommitNavigation(
  history: Pick<History, 'pushState' | 'replaceState'>,
  state: unknown,
  href: string,
  replace: boolean,
): void {
  if (replace) {
    history.replaceState(state, '', href);
    return;
  }
  history.pushState(state, '', href);
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

/** Read the opaque Episode selection; registry membership remains server-owned. */
export function readStoryWorkspaceEpisodeParam(query: URLSearchParams): string | null {
  const episode = query.get('episode');
  return episode && episode.trim() ? episode : null;
}

/** Optional Deck preselection is navigation intent only; it never authorizes a run. */
export function readStoryWorkspaceDeckParam(query: URLSearchParams): string | null {
  const deck = query.get('deck');
  return deck && deck.trim() ? deck : null;
}

/** Optional Agent preselection stays subordinate to the server-resolved Deck. */
export function readStoryWorkspaceAgentParam(query: URLSearchParams): string | null {
  const agent = query.get('agent');
  return agent && agent.trim() ? agent : null;
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

/** Legacy review belongs only to resource-management routes, never Dream or Decks surfaces. */
export function storyWorkspaceAllowsLegacyReviewPanel(
  match: StoryWorkspaceRouteMatch,
): boolean {
  if (
    match.route === 'dream'
    || match.route === 'episode-review'
    || match.route === 'run-execution'
    || match.route === 'decks'
    || match.route === 'creation-guide'
    || match.route === 'writing'
    || match.route === 'timeline'
    || match.route === 'analysis'
    || match.route === 'chat'
    || match.route === 'subscription'
    || match.route === 'settings'
    || match.route === 'settings-work'
    || match.route === 'settings-resources'
    || match.route === 'settings-plugins'
    || match.route === 'settings-model'
    || match.route === 'settings-about'
  ) return false;
  return storyWorkspaceDreamStageForRoute(match) === null;
}
