// [Input] State config, selected emotional state, session timestamp, and user_session labels.
// [Output] Render the emotional state chooser and compact writing-session metadata line.
// [Pos] state-chooser component in frontend/app/_dream/components
// [Sync] 2026-11-01: mobile page navigation, contained touch scrolling and cancellation of pending selection on hide.
// [Sync] 2026-06-01: show current user_session.labels beside the collapsed state indicator.
import { useState, useEffect, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import type { WritingChooserView } from './Editor/WritingDocument.protocol';
import { useTranslation } from 'react-i18next';
import { StateCube } from './StateCube';
import type { SessionLabels, StateConfig } from '../api/voiceApi';
import { getDateLocale } from '../i18n';
import { parseFlexibleTimestamp } from '../utils/timezone';

interface Props {
  stateConfig: StateConfig;
  selectedState: string | null;
  selectedStateLoading?: boolean;
  createdAt?: string;  // ISO timestamp recorded when the session was created
  sessionLabels?: SessionLabels;
  onChoose: (stateId: string) => void;
  mobile?: boolean;
  active?: boolean;
  navigationTarget?: HTMLElement | null;
  overlayTarget?: HTMLElement | null;
  openNonce?: number;
  onViewChange?: (view: WritingChooserView) => void;
}

export default function StateChooser({
  stateConfig,
  selectedState,
  selectedStateLoading = false,
  createdAt,
  sessionLabels = [],
  onChoose, mobile = false, active = true, navigationTarget, overlayTarget, openNonce, onViewChange
}: Props) {
  const { i18n } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);
  const [shouldAnimate, setShouldAnimate] = useState(false);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const selectionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef({active, onChoose, onViewChange});
  latest.current = {active, onChoose, onViewChange};
  const deliveredOpen = useRef(0);
  const indicatorRef = useRef<HTMLDivElement>(null);
  const visibleSessionLabels = useMemo(() => {
    return sessionLabels
      .map(label => String(label).trim())
      .filter(label => label.length > 0);
  }, [sessionLabels]);
  const sessionLabelsTitle = visibleSessionLabels.join(', ');

  useEffect(() => {
    if (!active) {
      if (selectionTimer.current !== null) clearTimeout(selectionTimer.current);
      selectionTimer.current = null;
      setIsExpanded(false);
      setIsFadingOut(false);
      return;
    }
    if (selectedStateLoading) return;
    setIsExpanded(!selectedState);
    if (selectedState) {
      setShouldAnimate(true);
      const timer = setTimeout(() => setShouldAnimate(false), 600);
      return () => clearTimeout(timer);
    }
  }, [selectedState, selectedStateLoading, active]);

  useEffect(() => () => {
    if (selectionTimer.current !== null) clearTimeout(selectionTimer.current);
  }, []);

  const open = () => {
    if (!latest.current.active || selectedStateLoading || selectionTimer.current !== null) return;
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    setIsExpanded(true);
  };
  useEffect(() => {
    if (!active || selectedStateLoading || !openNonce || openNonce <= deliveredOpen.current) return;
    deliveredOpen.current = openNonce;
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    setIsExpanded(true);
  }, [openNonce, active, selectedStateLoading]);

  const selectedStateData = selectedState ? stateConfig.states[selectedState] : null;

  const expanded = active && !selectedStateLoading && (!selectedStateData || isExpanded);
  const name = selectedStateData?.name ?? '';
  useEffect(() => {
    latest.current.onViewChange?.({loading: selectedStateLoading, selectedStateId: selectedState, name, expanded});
  }, [selectedStateLoading, selectedState, name, expanded]);

  // @@@ Use createdAt if provided, otherwise use today
  const timestamp = createdAt ? parseFlexibleTimestamp(createdAt) : null;
  const displayDate = timestamp ?? new Date();

  const dateLocale = getDateLocale(i18n.language);
  const dateString = displayDate.toLocaleDateString(dateLocale, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  });

  const handleStateSelect = (stateId: string) => {
    if (!latest.current.active || selectionTimer.current !== null) return;
    setIsFadingOut(true);
    selectionTimer.current = setTimeout(() => {
      selectionTimer.current = null;
      if (!latest.current.active) return;
      setIsExpanded(false);
      setIsFadingOut(false);
      latest.current.onChoose(stateId);
    }, 800);
  };

  // @@@ Mini icon generator for collapsed state (24px version)
  const getMiniStateIcon = (stateId: string) => {
    const iconProps = { width: 24, height: 24, viewBox: "0 0 100 100" };

    switch(stateId.toLowerCase()) {
      case 'happy':
        return (
          <svg {...iconProps}>
            <circle cx="50" cy="50" r="40" fill="none" stroke="#FFD93D" strokeWidth="6"/>
            <path d="M 35 60 Q 50 75 65 60" fill="none" stroke="#FFD93D" strokeWidth="6" strokeLinecap="round"/>
            <circle cx="38" cy="40" r="4" fill="#FFD93D"/>
            <circle cx="62" cy="40" r="4" fill="#FFD93D"/>
          </svg>
        );
      case 'ok':
        return (
          <svg {...iconProps}>
            <circle cx="50" cy="50" r="40" fill="none" stroke="#95D5B2" strokeWidth="6"/>
            <line x1="35" y1="60" x2="65" y2="60" stroke="#95D5B2" strokeWidth="6" strokeLinecap="round"/>
            <circle cx="38" cy="40" r="4" fill="#95D5B2"/>
            <circle cx="62" cy="40" r="4" fill="#95D5B2"/>
          </svg>
        );
      case 'unhappy':
        return (
          <svg {...iconProps}>
            <circle cx="50" cy="50" r="40" fill="none" stroke="#A8DADC" strokeWidth="6"/>
            <path d="M 35 65 Q 50 50 65 65" fill="none" stroke="#A8DADC" strokeWidth="6" strokeLinecap="round"/>
            <circle cx="38" cy="40" r="4" fill="#A8DADC"/>
            <circle cx="62" cy="40" r="4" fill="#A8DADC"/>
          </svg>
        );
      default:
        return (
          <svg {...iconProps}>
            <circle cx="50" cy="50" r="35" fill="none" stroke="#999" strokeWidth="4"/>
          </svg>
        );
    }
  };

  if (selectedStateLoading && !mobile) {
    return <div style={{ height: '32px' }} />;
  }

  const overlay = (
    <div className={mobile ? "state-chooser-overlay state-chooser-overlay--mobile" : "state-chooser-overlay"} role="dialog" aria-label={stateConfig.greeting || "Choose your emotion"} style={{
          position: mobile ? 'absolute' : 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'var(--color-bg-paper)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: mobile ? undefined : 'center',
          alignItems: mobile ? 'stretch' : 'center',
          zIndex: 9999,
          opacity: isFadingOut ? 0 : 1,
          transition: 'opacity 0.8s ease-out',
          pointerEvents: mobile ? 'auto' : isFadingOut ? 'none' : 'auto'
        }}>
          <div className="state-chooser-scroll" style={mobile ? undefined : {display: 'contents'}}><div className="state-chooser-body" style={mobile ? undefined : {display: 'contents'}}>
          {/* Header text */}
          <h1 className="state-chooser-greeting" style={{
            fontSize: 48,
            fontWeight: 300,
            color: 'var(--color-text-body)',
            marginBottom: 60,
            textAlign: 'center',
            letterSpacing: '0.05em',
            opacity: isFadingOut ? 0 : 1,
            transform: isFadingOut ? 'translateY(-20px)' : 'translateY(0)',
            transition: 'all 0.8s ease-out'
          }}>
            {stateConfig.greeting || "What's your emotion today?"}
          </h1>

          {/* 3D Cube */}
          <div className="state-chooser-cube" style={{
            opacity: isFadingOut ? 0 : 1,
            transform: isFadingOut ? 'scale(0.9)' : 'scale(1)',
            transition: 'all 0.8s ease-out'
          }}>
            <StateCube
              mobile={mobile}
              active={active && !isFadingOut}
              stateConfig={stateConfig}
              onStateSelect={handleStateSelect}
            />
          </div>

          {/* Helper text */}
          <p style={{
            marginTop: 40,
            fontSize: 14,
            color: 'var(--color-text-muted)',
            textAlign: 'center',
            opacity: isFadingOut ? 0 : 1,
            transition: 'opacity 0.8s ease-out'
          }}>
            {i18n.language.startsWith('zh') ? '选择心情，开始写作' : 'Click a state to begin writing'}
          </p>
        </div></div>
        </div>
  );
  const actionLabel = selectedStateLoading
    ? (i18n.language.startsWith('zh') ? '正在读取…' : 'Loading…')
    : name || (i18n.language.startsWith('zh') ? '选择心情' : 'Choose emotion');

  return (
    <>
      {/* @@@ Keyframe animation for highlight effect */}
      <style>{`
        @keyframes stateHighlight {
          0% {
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(100, 150, 255, 0.4);
          }
          50% {
            transform: scale(1.05);
            box-shadow: 0 0 0 8px rgba(100, 150, 255, 0);
          }
          100% {
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(100, 150, 255, 0);
          }
        }
      `}</style>

      <div className={mobile ? 'state-chooser state-chooser--mobile' : 'state-chooser'} style={{
        padding: '0',
        fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif"
      }}>
        {/* Compact view when state is selected */}
        {mobile || (selectedStateData && !isExpanded) ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            cursor: mobile ? 'default' : 'pointer',
            minWidth: 0,
            width: '100%'
          }}
          onClick={mobile ? undefined : open}
          >
            {/* Date */}
            <div style={{
              fontSize: 13,
              color: 'var(--color-text-secondary)',
              fontWeight: 400,
              flexShrink: 0
            }}>
              {dateString}
            </div>

            {/* Mini icon + state name */}
            {!mobile && <div
              ref={indicatorRef}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '4px 12px',
                background: 'var(--color-bg-surface)',
                borderRadius: 6,
                border: '1px solid var(--color-shadow-soft)',
                transition: 'all 0.2s',
                animation: shouldAnimate ? 'stateHighlight 0.6s ease-out' : 'none'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-bg-surface-solid)';
                e.currentTarget.style.borderColor = 'var(--color-shadow-medium)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--color-bg-surface)';
                e.currentTarget.style.borderColor = 'var(--color-shadow-soft)';
              }}
            >
            {/* Shrunken state icon */}
            <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>
              {selectedState && getMiniStateIcon(selectedState)}
            </div>

            <span style={{
              fontSize: 14,
              fontWeight: 500,
              color: 'var(--color-text-body)'
            }}>
              {selectedStateData?.name}
            </span>
          </div>}

          {visibleSessionLabels.length > 0 && (
            <div
              title={sessionLabelsTitle}
              data-session-labels
              aria-label={`Session labels: ${sessionLabelsTitle}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                minWidth: 0,
                flex: 1,
                overflow: 'hidden',
                whiteSpace: 'nowrap'
              }}
            >
              {visibleSessionLabels.map((label, index) => (
                <span
                  key={`${label}-${index}`}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    maxWidth: 120,
                    minWidth: 0,
                    padding: '2px 6px',
                    borderRadius: 4,
                    border: '1px solid var(--color-shadow-soft)',
                    background: 'color-mix(in srgb, var(--color-bg-surface-solid) 70%, transparent)',
                    color: 'var(--color-text-secondary)',
                    fontSize: 12,
                    lineHeight: 1.3,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}
                >
                  {label}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Existing desktop overlay */
        mobile ? null : overlay
      )}
      </div>
      {mobile && active && expanded && overlayTarget ? createPortal(overlay, overlayTarget) : null}
      {mobile && navigationTarget ? createPortal(
        <button type="button" className="writing-chooser-action" disabled={selectedStateLoading || !active}
          aria-label={actionLabel} aria-haspopup="dialog" aria-expanded={expanded} onClick={open}>
          {selectedState && getMiniStateIcon(selectedState)}<span>{actionLabel}</span>
        </button>, navigationTarget) : null}
    </>
  );
}
