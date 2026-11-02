// [Input] Read-only native host marker and canonical route matches.
// [Output] Mobile-only presentation policy and credential-free navigation state.
// [Pos] RN host integration; HTTP, permissions and business state retain their original modules.
import {resolveStoryWorkspacePath, storyWorkspaceDreamStageForRoute, STORY_WORKSPACE_PATHS} from '../router/storyWorkspacePath';

type NativeWindow = Window & {
  __INK_NATIVE_HOST__?: {framework?: string};
  webkit?: {messageHandlers?: {inkHostState?: {postMessage: (state: unknown) => void}}};
};

export function isReactNativeHost(): boolean {
  return typeof window !== 'undefined' && (window as NativeWindow).__INK_NATIVE_HOST__?.framework === 'react-native';
}

export function mobileHostPath(path: string): string {
  if (!isReactNativeHost()) return path;
  const url = new URL(path, window.location.origin);
  if (url.origin !== window.location.origin) return STORY_WORKSPACE_PATHS.chat;
  const match = resolveStoryWorkspacePath(url.pathname, url.search);
  if (!match || ['dream', 'creation-guide', 'run-execution', 'episode-review', 'dream-legacy'].includes(match.route)
      || storyWorkspaceDreamStageForRoute(match) !== null) return STORY_WORKSPACE_PATHS.chat;
  return url.pathname + url.search;
}

export function reportMobileHostRoute(authenticated: boolean, authFailure = false): void {
  if (!isReactNativeHost()) return;
  (window as NativeWindow).webkit?.messageHandlers?.inkHostState?.postMessage({
    path: window.location.pathname + window.location.search, authenticated, authFailure,
  });
}
