// [Sync] 2026-10-29: share original selection reads/rules through useReflectionAnalysisContent; Web placement and controls remain.
// [Sync] 2026-10-28: analysis Agent choices use one shared Deck/Agent catalog read.
// [Input] Page-local analysis selection, existing Deck APIs and metadata-only Reflections candidates.
// [Output] Compact accessible analysis-content panel; opening never starts sync or inference.
// [Pos] Reflections configuration presentation; reuses DeckChatSelector without changing Chat semantics.
// [Sync] 2026-10-23: share inline rerun controls and describe the mounted index as an on-demand reading range.
// [Sync] 2026-10-13: add overall Notion inclusion and Deck-grouped analysis Agent selection.
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getReflectionAnalysisContent, listDecksWithVoices,
  type Deck, type ReflectionAnalysisContentCandidates, type ReflectionAnalysisContentOptions,
} from '../api/voiceApi';
import DeckChatSelector from './deck/DeckChatSelector';
import useReflectionAnalysisContent from '../hooks/useReflectionAnalysisContent';

interface Props {
  value: ReflectionAnalysisContentOptions;
  onChange: (selection: ReflectionAnalysisContentOptions) => void;
  authenticated: boolean;
  inline?: boolean;
}

export default function ReflectionAnalysisContentControls({ value, onChange, authenticated, inline = false }: Props) {
  const { i18n } = useTranslation();
  const zh = i18n.language.startsWith('zh');
  const [open, setOpen] = useState(false);
  const expanded = inline || open;
  const {setRevision,loading,deckLoading,decks,candidates,deckError,ready,status,unavailableAgent}=useReflectionAnalysisContent({value,authenticated,expanded});
  const [layout, setLayout] = useState<{ left: number; width: number; top?: number; bottom?: number; maxHeight: number }>();
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const place = () => {
      const rect = trigger.current?.getBoundingClientRect();
      if (!rect) return;
      const margin = 16, width = Math.min(352, window.innerWidth - margin * 2);
      const above = rect.top - margin, below = window.innerHeight - rect.bottom - margin;
      const upward = above > below;
      setLayout({ width, left: Math.max(margin, Math.min(rect.right - width, window.innerWidth - width - margin)),
        ...(upward ? { bottom: window.innerHeight - rect.top + 8 } : { top: rect.bottom + 8 }),
        maxHeight: Math.max(80, (upward ? above : below) - 8) });
    };
    place();
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !root.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    window.addEventListener('resize', place);
    return () => { document.removeEventListener('pointerdown', outside); window.removeEventListener('resize', place); };
  }, [open]);


  return <div ref={root} style={{ display: inline ? 'block' : 'inline-flex' }} onKeyDown={event => {
    if (!inline && event.key === 'Escape' && !event.defaultPrevented) { event.preventDefault(); setOpen(false); trigger.current?.focus(); }
  }}>
    {!inline && <button type="button" ref={trigger} aria-expanded={open} aria-controls="reflection-analysis-content"
      onClick={() => setOpen(current => !current)} style={{ border: '1px solid var(--color-border-paper)', borderRadius: 24,
        background: 'var(--color-bg-app)', color: 'var(--color-text-body)', padding: '12px 18px', cursor: 'pointer' }}>
      {zh ? '分析内容' : 'Analysis content'} <span aria-hidden="true">{open ? '▴' : '▾'}</span>
    </button>}
    {expanded && (inline || layout) && <div id="reflection-analysis-content" role="region" aria-label={zh ? '分析内容选项' : 'Analysis content options'}
      style={{ ...(inline ? { width: '100%' } : layout), position: inline ? 'relative' : 'fixed', boxSizing: 'border-box', zIndex: inline ? undefined : 900, overflowY: inline ? undefined : 'auto', overscrollBehavior: 'contain',
        background: 'var(--color-bg-surface-solid)', border: '1px solid var(--color-border-paper)', borderRadius: 16,
        padding: 18, boxShadow: inline ? undefined : '0 8px 24px var(--color-shadow-medium)', textAlign: 'left', display: 'grid', gap: 12 }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--color-text-primary)' }}>
        <input type="checkbox" checked={value.include_notion} disabled={!ready && !value.include_notion}
          onChange={event => onChange({ ...value, include_notion: event.target.checked,
            connector_id: event.target.checked ? candidates?.connector_id : undefined,
            snapshot_version: event.target.checked ? candidates?.snapshot_version ?? undefined : undefined })} />
        {zh ? '将 Notion 加入分析' : 'Include Notion in analysis'}
      </label>
      <p role="status" style={{ margin: 0, fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>{status}</p>
      <DeckChatSelector decks={decks} selectedAgentId={value.agent_id} loading={deckLoading}
        error={deckError ? (zh ? '分析 Agent 加载失败' : 'Analysis Agents could not be loaded') : undefined}
        unavailableSelectionLabel={zh ? '所选 Agent 不可用' : 'Selected Agent unavailable'}
        noneLabel={zh ? '默认分析' : 'Default analysis'} triggerLabel={zh ? '分析 Agent' : 'Analysis Agent'}
        onChange={selection => onChange({ ...value, deck_id: selection?.deckId, agent_id: selection?.agentId })} />
      <p style={{ margin: 0, fontSize: 12, color: 'var(--color-text-secondary)' }}>
        {zh ? '所选 Agent 提供本次分析视角。' : 'The selected Agent provides the perspective for this analysis.'}
      </p>
      {unavailableAgent && <p role="alert" style={{ margin: 0, color: 'var(--color-state-error)', fontSize: 12 }}>
        {zh ? '所选分析 Agent 已不可用，请重新选择。' : 'The selected analysis Agent is unavailable. Select it again.'}
      </p>}
      {deckError && <p role="alert" style={{ margin: 0, color: 'var(--color-state-error)', fontSize: 12 }}>
        {zh ? '分析 Agent 加载失败；仍可使用默认分析。' : 'Analysis Agents could not be loaded. Default analysis remains available.'}
      </p>}
      {authenticated && <button type="button" disabled={loading || deckLoading} onClick={() => setRevision(current => current + 1)}
        style={{ justifySelf: 'start', background: 'transparent', color: 'var(--color-action-primary)', border: '1px solid var(--color-border-paper)', borderRadius: 12, padding: '5px 12px', cursor: 'pointer' }}>
        {zh ? '重新加载' : 'Reload'}
      </button>}
    </div>}
  </div>;
}
