// [Sync] 2026-05-30: replace inline chat with AgentLinkUI – a compact card that links to the
//   Claude-agent Chat view via onOpenChat(threadId). The old chatWithVoice inline chat is removed.
import { useState } from 'react';
import type { ChatWidgetData } from '../engine/ChatWidget';
import {
  FaBrain, FaHeart, FaQuestion, FaCloud, FaTheaterMasks, FaEye,
  FaFistRaised, FaLightbulb, FaShieldAlt, FaWind, FaFire, FaCompass
} from 'react-icons/fa';

const iconMap = {
  brain: FaBrain,
  heart: FaHeart,
  question: FaQuestion,
  cloud: FaCloud,
  masks: FaTheaterMasks,
  eye: FaEye,
  fist: FaFistRaised,
  lightbulb: FaLightbulb,
  shield: FaShieldAlt,
  wind: FaWind,
  fire: FaFire,
  compass: FaCompass,
};

interface ChatWidgetUIProps {
  data: ChatWidgetData;
  /** Called when the user clicks "Open Chat". Passes the linked thread_id. */
  onOpenChat: (threadId: string) => void;
  onDelete: () => void;
}

export default function ChatWidgetUI({ data, onOpenChat, onDelete }: ChatWidgetUIProps) {
  const [isHovered, setIsHovered] = useState(false);
  const Icon = iconMap[data.voiceConfig.icon as keyof typeof iconMap] || FaBrain;
  const hasThread = !!data.threadId;

  const colorHex = (() => {
    const map: Record<string, string> = {
      blue: '#4da3ff', pink: '#ff66b3', green: '#52c77e',
      purple: '#9b7ff5', orange: '#f9a875', red: '#f86e6e',
      yellow: '#f5d76e', teal: '#5ec0c0'
    };
    return map[data.voiceConfig.color] || '#4da3ff';
  })();

  return (
    <div
      style={{
        margin: '16px 0',
        padding: '14px 16px',
        background: 'var(--color-bg-surface)',
        borderRadius: '10px',
        maxWidth: '480px',
        position: 'relative',
        border: `1.5px solid ${colorHex}33`,
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        transition: 'all 0.2s ease'
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Delete button */}
      <button
        onClick={onDelete}
        style={{
          position: 'absolute',
          top: '6px',
          right: '6px',
          padding: '2px 6px',
          backgroundColor: 'transparent',
          color: 'var(--color-text-muted)',
          border: 'none',
          borderRadius: '4px',
          fontSize: '14px',
          cursor: 'pointer',
          opacity: isHovered ? 0.6 : 0,
          pointerEvents: isHovered ? 'auto' : 'none',
          lineHeight: '1'
        }}
        title="Remove agent link"
      >
        ×
      </button>

      {/* Icon */}
      <div style={{
        width: 36,
        height: 36,
        borderRadius: '50%',
        background: `linear-gradient(135deg, ${colorHex} 0%, ${colorHex}cc 100%)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}>
        <Icon size={18} color="#fff" />
      </div>

      {/* Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--color-text-primary)' }}>
          {data.voiceConfig.name}
        </div>
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 2 }}>
          {hasThread ? 'Claude-agent thread linked' : 'Creating thread…'}
        </div>
      </div>

      {/* Open Chat button */}
      {hasThread && (
        <button
          onClick={() => onOpenChat(data.threadId!)}
          style={{
            padding: '6px 12px',
            background: colorHex,
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            flexShrink: 0,
            transition: 'opacity 0.15s'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.opacity = '0.85'; }}
          onMouseLeave={(e) => { e.currentTarget.style.opacity = '1'; }}
          title="Open in Chat view"
        >
          Chat →
        </button>
      )}
    </div>
  );
}
