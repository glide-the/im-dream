// [Input] A selected enabled Deck, one creation goal, and the Dream start API.
// [Output] A single-in-flight Dream launch state plus the canonical run route.
// [Pos] Story Workspace hook node - dedicated Dream launch (Task 3 U4)

import { useCallback, useRef, useState } from 'react';
import { storyWorkspaceStartDreamRun } from '../../api/storyWorkspaceApi';
import type {
  StoryWorkspaceDreamLaunchAccepted,
  StoryWorkspaceDreamLaunchCommand,
} from './contracts';

type StoryWorkspaceDreamLaunchTransport = (
  command: StoryWorkspaceDreamLaunchCommand,
) => Promise<StoryWorkspaceDreamLaunchAccepted>;

export interface StoryWorkspaceDreamLauncher {
  start: (deckId: string, agentId: string, goal: string) => Promise<StoryWorkspaceDreamLaunchAccepted>;
}

export function storyWorkspaceNewDreamLaunchIdempotencyKey(
  uuidFactory: () => string = () => {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  },
): string {
  return `dream_${uuidFactory()}`;
}

export function storyWorkspaceDreamRunPath(workflowRunId: string): string {
  return `/story-workspace/dream?run=${encodeURIComponent(workflowRunId)}`;
}

/**
 * A small framework-independent coordinator. Assigning the Promise before it
 * leaves start() makes two synchronous clicks share one request.
 */
export function createStoryWorkspaceDreamLauncher(
  transport: StoryWorkspaceDreamLaunchTransport = storyWorkspaceStartDreamRun,
  idempotencyKeyFactory: () => string = storyWorkspaceNewDreamLaunchIdempotencyKey,
): StoryWorkspaceDreamLauncher {
  let inFlight: Promise<StoryWorkspaceDreamLaunchAccepted> | null = null;
  let retainedRequest: {
    fingerprint: string;
    idempotencyKey: string;
  } | null = null;

  return {
    start(deckId, agentId, goal) {
      if (inFlight) return inFlight;
      const normalizedDeckId = deckId.trim();
      const normalizedAgentId = agentId.trim();
      const normalizedGoal = goal.trim();
      if (!normalizedDeckId || !normalizedAgentId || !normalizedGoal) {
        return Promise.reject(new Error('请选择 Agent 并填写创作目标。'));
      }
      const fingerprint = `${normalizedDeckId}\u0000${normalizedAgentId}\u0000${normalizedGoal}`;
      if (!retainedRequest || retainedRequest.fingerprint !== fingerprint) {
        retainedRequest = {
          fingerprint,
          idempotencyKey: idempotencyKeyFactory(),
        };
      }
      const command: StoryWorkspaceDreamLaunchCommand = {
        deckId: normalizedDeckId,
        agentId: normalizedAgentId,
        goal: normalizedGoal,
        idempotencyKey: retainedRequest.idempotencyKey,
      };
      const pending = transport(command).finally(() => {
        inFlight = null;
      });
      inFlight = pending;
      return pending;
    },
  };
}

export interface StoryWorkspaceDreamLaunchState {
  readonly isLaunching: boolean;
  readonly error: Error | null;
  readonly start: (
    deckId: string,
    agentId: string,
    goal: string,
  ) => Promise<StoryWorkspaceDreamLaunchAccepted>;
}

export function useStoryWorkspaceDreamLaunch(): StoryWorkspaceDreamLaunchState {
  const launcher = useRef<StoryWorkspaceDreamLauncher | null>(null);
  if (!launcher.current) launcher.current = createStoryWorkspaceDreamLauncher();
  const [isLaunching, setIsLaunching] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const start = useCallback((deckId: string, agentId: string, goal: string) => {
    setIsLaunching(true);
    setError(null);
    return launcher.current!.start(deckId, agentId, goal).catch((reason: unknown) => {
      const launchError = reason instanceof Error
        ? reason
        : new Error('Dream 暂时无法发起。');
      setError(launchError);
      throw launchError;
    }).finally(() => {
      setIsLaunching(false);
    });
  }, []);

  return { isLaunching, error, start };
}
