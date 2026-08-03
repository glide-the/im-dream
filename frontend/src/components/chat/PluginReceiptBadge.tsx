// [Input] getThreadPluginLoadReceipt API plus the hydrated Deck bound to the thread.
// [Output] Compact badge showing the packed plugin package/version/digest for the
//          active chat thread; clicking opens a popover with the Deck metadata:
//          Deck name, bundled agent names, and the plugin manifest.
// [Pos] Mounted next to the Deck voice badge in ChatView's top-right action row.

import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  getThreadPluginLoadReceipt,
  listClaudePluginInstallations,
  shortDigest,
  type ClaudePluginInstallation,
  type PluginLoadReceipt,
} from '../../api/claudePluginAdminApi';
import type { Deck } from '../../api/voiceApi';
import { COLORS, iconMap } from '../deckVisuals';

interface PluginReceiptBadgeProps {
  activeVoiceId?: string;
  activeVoiceName?: string;
  deck?: Deck;
  threadId: string | null;
}

const sectionLabelStyle: React.CSSProperties = {
  display: 'block',
  marginBottom: 5,
  color: 'var(--color-text-muted)',
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: '.06em',
  textTransform: 'uppercase',
};

// @@@ Receipt polling: 3s cadence for up to ~2 minutes, long enough to cover
// the first run's workspace packing without polling plugin-free threads forever.
const RECEIPT_RETRY_MS = 3000;
const MAX_RECEIPT_ATTEMPTS = 40;

export default function PluginReceiptBadge({
  activeVoiceId,
  activeVoiceName,
  deck,
  threadId,
}: PluginReceiptBadgeProps) {
  const { t, i18n } = useTranslation();
  const language = (i18n.language || 'en').split('-')[0];
  const [receipt, setReceipt] = useState<PluginLoadReceipt | null>(null);
  const [configuredPlugins, setConfiguredPlugins] = useState<ClaudePluginInstallation[] | null>(null);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // @@@ The receipt only exists after the backend has packed the plugin
  // workspace for a run. On the FIRST conversation the badge mounts before
  // packing finishes, so a single fetch would miss it and the badge would
  // stay hidden until the thread is reopened — poll briefly until it appears.
  useEffect(() => {
    let cancelled = false;
    let retryTimer: number | undefined;
    let attempts = 0;
    setReceipt(null);
    setOpen(false);
    if (!threadId) return undefined;

    const load = () => {
      getThreadPluginLoadReceipt(threadId)
        .then((payload) => {
          if (cancelled) return;
          const packed = payload?.receipt?.plugins ?? payload?.launch_manifest?.plugins ?? [];
          if (packed.length > 0) {
            setReceipt(payload);
            return;
          }
          attempts += 1;
          if (attempts < MAX_RECEIPT_ATTEMPTS) {
            retryTimer = window.setTimeout(load, RECEIPT_RETRY_MS);
          }
        })
        .catch(() => {
          if (cancelled) return;
          attempts += 1;
          if (attempts < MAX_RECEIPT_ATTEMPTS) {
            retryTimer = window.setTimeout(load, RECEIPT_RETRY_MS);
          }
        });
    };
    load();
    return () => {
      cancelled = true;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
    };
  }, [threadId]);

  // @@@ Click-outside / Escape closes the metadata popover.
  useEffect(() => {
    if (!open) return undefined;
    const handleMouseDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const plugins = receipt?.receipt?.plugins ?? receipt?.launch_manifest?.plugins ?? [];
  const hasReceiptPlugins = plugins.length > 0;
  const frozen = receipt?.receipt?.frozen === true;
  const deckName = deck
    ? ((language === 'zh' ? deck.name_zh : deck.name_en) || deck.name)
    : null;
  const agents = (deck?.voices || []).filter((voice) => voice.enabled);
  const agentCount = deck
    ? (deck.voices ? agents.length : (deck.voice_count ?? 0))
    : 0;

  // @@@ Config-state plugin list (design §4.3): before the first run packs the
  // workspace there is no receipt, so show the Deck's configured Claude plugin
  // installations instead. Fetched lazily — only while no receipt is available.
  useEffect(() => {
    if (!deck || hasReceiptPlugins) return undefined;
    let cancelled = false;
    setConfiguredPlugins(null);
    listClaudePluginInstallations()
      .then(({ installations }) => {
        if (cancelled) return;
        setConfiguredPlugins(installations.filter((installation) => (
          installation.status === 'ready'
          && (installation.deck_refs ?? []).some(
            (ref) => ref.deck_id === deck.id && ref.enabled,
          )
        )));
      })
      .catch(() => {
        if (!cancelled) setConfiguredPlugins([]);
      });
    return () => {
      cancelled = true;
    };
  }, [deck, hasReceiptPlugins]);

  // @@@ The badge is a DECK CONTEXT badge (design §3): it renders whenever a
  // Deck context exists, even before the first message / pack — the receipt
  // plugin chips are a progressive enhancement on top.
  if (!deck && !hasReceiptPlugins) return null;

  return (
    <div ref={rootRef} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={t('chat.deck.metadataTitle')}
        title={t('chat.deck.metadataTitle')}
        onClick={() => setOpen((value) => !value)}
        style={{
          height: '2rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.35rem',
          padding: '0 0.6rem',
          borderRadius: '0.55rem',
          border: '1px solid #9b7ff555',
          background: open ? '#9b7ff52e' : '#9b7ff518',
          color: '#7a63d8',
          font: 'inherit',
          fontSize: '0.78rem',
          fontWeight: 600,
          maxWidth: '16rem',
          overflow: 'hidden',
          cursor: 'pointer',
        }}
      >
        <span aria-hidden>🧩</span>
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {hasReceiptPlugins ? (
            plugins.map((plugin) => (
              <span key={`${plugin.package_spec}-${plugin.artifact_digest}`} style={{ marginRight: '0.5rem' }}>
                {plugin.package_spec.split('@')[0]} v{plugin.resolved_version ?? '?'} ·{' '}
                {shortDigest(plugin.artifact_digest)}
              </span>
            ))
          ) : (
            deckName
          )}
        </span>
        {frozen ? <span style={{ opacity: 0.75 }}>🔒</span> : null}
      </button>

      {open ? (
        <div
          role="dialog"
          aria-label={t('chat.deck.metadataTitle')}
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            width: 300,
            maxHeight: 380,
            overflowY: 'auto',
            overscrollBehavior: 'contain',
            padding: '12px 14px',
            borderRadius: 10,
            border: '1px solid var(--color-border-neutral)',
            background: 'var(--color-bg-surface-solid)',
            boxShadow: '0 10px 30px var(--color-shadow-medium)',
            color: 'var(--color-text-body)',
            fontSize: 12,
            fontWeight: 400,
            lineHeight: 1.55,
            textAlign: 'left',
            zIndex: 40,
          }}
        >
          <div style={{
            marginBottom: 10,
            color: 'var(--color-text-primary)',
            fontFamily: 'Georgia, "Times New Roman", serif',
            fontSize: 14,
            fontWeight: 600,
          }}>
            {t('chat.deck.metadataTitle')}
            {frozen ? (
              <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--color-text-muted)' }}>
                🔒 {t('chat.deck.metadataFrozen')}
              </span>
            ) : null}
          </div>

          <section style={{ marginBottom: 12 }}>
            <span style={sectionLabelStyle}>{t('chat.deck.metadataDeckName')}</span>
            {deckName ? (
              <strong style={{ fontSize: 13, color: 'var(--color-text-primary)' }}>{deckName}</strong>
            ) : (
              <span style={{ color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                {t('chat.deck.metadataNoDeck')}
              </span>
            )}
          </section>

          {deck ? (
            <section style={{ marginBottom: 12 }}>
              <span style={sectionLabelStyle}>
                {t('chat.deck.metadataAgents')}（{agentCount}）
              </span>
              {agents.length > 0 ? (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                  {agents.map((voice) => {
                    const AgentIcon = iconMap[voice.icon as keyof typeof iconMap] || iconMap.brain;
                    const agentColor = COLORS[voice.color as keyof typeof COLORS]?.hex
                      || 'var(--color-action-link)';
                    const agentName = (language === 'zh' ? voice.name_zh : voice.name_en) || voice.name;
                    // @@@ Highlight the agent actually driving this conversation:
                    // match by voice id first (stable), fall back to the display
                    // name only when the thread→voice derivation was unavailable.
                    const isCurrent = activeVoiceId
                      ? voice.id === activeVoiceId
                      : activeVoiceName !== undefined && agentName === activeVoiceName;
                    return (
                      <span
                        key={voice.id}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '2px 8px',
                          borderRadius: 999,
                          border: `1px solid ${isCurrent ? agentColor : `${agentColor}55`}`,
                          background: isCurrent ? `${agentColor}2e` : `${agentColor}14`,
                          boxShadow: isCurrent ? `0 0 0 1px ${agentColor}55` : 'none',
                          color: isCurrent ? 'var(--color-text-primary)' : 'var(--color-text-body)',
                          fontSize: 11,
                          fontWeight: isCurrent ? 700 : 400,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        <AgentIcon size={11} color={agentColor} />
                        {agentName}
                        {isCurrent ? (
                          <span style={{
                            marginLeft: 2,
                            padding: '0 5px',
                            borderRadius: 999,
                            background: agentColor,
                            color: 'var(--color-text-on-action, #fff)',
                            fontSize: 9,
                            fontWeight: 700,
                            letterSpacing: '.04em',
                          }}>
                            {t('chat.deck.metadataCurrentAgent')}
                          </span>
                        ) : null}
                      </span>
                    );
                  })}
                </div>
              ) : (
                <span style={{ color: 'var(--color-text-secondary)' }}>
                  {t('chat.deck.agentCount', { count: agentCount })}
                </span>
              )}
            </section>
          ) : null}

          <section>
            <span style={sectionLabelStyle}>
              {t('chat.deck.metadataPlugins')}（
              {hasReceiptPlugins ? plugins.length : (configuredPlugins?.length ?? 0)}
              ）
            </span>
            {hasReceiptPlugins ? (
              <div style={{ display: 'grid', gap: 7 }}>
                {plugins.map((plugin) => (
                  <div
                    key={`${plugin.package_spec}-${plugin.artifact_digest}`}
                    title={plugin.artifact_digest}
                    style={{
                      padding: '7px 9px',
                      borderRadius: 7,
                      border: '1px solid var(--color-border-paper)',
                      background: 'var(--color-bg-surface)',
                    }}
                  >
                    <div style={{ color: 'var(--color-text-primary)', fontWeight: 600 }}>
                      {plugin.package_spec}{' '}
                      <span style={{ color: 'var(--color-text-secondary)', fontWeight: 400 }}>
                        v{plugin.resolved_version ?? '?'}
                      </span>
                    </div>
                    <code style={{ fontSize: 10, color: 'var(--color-text-muted)', overflowWrap: 'anywhere' }}>
                      sha256:{shortDigest(plugin.artifact_digest)}
                    </code>
                  </div>
                ))}
              </div>
            ) : configuredPlugins === null ? (
              <span style={{ color: 'var(--color-text-muted)' }}>
                {t('chat.deck.metadataPacking')}
              </span>
            ) : configuredPlugins.length === 0 ? (
              <span style={{ color: 'var(--color-text-secondary)' }}>
                {t('chat.deck.metadataNoPlugins')}
              </span>
            ) : (
              <div style={{ display: 'grid', gap: 7 }}>
                {configuredPlugins.map((installation) => (
                  <div
                    key={installation.id}
                    style={{
                      padding: '7px 9px',
                      borderRadius: 7,
                      border: '1px dashed var(--color-border-paper)',
                      background: 'var(--color-bg-surface)',
                    }}
                  >
                    <div style={{ color: 'var(--color-text-primary)', fontWeight: 600 }}>
                      {installation.package_name}{' '}
                      <span style={{ color: 'var(--color-text-secondary)', fontWeight: 400 }}>
                        v{installation.resolved_version}
                      </span>
                    </div>
                  </div>
                ))}
                <span style={{ color: 'var(--color-text-muted)', fontSize: 11 }}>
                  {t('chat.deck.metadataPacking')}
                </span>
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
