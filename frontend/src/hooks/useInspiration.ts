// [Input] Editor text snapshots, enabled Voice configs, local writing preferences, and the Claude Agent SSE suggestion helper.
// [Output] Debounced, incrementally streamed Writing inspiration state with Voice Thread reuse and stale-snapshot rejection.
// [Pos] Writing inspiration orchestration hook in frontend/src/hooks
// [Sync] 2026-08-31: replace the PolyCLI suggestion session with the existing Claude Agent SSE Voice Thread and expose text-delta updates as a typewriter effect.

import { useState, useRef, useCallback, useEffect } from 'react';
import type { VoiceConfig, VoiceInspiration } from '../api/voiceApi';
import { getSuggestion } from '../api/voiceApi';
import { getMetaPrompt, getStateConfig } from '../utils/voiceStorage';

interface UseInspirationOptions {
  debounceMs?: number;
  minTextLength?: number;
  animationDurationMs?: number;
  voices?: Record<string, VoiceConfig>;
}

interface UseInspirationReturn {
  currentInspiration: VoiceInspiration | null;
  isDisappearing: boolean;
  isAppearing: boolean;
  onTextChange: (allText: string, selectedState: string | null) => void;
  clearInspiration: () => void;
  setTextGetter: (getter: () => string) => void;
}

const DEFAULT_OPTIONS = {
  debounceMs: 2000,
  minTextLength: 10,
  animationDurationMs: 800,
};
const EMPTY_VOICES: Record<string, VoiceConfig> = {};

// @@@ Inspiration suggestion hook - debounces Claude SSE voice-thread suggestions and validates snapshots
export function useInspiration(options: UseInspirationOptions = {}): UseInspirationReturn {
  const config = { ...DEFAULT_OPTIONS, ...options };
  const voices = options.voices ?? EMPTY_VOICES;

  const [currentInspiration, setCurrentInspiration] = useState<VoiceInspiration | null>(null);
  const [isDisappearing, setIsDisappearing] = useState(false);
  const [isAppearing, setIsAppearing] = useState(false);

  const currentInspirationRef = useRef<VoiceInspiration | null>(null);
  const timerRef = useRef<number | null>(null);
  const appearanceFrameRef = useRef<number | null>(null);
  const snapshotRef = useRef<string>('');
  const textGetterRef = useRef<(() => string) | null>(null);
  const resolvedThreadIdsRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    if (isDisappearing) {
      const timer = window.setTimeout(() => {
        currentInspirationRef.current = null;
        setCurrentInspiration(null);
        setIsDisappearing(false);
        setIsAppearing(false);
      }, config.animationDurationMs);
      return () => window.clearTimeout(timer);
    }
  }, [isDisappearing, config.animationDurationMs]);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
      if (appearanceFrameRef.current !== null) {
        window.cancelAnimationFrame(appearanceFrameRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const next = new Map<string, string>();
    for (const [voiceKey, voice] of Object.entries(voices)) {
      const threadId = voice.thread_id || resolvedThreadIdsRef.current.get(voiceKey);
      if (threadId) next.set(voiceKey, threadId);
    }
    resolvedThreadIdsRef.current = next;
  }, [voices]);

  const setTextGetter = useCallback((getter: () => string) => {
    textGetterRef.current = getter;
  }, []);

  const displayInspiration = useCallback((suggestion: VoiceInspiration) => {
    const isFirstDelta = currentInspirationRef.current === null;
    currentInspirationRef.current = suggestion;
    setCurrentInspiration(suggestion);
    setIsDisappearing(false);
    if (!isFirstDelta) return;

    setIsAppearing(true);
    if (appearanceFrameRef.current !== null) {
      window.cancelAnimationFrame(appearanceFrameRef.current);
    }
    appearanceFrameRef.current = window.requestAnimationFrame(() => {
      appearanceFrameRef.current = null;
      setIsAppearing(false);
    });
  }, []);

  const clearInspiration = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    currentInspirationRef.current = null;
    setCurrentInspiration(null);
    setIsDisappearing(false);
    setIsAppearing(false);
  }, []);

  const onTextChange = useCallback((allText: string, selectedState: string | null) => {
    if (currentInspirationRef.current) {
      setIsDisappearing(true);
    }

    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }

    if (allText.trim().length < config.minTextLength) {
      return;
    }

    timerRef.current = window.setTimeout(async () => {
      snapshotRef.current = allText;

      try {
        const metaPrompt = getMetaPrompt();
        const stateConfig = getStateConfig();
        const statePrompt = selectedState && stateConfig.states[selectedState]
          ? stateConfig.states[selectedState].prompt
          : '';

        const suggestion = await getSuggestion(
          allText,
          voices,
          metaPrompt,
          statePrompt,
          resolvedThreadIdsRef.current,
          (partialSuggestion) => {
            const liveText = textGetterRef.current?.() ?? '';
            if (liveText !== snapshotRef.current) return;
            resolvedThreadIdsRef.current.set(
              partialSuggestion.voice_key,
              partialSuggestion.thread_id,
            );
            displayInspiration(partialSuggestion);
          },
        );
        const currentText = textGetterRef.current?.() ?? '';

        if (suggestion && currentText === snapshotRef.current) {
          resolvedThreadIdsRef.current.set(suggestion.voice_key, suggestion.thread_id);
          displayInspiration(suggestion);
        }
      } catch (error) {
        console.error('Failed to get inspiration:', error);
      }
    }, config.debounceMs);
  }, [config.minTextLength, config.debounceMs, displayInspiration, voices]);

  return {
    currentInspiration,
    isDisappearing,
    isAppearing,
    onTextChange,
    clearInspiration,
    setTextGetter,
  };
}
