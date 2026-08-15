// [Input] Deck/voice API types, capability-derived Agent type, visual metadata, and Chat handoff.
// [Output] Modal editor for Deck Agent type, metadata, voice prompts, and unified Chat launch.
// [Pos] deck-editor-modal ui in frontend/src/components
// [Sync] 2026-07-08: replace light-only modal panels, form fields, and voice rows with semantic
//                    theme tokens so the Deck editor stays readable in dark mode.
// [Sync] 2026-08-14: add semantic Chat/Dream Agent radio options backed by the
//                    server's optimistic binding revision; remove the duplicate Dream launch action.
// [Sync] 2026-08-15: remove the misleading duplicate "Deck Prompt" editor that
//                    wrote the description field, and expose labelled metadata controls/dialog semantics.
import { useEffect, useMemo, useState } from 'react';
import type { Deck, Voice } from '../api/voiceApi';
import type { DeckAgentType } from '../api/deckPluginApi';
import { COLORS, iconMap } from './deckVisuals';
import type { ActiveChatVoice } from '../lib/chat-schema';
import DeckClaudePluginSelector from './DeckClaudePluginSelector';

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
  onChatWithDeck?: (deckId: string, voiceInfo: ActiveChatVoice) => void;
}

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
  onChatWithDeck,
}: Props) {
  const voices = useMemo(() => deck.voices || [], [deck.voices]);
  const selectedVoice = useMemo(
    () => voices.find(v => v.id === selectedVoiceId) || null,
    [voices, selectedVoiceId]
  );
  const [agentType, setAgentType] = useState<DeckAgentType>(deck.agent_type ?? 'chat');
  const [agentTypeRevision, setAgentTypeRevision] = useState(deck.agent_type_revision ?? 0);
  const [agentTypeSaving, setAgentTypeSaving] = useState(false);
  const [agentTypeError, setAgentTypeError] = useState<string | null>(null);

  useEffect(() => {
    setAgentType(deck.agent_type ?? 'chat');
    setAgentTypeRevision(deck.agent_type_revision ?? 0);
    setAgentTypeError(null);
  }, [deck.agent_type, deck.agent_type_revision, deck.id]);

  const handleAgentTypeChange = async (nextType: DeckAgentType) => {
    if (isSystem || agentTypeSaving || nextType === agentType) return;
    const previousType = agentType;
    setAgentType(nextType);
    setAgentTypeSaving(true);
    setAgentTypeError(null);
    try {
      const revision = await onUpdateAgentType(deck.id, nextType, agentTypeRevision);
      setAgentTypeRevision(revision);
    } catch (error) {
      setAgentType(previousType);
      setAgentTypeError(error instanceof Error ? error.message : 'Agent 类型保存失败，请稍后重试。');
    } finally {
      setAgentTypeSaving(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'var(--color-bg-overlay)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9998,
        padding: 16,
        boxSizing: 'border-box'
      }}
      onClick={onClose}
    >
      <div
        aria-labelledby="deck-editor-title"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        style={{
          width: 'min(1200px, 100%)',
          height: '85vh',
          maxHeight: '85vh',
          background: 'var(--color-bg-app)',
          borderRadius: 14,
          overflow: 'hidden',
          border: '2px solid var(--color-border-paper)',
          boxShadow: '0 16px 36px var(--color-shadow-medium)',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 18px',
          borderBottom: '1px solid var(--color-border-paper)',
          background: 'var(--color-bg-surface-solid)'
        }}>
          <div id="deck-editor-title" style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)', letterSpacing: -0.3 }}>
            Deck Editor
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'var(--color-bg-surface)',
              border: '1px solid var(--color-border-paper)',
              borderRadius: 10,
              padding: '8px 14px',
              cursor: 'pointer',
              fontSize: 13,
              fontWeight: 600,
              color: 'var(--color-text-primary)',
              boxShadow: '0 2px 6px var(--color-shadow-soft)',
              transition: 'all 0.15s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = '0 4px 10px var(--color-shadow-medium)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 2px 6px var(--color-shadow-soft)';
            }}
          >
            Close
          </button>
        </div>

        <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflowY: 'auto' }}>
          {/* Deck metadata. There is no independent Deck prompt field in the persisted contract. */}
          <div>
            <div style={{
              width: '100%',
              background: 'var(--color-bg-surface-solid)',
              border: '2px solid var(--color-border-neutral)',
              borderRadius: 12,
              padding: 16,
              boxShadow: '0 2px 6px var(--color-shadow-soft)',
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
              boxSizing: 'border-box'
            }}>
              <label htmlFor={`deck-name-${deck.id}`} style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--color-text-secondary)',
                letterSpacing: 0.5,
                textTransform: 'uppercase'
              }}>
                Deck Name
              </label>
              <input
                id={`deck-name-${deck.id}`}
                key={`${deck.id}-${deck.name}`}
                type="text"
                defaultValue={deck.name}
                disabled={isSystem}
                onBlur={(e) => {
                  if (!isSystem && e.target.value !== deck.name) {
                    onUpdateDeck(deck.id, { name: e.target.value });
                  }
                }}
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  fontSize: 15,
                  fontWeight: 600,
                  border: '2px solid var(--color-border-neutral)',
                  borderRadius: 8,
                  background: isSystem ? 'var(--color-disabled-bg)' : 'var(--color-bg-paper)',
                  color: 'var(--color-text-primary)',
                  boxSizing: 'border-box'
                }}
              />
              <label htmlFor={`deck-description-${deck.id}`} style={{
                fontSize: 11,
                fontWeight: 600,
                color: 'var(--color-text-secondary)',
                letterSpacing: 0.5,
                textTransform: 'uppercase'
              }}>
                Deck Description
              </label>
              <textarea
                id={`deck-description-${deck.id}`}
                key={`${deck.id}-desc-${deck.description || ''}`}
                defaultValue={deck.description || ''}
                disabled={isSystem}
                onBlur={(e) => {
                  if (!isSystem && e.target.value !== (deck.description || '')) {
                    onUpdateDeck(deck.id, { description: e.target.value });
                  }
                }}
                style={{
                  width: '100%',
                  minHeight: 90,
                  padding: '10px 12px',
                  fontSize: 13,
                  fontFamily: 'monospace',
                  border: '2px solid var(--color-border-neutral)',
                  borderRadius: 8,
                  background: isSystem ? 'var(--color-disabled-bg)' : 'var(--color-bg-paper)',
                  color: 'var(--color-text-primary)',
                  resize: 'vertical',
                  boxSizing: 'border-box',
                  lineHeight: 1.5
                }}
              />
            </div>
          </div>

          <fieldset
            disabled={isSystem || agentTypeSaving}
            style={{
              margin: 0,
              border: '2px solid var(--color-border-neutral)',
              borderRadius: 12,
              padding: 16,
              background: 'var(--color-bg-surface-solid)',
              display: 'grid',
              gap: 10,
            }}
          >
            <legend style={{ padding: '0 0.4rem', fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Agent 类型
            </legend>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
              {([
                ['chat', '普通 Chat Agent', '使用标准消息发送、流式回复与历史会话。'],
                ['dream', 'Dream Agent', '在 Chat 中提交创作目标，并调用既有 Dream 工作流。'],
              ] as const).map(([value, label, description]) => (
                <label
                  key={value}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 10,
                    padding: '0.8rem',
                    borderRadius: 10,
                    border: `1px solid ${agentType === value ? 'var(--color-border-focus)' : 'var(--color-border-paper)'}`,
                    background: agentType === value ? 'var(--color-bg-hover)' : 'var(--color-bg-paper)',
                    cursor: isSystem || agentTypeSaving ? 'not-allowed' : 'pointer',
                  }}
                >
                  <input
                    type="radio"
                    name={`deck-agent-type-${deck.id}`}
                    value={value}
                    checked={agentType === value}
                    onChange={() => void handleAgentTypeChange(value)}
                    style={{ marginTop: 3 }}
                  />
                  <span>
                    <span style={{ display: 'block', fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>{label}</span>
                    <span style={{ display: 'block', marginTop: 3, fontSize: 12, lineHeight: 1.5, color: 'var(--color-text-secondary)' }}>{description}</span>
                  </span>
                </label>
              ))}
            </div>
            {agentTypeSaving ? <div role="status" style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>正在保存 Agent 类型…</div> : null}
            {agentTypeError ? <div role="alert" style={{ fontSize: 12, color: 'var(--color-state-error)' }}>{agentTypeError}</div> : null}
          </fieldset>

          {/* Claude Code plugins: shared-installation references (digest-pinned). */}
          <DeckClaudePluginSelector deckId={deck.id} disabled={isSystem} />

          <div style={{ height: 1, background: 'var(--color-border-paper)', width: '100%' }} />

          <div style={{
            display: 'flex',
            gap: 16,
            alignItems: 'stretch',
            flexWrap: 'wrap',
            flex: 1,
            minHeight: 280
          }}>
            {/* Left column: voice list */}
            <div style={{
              width: 320,
              flexShrink: 0,
              flexGrow: 0,
              minWidth: 260,
              maxHeight: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: 12
            }}>
              <div style={{
                background: 'var(--color-bg-surface-solid)',
                border: '2px solid var(--color-border-neutral)',
                borderRadius: 10,
                padding: 14,
                boxShadow: '0 2px 6px var(--color-shadow-soft)',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
                flex: 1,
                minHeight: 200,
                overflowY: 'auto'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between'
                }}>
                  <div style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                    letterSpacing: 0.5,
                    textTransform: 'uppercase'
                  }}>
                    Agents
                  </div>
                  {!isSystem && (
                    <button
                      onClick={() => onAddVoice(deck.id)}
                      disabled={creatingVoiceId === deck.id}
                      style={{
                        border: '1px dashed var(--color-action-link)',
                        background: 'transparent',
                        color: 'var(--color-action-link)',
                        padding: '6px 10px',
                        borderRadius: 6,
                        cursor: creatingVoiceId === deck.id ? 'not-allowed' : 'pointer',
                        fontSize: 12
                      }}
                    >
                      {creatingVoiceId === deck.id ? 'Adding…' : '+ Add'}
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto' }}>
                  {voices.length === 0 && (
                    <div style={{ color: 'var(--color-text-muted)', fontSize: 13, fontStyle: 'italic' }}>
                      No voices in this deck yet
                    </div>
                  )}
                  {voices.map(voice => {
                    const VoiceIcon = iconMap[voice.icon as keyof typeof iconMap] || iconMap.brain;
                    const voiceColor = COLORS[voice.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
                    const isSelected = selectedVoiceId === voice.id;

                    return (
                      <div
                        key={voice.id}
                        onClick={() => onSelectVoice(voice.id)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          padding: '10px 12px',
                          borderRadius: 8,
                          cursor: 'pointer',
                          border: isSelected ? `2px solid ${voiceColor}` : '2px solid transparent',
                          background: isSelected ? `${voiceColor}15` : 'var(--color-bg-surface)',
                          transition: 'all 0.15s',
                          opacity: voice.enabled ? 1 : 0.55
                        }}
                      >
                        <div style={{
                          width: 32,
                          height: 32,
                          borderRadius: 16,
                          background: voiceColor,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: 'var(--color-text-on-action)',
                          flexShrink: 0,
                          boxShadow: '0 2px 6px var(--color-shadow-medium)'
                        }}>
                          <VoiceIcon size={16} />
                        </div>
                        <div style={{
                          flex: 1,
                          minWidth: 0,
                          fontSize: 14,
                          fontWeight: isSelected ? 700 : 500,
                          color: 'var(--color-text-primary)',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {voice.name}
                        </div>
                        <input
                          aria-label={`Toggle ${voice.name}`}
                          type="checkbox"
                          checked={voice.enabled}
                          onClick={(e) => e.stopPropagation()}
                          onChange={() => onToggleVoice(voice.id, voice.enabled)}
                          disabled={isSystem}
                          style={{ cursor: 'pointer' }}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Right column: selected voice editor */}
            <div style={{
              flex: 1,
              minWidth: 0,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 12
            }}>
              {selectedVoice ? (() => {
                const voiceColor = COLORS[selectedVoice.color as keyof typeof COLORS]?.hex || 'var(--color-action-link)';
                const VoiceIcon = iconMap[selectedVoice.icon as keyof typeof iconMap] || iconMap.brain;

                return (
                  <div
                    key={selectedVoice.id}
                    style={{
                      flex: 1,
                      minHeight: 0,
                      background: 'var(--color-bg-surface-solid)',
                      border: `2px solid ${voiceColor}`,
                      borderRadius: 12,
                      padding: 18,
                      boxShadow: `0 4px 10px ${voiceColor}25`,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 12
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      flexWrap: 'wrap'
                    }}>
                      <div style={{
                        width: 44,
                        height: 44,
                        borderRadius: 22,
                        background: voiceColor,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--color-text-on-action)',
                        boxShadow: `0 3px 8px ${voiceColor}40`
                      }}>
                        <VoiceIcon size={22} />
                      </div>

                      <input
                        aria-label="Agent Name"
                        key={`${selectedVoice.id}-${selectedVoice.name}`}
                        type="text"
                        defaultValue={selectedVoice.name}
                        disabled={isSystem}
                        onBlur={(e) => {
                          if (!isSystem && e.target.value !== selectedVoice.name) {
                            onUpdateVoice(selectedVoice.id, { name: e.target.value });
                          }
                        }}
                        style={{
                          flex: 1,
                          minWidth: 140,
                          border: 'none',
                          borderBottom: '2px solid var(--color-border-neutral)',
                          fontSize: 18,
                          fontWeight: 700,
                          padding: '6px 4px',
                          outline: 'none',
                          background: 'transparent'
                        }}
                      />

                      <select
                        aria-label="Agent Icon"
                        value={selectedVoice.icon}
                        disabled={isSystem}
                        onChange={(e) => onUpdateVoice(selectedVoice.id, { icon: e.target.value })}
                        style={{
                          padding: '8px 10px',
                          borderRadius: 6,
                          border: '1px solid var(--color-border-neutral)',
                          background: 'var(--color-bg-paper)',
                          color: 'var(--color-text-primary)',
                          fontSize: 12,
                          cursor: isSystem ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {Object.keys(iconMap).map((iconName) => (
                          <option key={iconName} value={iconName}>{iconName}</option>
                        ))}
                      </select>

                      <select
                        aria-label="Agent Color"
                        value={selectedVoice.color}
                        disabled={isSystem}
                        onChange={(e) => onUpdateVoice(selectedVoice.id, { color: e.target.value })}
                        style={{
                          padding: '8px 10px',
                          borderRadius: 6,
                          border: '1px solid var(--color-border-neutral)',
                          background: 'var(--color-bg-paper)',
                          color: 'var(--color-text-primary)',
                          fontSize: 12,
                          cursor: isSystem ? 'not-allowed' : 'pointer'
                        }}
                      >
                        {Object.entries(COLORS).map(([colorName, data]) => (
                          <option key={colorName} value={colorName}>{data.label}</option>
                        ))}
                      </select>

                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--color-text-body)' }}>
                        <input
                          type="checkbox"
                          checked={selectedVoice.enabled}
                          disabled={isSystem}
                          onChange={() => onToggleVoice(selectedVoice.id, selectedVoice.enabled)}
                        />
                        Enabled
                      </label>

                      {!isSystem && (
                        <button
                          onClick={() => onDeleteVoice(selectedVoice.id)}
                          style={{
                            padding: '8px 12px',
                            background: 'var(--color-bg-paper)',
                            border: '1px solid var(--color-border-neutral)',
                            borderRadius: 6,
                            cursor: 'pointer',
                            fontSize: 12,
                            color: 'var(--color-state-error)'
                          }}
                        >
                          Delete
                        </button>
                      )}

                      {onChatWithDeck && (
                        <button
                          onClick={() => {
                            // "Chat →" = preselect this Deck in the chat input
                            // dock together with this Agent.
                            onChatWithDeck(deck.id, {
                              id: selectedVoice.id,
                              name: selectedVoice.name,
                              systemPrompt: selectedVoice.system_prompt,
                              icon: selectedVoice.icon,
                              color: selectedVoice.color,
                            });
                          }}
                          style={{
                            padding: '8px 12px',
                            background: 'var(--color-action-link)',
                            border: 'none',
                            borderRadius: 6,
                            cursor: 'pointer',
                            fontSize: 12,
                            color: 'var(--color-text-on-action)'
                          }}
                        >
                          在 Chat 中使用 →
                        </button>
                      )}
                    </div>

                    <label htmlFor={`agent-prompt-${selectedVoice.id}`} style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: 'var(--color-text-secondary)',
                      letterSpacing: 0.5,
                      textTransform: 'uppercase'
                    }}>
                      Agent Prompt
                    </label>
                    <textarea
                      id={`agent-prompt-${selectedVoice.id}`}
                      key={`${selectedVoice.id}-${selectedVoice.system_prompt}`}
                      defaultValue={selectedVoice.system_prompt}
                      disabled={isSystem}
                      onBlur={(e) => {
                        if (!isSystem && e.target.value !== selectedVoice.system_prompt) {
                          onUpdateVoice(selectedVoice.id, { system_prompt: e.target.value });
                        }
                      }}
                      style={{
                        flex: 1,
                        width: '100%',
                        minHeight: 0,
                        padding: 12,
                        fontSize: 13,
                        fontFamily: 'monospace',
                        border: '2px solid var(--color-border-neutral)',
                        borderRadius: 8,
                        background: isSystem ? 'var(--color-disabled-bg)' : 'var(--color-bg-paper)',
                        color: 'var(--color-text-primary)',
                        resize: 'vertical',
                        boxSizing: 'border-box',
                        lineHeight: 1.6
                      }}
                    />
                  </div>
                );
              })() : (
                <div style={{
                  flex: 1,
                  background: 'var(--color-bg-surface-solid)',
                  border: '2px dashed var(--color-border-paper)',
                  borderRadius: 12,
                  padding: 40,
                  color: 'var(--color-text-muted)',
                  fontSize: 14,
                  textAlign: 'center'
                }}>
                  Select an agent from the list to edit
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
