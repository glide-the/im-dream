// [Input] Plugin lifecycle mutations and server operation polling.
// [Output] Mutation runner with authoritative queued/running/completed/error progress.
// [Pos] Plugin Admin operation hook; never fabricates backend completion.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getPluginOperation,
  installPlugin,
  mutatePlugin,
  type InstallPluginInput,
  type PluginMutationInput,
  type PluginOperation,
} from '../api/deckPluginAdminApi';

const TERMINAL_STATUSES = new Set(['ready', 'completed', 'error', 'failed']);

export function usePluginOperation(onSettled?: () => void) {
  const [operation, setOperation] = useState<PluginOperation | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const settledCallbackRef = useRef(onSettled);
  settledCallbackRef.current = onSettled;

  const track = useCallback(async (promise: Promise<PluginOperation>) => {
    setSubmitting(true);
    setError(null);
    try {
      const nextOperation = await promise;
      setOperation(nextOperation);
      if (TERMINAL_STATUSES.has(nextOperation.status)) settledCallbackRef.current?.();
      return nextOperation;
    } catch (reason) {
      const nextError = reason instanceof Error ? reason : new Error('插件管理操作失败。');
      setError(nextError);
      throw nextError;
    } finally {
      setSubmitting(false);
    }
  }, []);

  const install = useCallback((input: InstallPluginInput) => track(installPlugin(input)), [track]);
  const mutate = useCallback((input: PluginMutationInput) => track(mutatePlugin(input)), [track]);
  const clear = useCallback(() => {
    setOperation(null);
    setError(null);
  }, []);

  useEffect(() => {
    if (!operation || TERMINAL_STATUSES.has(operation.status)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void getPluginOperation(operation, controller.signal)
        .then((nextOperation) => {
          setOperation(nextOperation);
          if (TERMINAL_STATUSES.has(nextOperation.status)) settledCallbackRef.current?.();
        })
        .catch((reason: unknown) => {
          if (controller.signal.aborted) return;
          setError(reason instanceof Error ? reason : new Error('无法刷新操作进度。'));
        });
    }, 1500);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [operation]);

  return { operation, submitting, error, install, mutate, clear };
}
