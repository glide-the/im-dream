// [Input] Original ready installation/Deck reference endpoints and optional platform HTTP.
// [Output] Shared selection, durable save feedback and original error/retry state.
// [Pos] Deck plugin-reference UI lifecycle used by Web and Native presentations.
// [Sync] 2026-10-29: extract the existing selector lifecycle; installation status and reference payload remain server-owned.
import {useCallback,useEffect,useMemo,useState} from 'react';
import {ClaudePluginApiError,listClaudePluginInstallations,listDeckClaudePluginRefs,putDeckClaudePluginRefs,type ClaudePluginInstallation} from '../api/claudePluginAdminApi';

export function useDeckClaudePluginRefs(deckId:string,onSaved?:()=>Promise<void>,transport:typeof fetch=fetch){
  const [installations, setInstallations] = useState<ClaudePluginInstallation[]>([]);
  const [selected, setSelected] = useState<Map<string, boolean>>(new Map());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const readyInstallations = useMemo(
    () => installations.filter((item) => item.status === 'ready'),
    [installations],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [installResult, refs] = await Promise.all([
        listClaudePluginInstallations(transport),
        listDeckClaudePluginRefs(deckId,transport),
      ]);
      setInstallations(installResult.installations);
      const next = new Map<string, boolean>();
      refs.forEach((ref) => next.set(ref.plugin_installation_id, ref.enabled === 1));
      setSelected(next);
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setLoading(false);
    }
  }, [deckId,transport]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = useCallback((installationId: string) => {
    setSaved(false);
    setSelected((current) => {
      const next = new Map(current);
      if (next.get(installationId)) {
        next.delete(installationId);
      } else {
        next.set(installationId, true);
      }
      return next;
    });
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const refs = [...selected.entries()]
        .filter(([, enabled]) => enabled)
        .map(([installationId], index) => ({
          plugin_installation_id: installationId,
          enabled: true,
          order_index: index,
        }));
      await putDeckClaudePluginRefs(deckId, refs,transport);
      await onSaved?.();
      setSaved(true);
    } catch (err) {
      setError(err instanceof ClaudePluginApiError ? `${err.code}: ${err.message}` : String(err));
    } finally {
      setSaving(false);
    }
  }, [deckId, onSaved, selected,transport]);

  return {readyInstallations,selected,loading,saving,error,saved,toggle,handleSave,load};
}
