// [Input] Existing browser session and Admin-owned default/desired policy revisions.
// [Output] Draft behavior editing, idempotent save/recovery and next-response feedback.
// [Pos] Single new Settings section; Reflections pages stay unchanged.
// [Sync] 2026-10-15: initial L3 memory behavior controls.
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { API_BASE } from '../../lib/apiBase';
import { browserRequestHeaders } from '../../lib/browserSession';
import './MemoryBehaviorSettings.css';
type ThemeId = 'THEME_FRUSTRATION' | 'THEME_DEFENSE' | 'THEME_PRESSURE' | 'THEME_VALUE';
type Option = { enabled: boolean; action: string };
type Desired = { enabled: boolean; themes: Record<ThemeId, Option> };
type Snapshot = { owner_id: string; revision: number; taxonomy_revision: string; default: Desired; desired: Desired; updated_at: string | null; catalog: { id: ThemeId; label: string; actions: string[]; default_action: string }[] };
type Command = { owner: string; requestId: string; input: { expected_revision: number; desired: Desired } };
const PENDING_KEY = 'ink-memory-behavior-pending-v1';
const ACTIONS: Record<string, [string, string]> = {
  acknowledge_then_help: ['先回应感受，再提供帮助', 'Acknowledge, then help'],
  help_only: ['直接帮助当前任务', 'Help with the current task'],
  ask_support_type: ['任务不明确时询问需要哪种支持', 'Ask about support when the task is unclear'],
  respect_distance: ['尊重距离，不追问心理话题', 'Respect distance without probing'],
  prioritize_actions: ['梳理优先顺序和下一步', 'Prioritize actions and next steps'],
  connect_goal_to_choice: ['结合目标解释选择与取舍', 'Connect goals to choices'],
  acknowledge_only: ['简短回应当前表达的需要', 'Briefly acknowledge the expressed need'],
};
const THEMES: Record<ThemeId, string> = { THEME_FRUSTRATION: 'Frustration', THEME_DEFENSE: 'Defense', THEME_PRESSURE: 'Pressure', THEME_VALUE: 'Value' };
function savedCommand(owner: string): Command | null {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY);
    const command = raw ? JSON.parse(raw) as Command : null;
    return command?.owner === owner && typeof command.requestId === 'string' ? command : null;
  } catch { return null; }
}
export default function MemoryBehaviorSettings() {
  const { i18n } = useTranslation(); const zh = i18n.language.startsWith('zh');
  const words = (cn: string, en: string) => zh ? cn : en;
  const loadRevision = useRef(0);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [draft, setDraft] = useState<Desired | null>(null);
  const [pending, setPending] = useState<Command | null>(null);
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState('');
  const [error, setError] = useState(false);
  const [conflict, setConflict] = useState(false);
  const load = useCallback(async (signal?: AbortSignal) => {
    const revision = ++loadRevision.current;
    setBusy(true); setError(false); setConflict(false);
    try {
      const response = await fetch(`${API_BASE}/api/memory/behavior`, { headers: browserRequestHeaders(), signal });
      if (!response.ok) throw new Error('read');
      const current = await response.json() as Snapshot;
      if (revision !== loadRevision.current || signal?.aborted) return;
      setSnapshot(current); setDraft(structuredClone(current.desired));
      const command = savedCommand(current.owner_id); setPending(command);
      setMessage(command ? (zh ? '上次保存结果尚未核实。可核实保存结果，或读取最新设置。' : 'The previous save is unverified. Check its result or load current settings.') : '');
    } catch { if (revision !== loadRevision.current || signal?.aborted) return; setError(true); setMessage(zh ? '暂时无法读取设置，请重试。' : 'Settings could not be loaded. Please retry.'); }
    finally { if (revision === loadRevision.current && !signal?.aborted) setBusy(false); }
  }, [zh]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => { controller.abort(); }; }, [load]);
  const finish = (result: Snapshot) => {
    setSnapshot(result); setDraft(structuredClone(result.desired)); setPending(null);
    sessionStorage.removeItem(PENDING_KEY); setError(false); setConflict(false);
    setMessage(words('已保存，下一次回应使用此设置。', 'Saved. These settings apply to the next response.'));
  };
  const submit = async (command: Command) => {
    setBusy(true); setError(false); setPending(command);
    sessionStorage.setItem(PENDING_KEY, JSON.stringify(command));
    try {
      const response = await fetch(`${API_BASE}/api/memory/behavior`, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Request-ID': command.requestId, ...browserRequestHeaders() }, body: JSON.stringify(command.input) });
      if (response.ok) finish(await response.json() as Snapshot);
      else {
        const body = await response.json().catch(() => ({})) as { detail?: { outcome_unknown?: boolean } };
        setError(true);
        if (response.status === 409) {
          setPending(null); sessionStorage.removeItem(PENDING_KEY);
          setConflict(true);
          const latest = await fetch(`${API_BASE}/api/memory/behavior`, { headers: browserRequestHeaders() }).catch(() => null);
          if (latest?.ok) {
            const current = await latest.json() as Snapshot;
            if (current.owner_id === command.owner) setSnapshot(current);
          }
          setMessage(words('设置已在其他位置更新。草稿已保留；核对已保存值后再保存，或读取最新设置。', 'Settings changed elsewhere. Your draft is preserved; review saved values before saving or load current settings.'));
        } else if (body.detail?.outcome_unknown || response.status >= 500) {
          setMessage(words('保存结果尚未核实。请核实结果或重试同一次保存。', 'The save result is unverified. Check it or retry the same save.'));
        } else {
          setPending(null); sessionStorage.removeItem(PENDING_KEY);
          setMessage(words('保存未完成，请稍后重试。', 'Settings were not saved. Please retry.'));
        }
      }
    } catch { setError(true); setMessage(words('连接中断，保存结果尚未核实。请核实结果或重试同一次保存。', 'Connection interrupted. Check the result or retry the same save.')); }
    finally { setBusy(false); }
  };
  const check = async () => {
    if (!pending) return; setBusy(true);
    try {
      const response = await fetch(`${API_BASE}/api/memory/behavior/receipt/${encodeURIComponent(pending.requestId)}`, { headers: browserRequestHeaders() });
      if (!response.ok) throw new Error('receipt');
      const receipt = await response.json() as { status: string; result: Snapshot | null };
      if (receipt.status === 'committed' && receipt.result) finish(receipt.result);
      else { setError(true); setMessage(words('尚未找到保存回执。可以重试同一次保存。', 'No save receipt was found. You can retry the same save.')); }
    } catch { setError(true); setMessage(words('暂时无法核实保存结果。', 'The save result could not be checked.')); }
    finally { setBusy(false); }
  };
  const dirty = snapshot && draft && JSON.stringify(draft) !== JSON.stringify(snapshot.desired);
  return <section className="memory-behavior" aria-labelledby="memory-behavior-title">
    <header><h1 id="memory-behavior-title">{words('记忆回应', 'Memory responses')}</h1><p>{words('有可用回顾内容时，根据与你当前任务相关的观察调整回应方式。', 'Adapt responses using relevant Reflections observations.')}</p></header>
    {message && <p role={error ? 'alert' : 'status'} className="memory-behavior__message">{message}</p>}
    {!snapshot || !draft ? <button disabled={busy} onClick={() => { void load(); }}>{busy ? words('读取中…', 'Loading…') : words('重新读取', 'Reload')}</button> : <>
      <div className="story-workspace-settings__card"><label className="memory-behavior__toggle"><input type="checkbox" checked={draft.enabled} disabled={busy || !!pending} onChange={e => setDraft({ ...draft, enabled: e.target.checked })}/><strong>{words('使用回顾记忆调整回应', 'Use Reflections to adapt responses')}</strong></label><p>{words('默认关闭。开启后仍以你当前的任务和明确表达的边界为准。', 'Off by default. Your current task and stated boundaries take priority.')}</p></div>
      {conflict && <p>{words('其他位置已保存：', 'Saved elsewhere: ')}{snapshot.desired.enabled ? words('已开启', 'On') : words('已关闭', 'Off')} · {snapshot.catalog.map(theme => `${zh ? theme.label : THEMES[theme.id]}：${snapshot.desired.themes[theme.id].enabled ? ACTIONS[snapshot.desired.themes[theme.id].action]?.[zh ? 0 : 1] : words('关闭', 'Off')}`).join('；')}</p>}
      <div className="memory-behavior__themes">{snapshot.catalog.map(theme => <fieldset key={theme.id} className="story-workspace-settings__card" disabled={busy || !!pending || !draft.enabled}>
        <legend>{zh ? theme.label : THEMES[theme.id]}</legend>
        <label className="memory-behavior__toggle"><input type="checkbox" checked={draft.themes[theme.id].enabled} onChange={e => setDraft({ ...draft, themes: { ...draft.themes, [theme.id]: { ...draft.themes[theme.id], enabled: e.target.checked } } })}/>{words('启用此主题', 'Enable this theme')}</label>
        <label className="memory-behavior__action"><span>{words('回应方式', 'Response style')}</span><select aria-label={`${zh ? theme.label : THEMES[theme.id]} ${words('回应方式', 'response style')}`} value={draft.themes[theme.id].action} onChange={e => setDraft({ ...draft, themes: { ...draft.themes, [theme.id]: { ...draft.themes[theme.id], action: e.target.value } } })}>{theme.actions.map(action => <option value={action} key={action}>{ACTIONS[action]?.[zh ? 0 : 1] ?? action}</option>)}</select></label>
      </fieldset>)}</div>
      <p>{words('保存不影响正在生成的回应。历史主题只是分析线索，不代表你现在的情绪。', 'Saving does not change an in-progress response. Historical themes do not describe your current feelings.')}</p>
      <div className="memory-behavior__buttons">
        <button disabled={busy || !!pending} onClick={() => setDraft(structuredClone(snapshot.default))}>{words('恢复默认', 'Restore defaults')}</button>
        {pending ? <><button disabled={busy} onClick={() => { void check(); }}>{words('核实保存结果', 'Check save result')}</button><button disabled={busy} onClick={() => { void submit(pending); }}>{words('重试这次保存', 'Retry this save')}</button></> : <button disabled={busy || !dirty} onClick={() => { void submit({ owner: snapshot.owner_id, requestId: crypto.randomUUID(), input: { expected_revision: snapshot.revision, desired: draft } }); }}>{busy ? words('保存中…', 'Saving…') : words('保存', 'Save')}</button>}
        <button disabled={busy} onClick={() => { sessionStorage.removeItem(PENDING_KEY); setPending(null); void load(); }}>{words('读取最新设置', 'Load current settings')}</button>
      </div>
    </>}
  </section>;
}
