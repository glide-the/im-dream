// [Input] Deck/Voice CRUD, real runtime-version facts, plugin refs, and Chat handoff.
// [Output] Compact IM maintenance dialog with overview, Agents, plugins, and folded version history.
// [Pos] Deck maintenance modal in frontend/src/components.
// [Sync] 2026-08-16: replace the legacy 1200px nested-card editor with the PDF-led 920px
//                    segmented dialog and restore real binding-version management.

import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import type { Deck, Voice } from '../api/voiceApi';
import type { DeckAgentType } from '../api/deckPluginApi';
import type { ActiveChatVoice } from '../lib/chat-schema';
import { useDeckContentVersions } from '../hooks/useDeckContentVersions';
import DeckClaudePluginSelector from './DeckClaudePluginSelector';
import DeckVersionPanel from './deck/DeckVersionPanel';
import DeckVersionSubmitDialog from './deck/DeckVersionSubmitDialog';
import { COLORS, iconMap } from './deckVisuals';
import './DeckEditorModal.css';

type EditorSection = 'overview' | 'agents' | 'plugins';

interface Props {
  deck: Deck;
  isSystem: boolean;
  selectedVoiceId: string | null;
  onSelectVoice: (voiceId: string | null) => void;
  onClose: () => void;
  creatingVoiceId: string | null;
  onAddVoice: (deckId: string) => Promise<void>;
  onUpdateDeck: (deckId: string, data: Partial<Deck>) => Promise<void>;
  onUpdateAgentType: (
    deckId: string,
    agentType: DeckAgentType,
    expectedBindingRevision: number,
  ) => Promise<number>;
  onUpdateVoice: (voiceId: string, data: Partial<Voice>) => Promise<void>;
  onToggleVoice: (voiceId: string, currentEnabled: boolean) => Promise<void>;
  onDeleteVoice: (voiceId: string) => Promise<void>;
  onVersionChanged: () => Promise<void>;
  onChatWithDeck?: (deckId: string, voiceInfo: ActiveChatVoice) => void;
}

const SECTIONS: Array<{ id: EditorSection; label: string }> = [
  { id: 'overview', label: '概览' },
  { id: 'agents', label: 'Agents' },
  { id: 'plugins', label: 'Claude 插件' },
];

export default function DeckEditorModal({
  deck,
  isSystem,
  selectedVoiceId,
  onSelectVoice,
  onClose,
  creatingVoiceId,
  onAddVoice,
  onUpdateDeck,
  onUpdateAgentType,
  onUpdateVoice,
  onToggleVoice,
  onDeleteVoice,
  onVersionChanged,
  onChatWithDeck,
}: Props) {
  const voices = useMemo(() => deck.voices || [], [deck.voices]);
  const selectedVoice = useMemo(
    () => voices.find((voice) => voice.id === selectedVoiceId) || null,
    [selectedVoiceId, voices],
  );
  const [section, setSection] = useState<EditorSection>('overview');
  const [historyOpen, setHistoryOpen] = useState(false);
  const historyTriggerRef = useRef<HTMLButtonElement>(null);
  const [agentType, setAgentType] = useState<DeckAgentType>(deck.agent_type ?? 'chat');
  const [agentTypeRevision, setAgentTypeRevision] = useState(deck.agent_type_revision ?? 0);
  const [agentTypeSaving, setAgentTypeSaving] = useState(false);
  const [agentTypeError, setAgentTypeError] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const contentVersions = useDeckContentVersions(deck.id);
  const DeckIcon = iconMap[deck.icon as keyof typeof iconMap] || iconMap.brain;
  const deckAccent = COLORS[deck.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';

  useEffect(() => {
    setAgentType(deck.agent_type ?? 'chat');
    setAgentTypeRevision(deck.agent_type_revision ?? 0);
    setAgentTypeError(null);
  }, [deck.agent_type, deck.agent_type_revision, deck.id]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      if (historyOpen) {
        setHistoryOpen(false);
        requestAnimationFrame(() => historyTriggerRef.current?.focus());
      } else {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [historyOpen, onClose]);

  const closeHistory = () => {
    setHistoryOpen(false);
    requestAnimationFrame(() => historyTriggerRef.current?.focus());
  };

  const runDraftMutation = async (action: () => Promise<void>) => {
    setMutationError(null);
    try {
      await action();
      await contentVersions.refresh(historyOpen);
    } catch (error) {
      const message = error instanceof Error ? error.message : '保存失败，请重试。';
      setMutationError(message);
      throw error;
    }
  };

  const handleAgentTypeChange = async (nextType: DeckAgentType) => {
    if (isSystem || agentTypeSaving || nextType === agentType) return;
    const previousType = agentType;
    setAgentType(nextType);
    setAgentTypeSaving(true);
    setAgentTypeError(null);
    try {
      const revision = await onUpdateAgentType(deck.id, nextType, agentTypeRevision);
      setAgentTypeRevision(revision);
      await contentVersions.refresh(historyOpen);
    } catch (error) {
      setAgentType(previousType);
      setAgentTypeError(error instanceof Error ? error.message : 'Agent 类型保存失败，请稍后重试。');
    } finally {
      setAgentTypeSaving(false);
    }
  };

  return (
    <div className="deck-editor-backdrop" onClick={onClose} role="presentation">
      <section
        aria-labelledby="deck-editor-title"
        aria-modal="true"
        className={`deck-editor${historyOpen ? ' has-history' : ''}`}
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <header className="deck-editor__header">
          <div className="deck-editor__identity">
            <span
              aria-hidden="true"
              className="deck-editor__deck-icon"
              style={{ '--deck-editor-accent': deckAccent } as CSSProperties}
            >
              <DeckIcon size={20} />
            </span>
            <div>
              <h1 id="deck-editor-title">{deck.name || 'New Deck'}</h1>
              <p>
                {contentVersions.loading ? '正在读取内容版本' : contentVersions.state?.latest_version ? `内容版本 v${contentVersions.state.latest_version}` : '内容版本未提交'}
                {contentVersions.state?.dirty ? ` · 草稿 r${contentVersions.state.draft_revision}` : ''}
                {deck.deck_plugin_version ? ` · 运行插件 v${deck.deck_plugin_version}` : ''}
                {isSystem ? ' · 系统 Deck' : ''}
              </p>
            </div>
          </div>
          <div className="deck-editor__header-actions">
            {!isSystem && (
              <button
                className="deck-primary-button deck-version-submit-trigger"
                disabled={contentVersions.loading || contentVersions.submitting || !contentVersions.state?.dirty || contentVersions.capabilityUnavailable}
                onClick={() => void contentVersions.prepare()}
                type="button"
              >
                {contentVersions.submitting ? '准备中…' : `提交 v${contentVersions.state?.next_version ?? 1}`}
              </button>
            )}
            <button
              aria-expanded={historyOpen}
              className="deck-version-trigger"
              onClick={() => setHistoryOpen((value) => !value)}
              ref={historyTriggerRef}
              type="button"
            >
              <span aria-hidden="true">◷</span>
              版本记录
            </button>
            <button aria-label="Close" className="deck-icon-button" onClick={onClose} type="button">×</button>
          </div>
        </header>

        <nav aria-label="Deck maintenance sections" className="deck-editor__tabs" role="tablist">
          {SECTIONS.map((candidate) => (
            <button
              aria-controls={`deck-editor-panel-${candidate.id}`}
              aria-selected={section === candidate.id}
              id={`deck-editor-tab-${candidate.id}`}
              key={candidate.id}
              onClick={() => setSection(candidate.id)}
              role="tab"
              type="button"
            >
              {candidate.label}
              {candidate.id === 'agents' && <span>{voices.length}</span>}
            </button>
          ))}
        </nav>

        <div className="deck-editor__workspace">
          <main
            aria-labelledby={`deck-editor-tab-${section}`}
            className="deck-editor__main"
            id={`deck-editor-panel-${section}`}
            role="tabpanel"
          >
            {section === 'overview' && (
              <div className="deck-editor-panel deck-editor-overview">
                <div className="deck-editor-panel__heading">
                  <div><h2>Deck 信息</h2><p>基础信息和对话入口类型。</p></div>
                  <span className={`deck-editor-state${deck.enabled ? ' is-enabled' : ''}`}>
                    {deck.enabled ? '已启用' : '已停用'}
                  </span>
                </div>

                <div className="deck-field-group">
                  <label htmlFor={`deck-name-${deck.id}`}>Deck Name</label>
                  <input
                    defaultValue={deck.name}
                    disabled={isSystem}
                    id={`deck-name-${deck.id}`}
                    key={`${deck.id}-${deck.name}`}
                    onBlur={(event) => {
                      if (!isSystem && event.target.value !== deck.name) {
                        void runDraftMutation(() => onUpdateDeck(deck.id, { name: event.target.value })).catch(() => undefined);
                      }
                    }}
                    type="text"
                  />
                </div>

                <div className="deck-field-group">
                  <label htmlFor={`deck-description-${deck.id}`}>Deck Description</label>
                  <textarea
                    defaultValue={deck.description || ''}
                    disabled={isSystem}
                    id={`deck-description-${deck.id}`}
                    key={`${deck.id}-${deck.description || ''}`}
                    onBlur={(event) => {
                      if (!isSystem && event.target.value !== (deck.description || '')) {
                        void runDraftMutation(() => onUpdateDeck(deck.id, { description: event.target.value })).catch(() => undefined);
                      }
                    }}
                    rows={4}
                  />
                </div>

                <fieldset className="deck-agent-type" disabled={isSystem || agentTypeSaving}>
                  <legend>Agent 类型</legend>
                  <div className="deck-agent-type__options">
                    {([
                      ['chat', '普通 Chat Agent', '标准对话、流式回复与历史会话。'],
                      ['dream', 'Dream Agent', '在 Chat 中提交目标并进入 Dream 创作。'],
                    ] as const).map(([value, label, description]) => (
                      <label className={agentType === value ? 'is-selected' : ''} key={value}>
                        <input
                          checked={agentType === value}
                          name={`deck-agent-type-${deck.id}`}
                          onChange={() => void handleAgentTypeChange(value)}
                          type="radio"
                          value={value}
                        />
                        <span><strong>{label}</strong><small>{description}</small></span>
                      </label>
                    ))}
                  </div>
                  {agentTypeSaving && <p className="deck-field-status" role="status">正在保存 Agent 类型…</p>}
                  {agentTypeError && <p className="deck-field-status is-error" role="alert">{agentTypeError}</p>}
                </fieldset>
              </div>
            )}

            {section === 'agents' && (
              <div className="deck-editor-panel deck-agents">
                <aside className="deck-agents__list">
                  <div className="deck-editor-panel__heading">
                    <div><h2>Agents</h2><p>{voices.length} 个配置</p></div>
                    {!isSystem && (
                      <button
                        className="deck-secondary-button"
                        disabled={creatingVoiceId === deck.id}
                        onClick={() => void runDraftMutation(() => onAddVoice(deck.id)).catch(() => undefined)}
                        type="button"
                      >
                        {creatingVoiceId === deck.id ? 'Adding…' : '+ Add'}
                      </button>
                    )}
                  </div>
                  <div className="deck-agents__items" role="list">
                    {voices.length === 0 && <p className="deck-empty-copy">No voices in this deck yet</p>}
                    {voices.map((voice) => {
                      const VoiceIcon = iconMap[voice.icon as keyof typeof iconMap] || iconMap.brain;
                      const accent = COLORS[voice.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
                      return (
                        <div
                          className={`deck-agent-row${selectedVoiceId === voice.id ? ' is-selected' : ''}${voice.enabled ? '' : ' is-disabled'}`}
                          key={voice.id}
                          role="listitem"
                          style={{ '--deck-agent-accent': accent } as CSSProperties}
                        >
                          <button onClick={() => onSelectVoice(voice.id)} type="button">
                            <span aria-hidden="true"><VoiceIcon size={16} /></span>
                            <strong>{voice.name}</strong>
                          </button>
                          <input
                            aria-label={`Toggle ${voice.name}`}
                            checked={voice.enabled}
                            disabled={isSystem}
                            onChange={() => void runDraftMutation(() => onToggleVoice(voice.id, voice.enabled)).catch(() => undefined)}
                            type="checkbox"
                          />
                        </div>
                      );
                    })}
                  </div>
                </aside>

                <section className="deck-agent-editor">
                  {selectedVoice ? (() => {
                    const VoiceIcon = iconMap[selectedVoice.icon as keyof typeof iconMap] || iconMap.brain;
                    const accent = COLORS[selectedVoice.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
                    return (
                      <div className="deck-agent-editor__content" style={{ '--deck-agent-accent': accent } as CSSProperties}>
                        <header className="deck-agent-editor__header">
                          <span aria-hidden="true" className="deck-agent-editor__avatar"><VoiceIcon size={18} /></span>
                          <input
                            aria-label="Agent Name"
                            defaultValue={selectedVoice.name}
                            disabled={isSystem}
                            key={`${selectedVoice.id}-${selectedVoice.name}`}
                            onBlur={(event) => {
                              if (!isSystem && event.target.value !== selectedVoice.name) {
                                void runDraftMutation(() => onUpdateVoice(selectedVoice.id, { name: event.target.value })).catch(() => undefined);
                              }
                            }}
                            type="text"
                          />
                        </header>

                        <div className="deck-agent-editor__tools">
                          <select
                            aria-label="Agent Icon"
                            disabled={isSystem}
                            onChange={(event) => void runDraftMutation(() => onUpdateVoice(selectedVoice.id, { icon: event.target.value })).catch(() => undefined)}
                            value={selectedVoice.icon}
                          >
                            {Object.keys(iconMap).map((iconName) => <option key={iconName} value={iconName}>{iconName}</option>)}
                          </select>
                          <select
                            aria-label="Agent Color"
                            disabled={isSystem}
                            onChange={(event) => void runDraftMutation(() => onUpdateVoice(selectedVoice.id, { color: event.target.value })).catch(() => undefined)}
                            value={selectedVoice.color}
                          >
                            {Object.entries(COLORS).map(([name, data]) => <option key={name} value={name}>{data.label}</option>)}
                          </select>
                          <label className="deck-checkbox"><input checked={selectedVoice.enabled} disabled={isSystem} onChange={() => void runDraftMutation(() => onToggleVoice(selectedVoice.id, selectedVoice.enabled)).catch(() => undefined)} type="checkbox" /> Enabled</label>
                          {!isSystem && <button className="deck-danger-button" onClick={() => void runDraftMutation(() => onDeleteVoice(selectedVoice.id)).catch(() => undefined)} type="button">Delete</button>}
                          {onChatWithDeck && (
                            <button
                              className="deck-primary-button"
                              onClick={() => onChatWithDeck(deck.id, {
                                id: selectedVoice.id,
                                name: selectedVoice.name,
                                systemPrompt: selectedVoice.system_prompt,
                                icon: selectedVoice.icon,
                                color: selectedVoice.color,
                              })}
                              type="button"
                            >
                              在 Chat 中使用 →
                            </button>
                          )}
                        </div>

                        <div className="deck-field-group deck-agent-editor__prompt">
                          <label htmlFor={`agent-prompt-${selectedVoice.id}`}>Agent Prompt</label>
                          <textarea
                            defaultValue={selectedVoice.system_prompt}
                            disabled={isSystem}
                            id={`agent-prompt-${selectedVoice.id}`}
                            key={`${selectedVoice.id}-${selectedVoice.system_prompt}`}
                            onBlur={(event) => {
                              if (!isSystem && event.target.value !== selectedVoice.system_prompt) {
                                void runDraftMutation(() => onUpdateVoice(selectedVoice.id, { system_prompt: event.target.value })).catch(() => undefined);
                              }
                            }}
                          />
                        </div>
                      </div>
                    );
                  })() : <p className="deck-empty-copy deck-agent-editor__empty">Select an agent from the list to edit</p>}
                </section>
              </div>
            )}

            {section === 'plugins' && (
              <div className="deck-editor-panel deck-editor-plugins">
                <div className="deck-editor-panel__heading"><div><h2>Claude 插件</h2><p>选择已安装、ready 且 digest 校验通过的插件引用。</p></div></div>
                <DeckClaudePluginSelector deckId={deck.id} disabled={isSystem} onSaved={() => contentVersions.refresh(historyOpen).then(() => undefined)} />
              </div>
            )}
          </main>

          {historyOpen && (
            <DeckVersionPanel
              deckId={deck.id}
              isSystem={isSystem}
              onClose={closeHistory}
              onVersionChanged={onVersionChanged}
            />
          )}
        </div>
        {(mutationError || contentVersions.error) && (
          <div className="deck-editor__feedback" role="alert">{mutationError || contentVersions.error}</div>
        )}
      </section>
      {contentVersions.preview && (
        <DeckVersionSubmitDialog
          deckName={deck.name || 'Deck'}
          error={contentVersions.error}
          onCancel={contentVersions.clearPreview}
          onConfirm={async (description) => {
            const committed = await contentVersions.commit(description);
            if (!committed) return false;
            await onVersionChanged();
            return true;
          }}
          preview={contentVersions.preview}
          submitting={contentVersions.submitting}
        />
      )}
    </div>
  );
}
