// [Input] Deck id, a selected server option, and the frozen binding GET/PUT contracts.
// [Output] Binding state plus next-run save, conflict refresh, and user reconfirmation state.
// [Pos] Deck Editor Plugin binding data hook.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  DeckPluginApiError,
  getDeckPluginBinding,
  updateDeckPluginBinding,
  type DeckPluginBindingState,
  type DeckPluginOption,
  type DeckPluginOptionsResponse,
} from '../api/deckPluginApi';

export interface DeckPluginBindingConflict {
  message: string;
  currentRevision: number | null;
  selectionStillAvailable: boolean;
}

function bindingLoadMessage(error: unknown): string {
  if (error instanceof DeckPluginApiError && error.status === 404) {
    return '无法读取此 Deck 的工作流插件绑定。';
  }
  if (error instanceof Error && error.message === 'Not authenticated') {
    return '登录状态已失效，请重新登录后重试。';
  }
  return '工作流插件绑定加载失败，请稍后重试。';
}

function bindingSaveMessage(error: unknown): string {
  if (error instanceof DeckPluginApiError) {
    if (error.status === 422 && error.errorCode) {
      return `该版本当前不可选择（${error.errorCode}）。请按恢复提示处理后重试。`;
    }
    if (error.status === 404) return '无法保存：Deck 不存在或无编辑权限。';
  }
  if (error instanceof Error && error.message === 'Not authenticated') {
    return '登录状态已失效，请重新登录后重试。';
  }
  return '插件版本保存失败，请稍后重试。';
}

export function useDeckPluginBinding(deckId: string) {
  const [state, setState] = useState<DeckPluginBindingState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [conflict, setConflict] = useState<DeckPluginBindingConflict | null>(null);
  const requestId = useRef(0);
  const currentState = state?.deck_id === deckId ? state : null;

  const refresh = useCallback(async (): Promise<DeckPluginBindingState | null> => {
    const currentRequest = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const nextState = await getDeckPluginBinding(deckId);
      if (currentRequest === requestId.current) setState(nextState);
      return nextState;
    } catch (nextError) {
      if (currentRequest === requestId.current) setError(bindingLoadMessage(nextError));
      return null;
    } finally {
      if (currentRequest === requestId.current) setLoading(false);
    }
  }, [deckId]);

  useEffect(() => {
    void refresh();
    return () => {
      requestId.current += 1;
    };
  }, [refresh]);

  const save = useCallback(async (
    option: DeckPluginOption,
    refreshOptions: () => Promise<DeckPluginOptionsResponse | null>,
  ): Promise<boolean> => {
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    setConflict(null);
    try {
      const saved = await updateDeckPluginBinding(deckId, {
        deck_plugin_id: option.deck_plugin_id,
        deck_plugin_version: option.deck_plugin_version,
        expected_binding_revision: currentState?.binding_revision ?? 0,
        apply_to: 'next_run',
      });
      setState({
        deck_id: saved.deck_id,
        binding_revision: saved.binding_revision,
        applied_to: 'next_run',
        binding: saved,
      });
      setSuccessMessage('插件版本已更新，将在下一次运行时生效。');
      return true;
    } catch (nextError) {
      if (
        nextError instanceof DeckPluginApiError
        && nextError.status === 409
        && nextError.errorCode === 'BINDING_REVISION_CONFLICT'
      ) {
        const [, refreshedOptions] = await Promise.all([refresh(), refreshOptions()]);
        const selectionStillAvailable = Boolean(refreshedOptions?.options.some(candidate => (
          candidate.deck_plugin_id === option.deck_plugin_id
          && candidate.deck_plugin_version === option.deck_plugin_version
          && candidate.selectable
        )));
        setConflict({
          message: '该 Deck 的插件选择已被其他会话修改。已刷新最新状态，请重新确认。',
          currentRevision: nextError.currentRevision,
          selectionStillAvailable,
        });
        return false;
      }
      setError(bindingSaveMessage(nextError));
      return false;
    } finally {
      setSaving(false);
    }
  }, [currentState?.binding_revision, deckId, refresh]);

  return {
    state: currentState,
    loading,
    saving,
    error,
    successMessage,
    conflict,
    refresh,
    save,
  };
}
