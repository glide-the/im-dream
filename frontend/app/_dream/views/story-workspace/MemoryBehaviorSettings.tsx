// [Sync] 2026-10-29: reuse the original Memory responses state with the unchanged Web DOM and CSS.
// [Input] Existing browser session and Admin-owned default/desired policy revisions.
// [Output] Draft behavior editing, idempotent save/recovery and next-response feedback.
// [Pos] Single new Settings section; Reflections pages stay unchanged.
// [Sync] 2026-10-15: initial L3 memory behavior controls.
import {useTranslation} from 'react-i18next';
import useMemoryBehaviorSettings,{cloneMemoryBehavior,MEMORY_BEHAVIOR_ACTIONS as ACTIONS,MEMORY_BEHAVIOR_THEMES as THEMES} from '../../hooks/useMemoryBehaviorSettings';
import './MemoryBehaviorSettings.css';
export default function MemoryBehaviorSettings() {
  const {i18n}=useTranslation();const zh=i18n.language.startsWith('zh');
  const words=(cn:string,en:string)=>zh?cn:en;
  const {snapshot,draft,setDraft,pending,busy,message,error,conflict,load,submit,save,check,loadCurrent,dirty}=useMemoryBehaviorSettings({zh});
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
        <button disabled={busy || !!pending} onClick={() => setDraft(cloneMemoryBehavior(snapshot.default))}>{words('恢复默认', 'Restore defaults')}</button>
        {pending ? <><button disabled={busy} onClick={() => { void check(); }}>{words('核实保存结果', 'Check save result')}</button><button disabled={busy} onClick={() => { void submit(pending); }}>{words('重试这次保存', 'Retry this save')}</button></> : <button disabled={busy || !dirty} onClick={() => { void save(); }}>{busy ? words('保存中…', 'Saving…') : words('保存', 'Save')}</button>}
        <button disabled={busy} onClick={() => { loadCurrent(); }}>{words('读取最新设置', 'Load current settings')}</button>
      </div>
    </>}
  </section>;
}
