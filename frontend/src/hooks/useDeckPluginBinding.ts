// [Input] Deck id, exact server versions, and optimistic binding APIs.
// [Output] Current runtime-version binding plus explicit save/conflict state.
// [Pos] Deck version-management data hook.
// [Sync] 2026-08-16: restore real binding-version management without Workflow UI semantics.

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

function loadMessage(error: unknown): string {
  if (error instanceof DeckPluginApiError && error.status === 404) return '此 Deck 的版本信息不可用。';
  if (error instanceof Error && error.message === 'Not authenticated') return '登录状态已失效，请重新登录。';
  return '版本信息加载失败，请稍后重试。';
}

function saveMessage(error: unknown): string {
  if (error instanceof DeckPluginApiError) {
    if (error.status === 422 && error.errorCode) return `该版本当前不可选择（${error.errorCode}）。`;
    if (error.status === 404) return '无法保存：Deck 不存在或无编辑权限。';
  }
  return '版本保存失败，请稍后重试。';
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
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const next = await getDeckPluginBinding(deckId);
      if (id === requestId.current) setState(next);
      return next;
    } catch (nextError) {
      if (id === requestId.current) setError(loadMessage(nextError));
      return null;
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [deckId]);

  useEffect(() => {
    void refresh();
    return () => { requestId.current += 1; };
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
      setSuccessMessage(`已切换到 v${saved.deck_plugin_version}，下一次运行生效。`);
      return true;
    } catch (nextError) {
      if (
        nextError instanceof DeckPluginApiError
        && nextError.status === 409
        && nextError.errorCode === 'BINDING_REVISION_CONFLICT'
      ) {
        const [, refreshedOptions] = await Promise.all([refresh(), refreshOptions()]);
        const selectionStillAvailable = Boolean(refreshedOptions?.options.some((candidate) => (
          candidate.deck_plugin_id === option.deck_plugin_id
          && candidate.deck_plugin_version === option.deck_plugin_version
          && candidate.selectable
        )));
        setConflict({
          message: '版本已被其他会话修改。已刷新最新状态，请重新确认。',
          currentRevision: nextError.currentRevision,
          selectionStillAvailable,
        });
        return false;
      }
      setError(saveMessage(nextError));
      return false;
    } finally {
      setSaving(false);
    }
  }, [currentState?.binding_revision, deckId, refresh]);

  return { state: currentState, loading, saving, error, successMessage, conflict, refresh, save };
}
