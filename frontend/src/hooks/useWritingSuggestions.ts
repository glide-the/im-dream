// [Input] Current EditorEngine Session, Session persistence barrier, product i18n, and the shared Claude Agent Thread/SSE transports.
// [Output] Provide explicit generate/retry commands for persistent WritingSuggestionCells with Session/Cell/request/Thread stale-response isolation.
// [Pos] Manual Writing suggestion orchestration hook in frontend/src/hooks.
// [Sync] 2026-09-01: replace automatic debounced random-Voice inspiration with one manually triggered Session-owned Writing Thread.

import { useCallback, useEffect, useRef, type RefObject } from 'react';
import i18n from '../i18n';
import { createChatThread } from '../api/chatHistoryApi';
import { streamClaudeAgentTurn } from '../api/voiceApi';
import type {
  EditorEngine,
  EditorState,
  WritingSuggestionError,
} from '../engine/EditorEngine';
import { readClaudeAgentErrorCode } from '../lib/claude-agent-transport';
import { getMetaPrompt, getStateConfig } from '../utils/voiceStorage';

interface WritingSuggestionPrompt {
  message: string;
  systemPrompt: string;
}

export interface WritingSuggestionRequest {
  sessionId: string;
  suggestionCellId: string;
  requestId: string;
  textSnapshot: string;
}

type StreamClaudeAgentTurn = typeof streamClaudeAgentTurn;

export interface WritingSuggestionControllerDependencies {
  getEngine: () => EditorEngine | null;
  createThread: () => Promise<string | null>;
  persistSession: (state: EditorState) => Promise<unknown>;
  streamTurn: StreamClaudeAgentTurn;
  buildPrompt: (textSnapshot: string) => WritingSuggestionPrompt;
}

function createRequestId(): string {
  return crypto.randomUUID ? crypto.randomUUID() : `writing-${Date.now().toString(36)}`;
}

function safeSuggestionError(error: unknown): WritingSuggestionError {
  const protocolCode = readClaudeAgentErrorCode(error);
  const retryable = error && typeof error === 'object' && 'retryable' in error
    ? (error as { retryable?: unknown }).retryable !== false
    : true;
  return {
    code: protocolCode || 'WRITING_REQUEST_FAILED',
    message: 'The suggestion could not be generated.',
    retryable,
  };
}

function buildProductWritingPrompt(
  textSnapshot: string,
  selectedState: string | null,
): WritingSuggestionPrompt {
  const metaPrompt = getMetaPrompt().trim();
  const stateConfig = getStateConfig();
  const statePrompt = selectedState && stateConfig.states[selectedState]
    ? stateConfig.states[selectedState].prompt.trim()
    : '';
  const optionalContext = [
    statePrompt ? `The writer's current self-described state:\n${statePrompt}` : '',
    metaPrompt ? `The writer's saved style preference:\n${metaPrompt}` : '',
  ].filter(Boolean).join('\n\n');

  return {
    systemPrompt: [
      'You are Ink & Memory Writing Suggestions, a product-level writing companion.',
      'Respond in the same language as the quoted passage.',
      'Offer a concise, concrete direction that helps the writer explore the passage more deeply.',
      'Do not claim a persona, mention a Deck or Voice, critique the writer, summarize the passage, or include a heading.',
      'Return only the suggestion text.',
      optionalContext,
    ].filter(Boolean).join('\n\n'),
    message: [
      'Focus only on this user-authored passage. Earlier assistant suggestions in the Thread are not user prose.',
      '<writing_passage>',
      textSnapshot,
      '</writing_passage>',
      'Give one useful direction for going deeper.',
    ].join('\n'),
  };
}

export class WritingSuggestionController {
  private readonly dependencies: WritingSuggestionControllerDependencies;
  private activeRequests = new Map<string, WritingSuggestionRequest & { abort: AbortController }>();
  private threadCreation: { sessionId: string; promise: Promise<string> } | null = null;

  constructor(dependencies: WritingSuggestionControllerDependencies) {
    this.dependencies = dependencies;
  }

  private hasStreamingRequest(sessionId: string, engine: EditorEngine): boolean {
    return [...this.activeRequests.values()].some((request) => {
      if (request.sessionId !== sessionId) return false;
      const cell = engine.getWritingSuggestionCell(request.suggestionCellId);
      return cell?.status === 'streaming' && cell.requestId === request.requestId;
    });
  }

  start(textCellId: string): string | null {
    const engine = this.dependencies.getEngine();
    if (!engine) return null;
    const state = engine.getState();
    if (this.hasStreamingRequest(state.id, engine)) {
      return null;
    }
    const textCell = state.cells.find((cell) => cell.id === textCellId);
    if (!textCell || textCell.type !== 'text' || !textCell.content.trim()) return null;

    const requestId = createRequestId();
    const suggestion = engine.insertWritingSuggestionAfterTextCell(
      textCellId,
      textCell.content,
      requestId,
    );
    if (!suggestion) return null;

    this.run({
      sessionId: state.id,
      suggestionCellId: suggestion.id,
      requestId,
      textSnapshot: suggestion.anchor.textSnapshot,
    });
    return suggestion.id;
  }

  retry(suggestionCellId: string): boolean {
    const engine = this.dependencies.getEngine();
    if (!engine) return false;
    const state = engine.getState();
    if (this.hasStreamingRequest(state.id, engine)) {
      return false;
    }
    const existing = engine.getWritingSuggestionCell(suggestionCellId);
    if (!existing || !existing.anchor.textSnapshot.trim()) return false;

    const requestId = createRequestId();
    const suggestion = engine.beginWritingSuggestionRetry(suggestionCellId, requestId);
    if (!suggestion) return false;

    this.run({
      sessionId: state.id,
      suggestionCellId,
      requestId,
      textSnapshot: suggestion.anchor.textSnapshot,
    });
    return true;
  }

  cancelRequestsOutsideSession(sessionId: string | null): void {
    for (const [cellId, request] of this.activeRequests) {
      if (request.sessionId === sessionId) continue;
      request.abort.abort();
      this.activeRequests.delete(cellId);
    }
    if (this.threadCreation && this.threadCreation.sessionId !== sessionId) {
      this.threadCreation = null;
    }
  }

  dispose(): void {
    for (const request of this.activeRequests.values()) request.abort.abort();
    this.activeRequests.clear();
    this.threadCreation = null;
  }

  private run(request: WritingSuggestionRequest): void {
    const abort = new AbortController();
    this.activeRequests.set(request.suggestionCellId, { ...request, abort });
    void this.generate(request, abort).finally(() => {
      const active = this.activeRequests.get(request.suggestionCellId);
      if (active?.requestId === request.requestId) {
        this.activeRequests.delete(request.suggestionCellId);
      }
    });
  }

  private async ensureThread(sessionId: string): Promise<string> {
    const engine = this.dependencies.getEngine();
    if (!engine || engine.getState().id !== sessionId) {
      throw new Error('Writing Session changed before Thread resolution.');
    }
    const existingThreadId = engine.getState().writingThreadId;
    if (existingThreadId) return existingThreadId;

    if (this.threadCreation?.sessionId === sessionId) return this.threadCreation.promise;
    const promise = this.dependencies.createThread().then((threadId) => {
      if (!threadId) throw new Error('Writing Thread could not be created.');
      const liveEngine = this.dependencies.getEngine();
      if (!liveEngine?.setWritingThreadId(sessionId, threadId)) {
        throw new Error('Writing Session changed before Thread association.');
      }
      return threadId;
    }).finally(() => {
      if (this.threadCreation?.promise === promise) this.threadCreation = null;
    });
    this.threadCreation = { sessionId, promise };
    return promise;
  }

  private isCurrent(request: WritingSuggestionRequest, threadId?: string): boolean {
    return this.dependencies.getEngine()?.isWritingSuggestionRequestCurrent(
      request.sessionId,
      request.suggestionCellId,
      request.requestId,
      threadId,
    ) ?? false;
  }

  private fail(
    request: WritingSuggestionRequest,
    error: WritingSuggestionError,
    threadId?: string,
  ): void {
    this.dependencies.getEngine()?.failWritingSuggestion(
      request.sessionId,
      request.suggestionCellId,
      request.requestId,
      error,
      threadId,
    );
  }

  private async generate(
    request: WritingSuggestionRequest,
    abort: AbortController,
  ): Promise<void> {
    let threadId: string | undefined;
    try {
      threadId = await this.ensureThread(request.sessionId);
      if (!this.isCurrent(request, threadId)) return;

      const engine = this.dependencies.getEngine();
      if (!engine) return;
      try {
        await this.dependencies.persistSession(engine.getState());
      } catch {
        this.fail(request, {
          code: 'WRITING_THREAD_PERSIST_FAILED',
          message: 'The Writing Thread association could not be saved.',
          retryable: true,
        }, threadId);
        return;
      }
      if (!this.isCurrent(request, threadId)) return;

      const prompt = this.dependencies.buildPrompt(request.textSnapshot);
      await this.dependencies.streamTurn({
        threadId,
        message: prompt.message,
        systemPrompt: prompt.systemPrompt,
        signal: abort.signal,
        onDelta: (delta) => {
          this.dependencies.getEngine()?.appendWritingSuggestionDelta(
            request.sessionId,
            request.suggestionCellId,
            request.requestId,
            threadId as string,
            delta,
          );
        },
        onComplete: (fullText) => {
          const liveEngine = this.dependencies.getEngine();
          const cell = liveEngine?.getWritingSuggestionCell(request.suggestionCellId);
          if (!fullText.trim() && !cell?.content.trim()) {
            this.fail(request, {
              code: 'WRITING_REQUEST_FAILED',
              message: 'The suggestion response was empty.',
              retryable: true,
            }, threadId);
            return;
          }
          liveEngine?.completeWritingSuggestion(
            request.sessionId,
            request.suggestionCellId,
            request.requestId,
            threadId as string,
          );
        },
        onError: (error) => {
          this.fail(request, safeSuggestionError(error), threadId);
        },
      });
    } catch {
      this.fail(request, {
        code: 'WRITING_THREAD_CREATE_FAILED',
        message: 'The Writing Thread could not be created.',
        retryable: true,
      }, threadId);
    }
  }
}

interface UseWritingSuggestionsOptions {
  engineRef: RefObject<EditorEngine | null>;
  sessionId: string | null;
  selectedState: string | null;
  persistSession: (state: EditorState) => Promise<unknown>;
}

export function useWritingSuggestions({
  engineRef,
  sessionId,
  selectedState,
  persistSession,
}: UseWritingSuggestionsOptions) {
  const selectedStateRef = useRef(selectedState);
  const persistSessionRef = useRef(persistSession);
  selectedStateRef.current = selectedState;
  persistSessionRef.current = persistSession;

  const controllerRef = useRef<WritingSuggestionController | null>(null);
  if (!controllerRef.current) {
    controllerRef.current = new WritingSuggestionController({
      getEngine: () => engineRef.current,
      createThread: () => createChatThread(
        undefined,
        undefined,
        i18n.t('writingSuggestion.threadTitle'),
      ),
      persistSession: (editorState) => persistSessionRef.current(editorState),
      streamTurn: streamClaudeAgentTurn,
      buildPrompt: (textSnapshot) => buildProductWritingPrompt(
        textSnapshot,
        selectedStateRef.current,
      ),
    });
  }

  useEffect(() => {
    controllerRef.current?.cancelRequestsOutsideSession(sessionId);
  }, [sessionId]);

  useEffect(() => () => controllerRef.current?.dispose(), []);

  const generateSuggestion = useCallback((textCellId: string) => (
    controllerRef.current?.start(textCellId) ?? null
  ), []);
  const retrySuggestion = useCallback((suggestionCellId: string) => (
    controllerRef.current?.retry(suggestionCellId) ?? false
  ), []);

  return { generateSuggestion, retrySuggestion };
}
