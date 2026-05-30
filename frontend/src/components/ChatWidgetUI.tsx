// [Sync] 2026-05-30: replace inline chat with AgentLinkUI – a compact card that links to the
//   Claude-agent Chat view via onOpenChat(threadId). The old chatWithVoice inline chat is removed.
// [Sync] 2026-05-30: restore inline chat using claude-agent service. Voice system prompt is
//   concatenated into every message request (systemPrompt field). The "Chat →" button remains
//   for users who want the full Chat view. No auto-navigation from the editor.
import React, { useState, useRef, useCallback, useEffect } from 'react';
import type { ChatWidgetData } from '../engine/ChatWidget';
import {
  FaBrain, FaHeart, FaQuestion, FaCloud, FaTheaterMasks, FaEye,
  FaFistRaised, FaLightbulb, FaShieldAlt, FaWind, FaFire, FaCompass, FaPaperPlane
} from 'react-icons/fa';
import { getAuthToken } from '../contexts/AuthContext';
import type { ChatApiSchemaRequestBody } from '../lib/chat-schema';
import { DEFAULT_CHAT_MODEL } from '../lib/chat-schema';

const API_BASE = '/ink-and-memory';

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

interface InlineMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatWidgetUIProps {
  data: ChatWidgetData;
  /** Called when the user clicks "Open in Chat". Passes the linked thread_id. */
  onOpenChat: (threadId: string) => void;
  onDelete: () => void;
}

export default function ChatWidgetUI({ data, onOpenChat, onDelete }: ChatWidgetUIProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<InlineMessage[]>([]);
  const [streamingText, setStreamingText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

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

  // Auto-scroll to latest message
  useEffect(() => {
    if (isExpanded) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingText, isExpanded]);

  const handleSend = useCallback(async () => {
    const text = inputText.trim();
    if (!text || !hasThread || isSending) return;

    setInputText('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsExpanded(true);
    setIsSending(true);
    setStreamingText('');

    const messageId = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;

    const requestBody: ChatApiSchemaRequestBody = {
      id: data.threadId!,
      resume: true,
      message: {
        id: messageId,
        role: 'user',
        parts: [{ type: 'text', text }],
        createdAt: new Date(),
      } as ChatApiSchemaRequestBody['message'],
      chatModel: DEFAULT_CHAT_MODEL,
      toolChoice: 'auto',
      allowedAppDefaultToolkit: [],
      allowedMcpServers: {},
      attachments: [],
      // Concatenate the voice system prompt into every message request
      systemPrompt: data.voiceConfig.tagline,
    };

    try {
      const response = await fetch(`${API_BASE}/api/claude-agent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + getAuthToken(),
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok || !response.body) {
        throw new Error(`Request failed: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = '';
      let buffer = '';

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last (potentially incomplete) line in the buffer
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const json = line.slice('data: '.length).trim();
          if (!json) continue;
          try {
            const event = JSON.parse(json) as { type: string; delta?: string; finishReason?: string };
            if (event.type === 'text-delta' && event.delta) {
              accumulated += event.delta;
              setStreamingText(accumulated);
            } else if (event.type === 'finish' || event.type === 'message-final') {
              if (accumulated) {
                setMessages(prev => [...prev, { role: 'assistant', content: accumulated }]);
                setStreamingText('');
                accumulated = '';
              }
            }
          } catch {
            // ignore malformed SSE lines
          }
        }
      }

      // Flush any remaining streaming text as a completed message
      if (accumulated) {
        setMessages(prev => [...prev, { role: 'assistant', content: accumulated }]);
        setStreamingText('');
      }
    } catch (err) {
      console.error('Inline Deck chat error:', err);
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠️ Could not get a response. Please try again.' }]);
      setStreamingText('');
    } finally {
      setIsSending(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [inputText, hasThread, isSending, data.threadId, data.voiceConfig.tagline]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const hasMessages = messages.length > 0 || !!streamingText;

  return (
    <div
      style={{
        margin: '16px 0',
        background: 'var(--color-bg-surface)',
        borderRadius: '10px',
        maxWidth: '560px',
        position: 'relative',
        border: `1.5px solid ${colorHex}33`,
        transition: 'all 0.2s ease'
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 14px' }}>
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

        {/* Voice icon */}
        <div style={{
          width: 34,
          height: 34,
          borderRadius: '50%',
          background: `linear-gradient(135deg, ${colorHex} 0%, ${colorHex}cc 100%)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          <Icon size={16} color="#fff" />
        </div>

        {/* Voice name + status */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--color-text-primary)' }}>
            {data.voiceConfig.name}
          </div>
          <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginTop: 1 }}>
            {hasThread ? (hasMessages ? `${messages.length} message${messages.length !== 1 ? 's' : ''}` : 'Ask anything…') : 'Creating thread…'}
          </div>
        </div>

        {/* Open in Chat button */}
        {hasThread && (
          <button
            onClick={() => onOpenChat(data.threadId!)}
            style={{
              padding: '5px 10px',
              background: 'transparent',
              color: colorHex,
              border: `1px solid ${colorHex}88`,
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              flexShrink: 0,
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = `${colorHex}22`; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            title="Open full Chat view"
          >
            Chat →
          </button>
        )}
      </div>

      {/* Message history (collapsible) */}
      {isExpanded && hasMessages && (
        <div style={{
          maxHeight: '260px',
          overflowY: 'auto',
          padding: '0 14px 8px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}>
          {messages.map((msg, idx) => (
            <div key={idx} style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              padding: '7px 11px',
              borderRadius: msg.role === 'user' ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
              background: msg.role === 'user' ? colorHex : 'var(--color-bg-hover)',
              color: msg.role === 'user' ? '#fff' : 'var(--color-text-body)',
              fontSize: 13,
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {msg.content}
            </div>
          ))}
          {streamingText && (
            <div style={{
              alignSelf: 'flex-start',
              maxWidth: '85%',
              padding: '7px 11px',
              borderRadius: '12px 12px 12px 3px',
              background: 'var(--color-bg-hover)',
              color: 'var(--color-text-body)',
              fontSize: 13,
              lineHeight: '1.5',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}>
              {streamingText}
              <span style={{ opacity: 0.5, marginLeft: 2 }}>▋</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Collapse toggle when messages exist but panel is collapsed */}
      {!isExpanded && hasMessages && (
        <button
          onClick={() => setIsExpanded(true)}
          style={{
            display: 'block',
            width: '100%',
            padding: '4px 14px',
            background: 'transparent',
            border: 'none',
            borderTop: `1px solid ${colorHex}22`,
            fontSize: 12,
            color: 'var(--color-text-secondary)',
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          ▸ Show {messages.length} message{messages.length !== 1 ? 's' : ''}
        </button>
      )}

      {/* Inline input */}
      {hasThread && (
        <div style={{
          display: 'flex',
          gap: '8px',
          padding: '8px 10px 10px',
          borderTop: (isExpanded && hasMessages) ? `1px solid ${colorHex}22` : undefined,
          alignItems: 'flex-end',
        }}>
          <textarea
            ref={inputRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isSending ? 'Waiting for response…' : `Message ${data.voiceConfig.name}…`}
            disabled={isSending}
            rows={1}
            style={{
              flex: 1,
              resize: 'none',
              padding: '7px 10px',
              borderRadius: 7,
              border: `1px solid ${colorHex}44`,
              background: 'var(--color-bg-app)',
              color: 'var(--color-text-body)',
              fontSize: 13,
              lineHeight: '1.5',
              outline: 'none',
              fontFamily: 'inherit',
              overflow: 'hidden',
            }}
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = 'auto';
              t.style.height = `${Math.min(t.scrollHeight, 120)}px`;
            }}
          />
          <button
            onClick={() => void handleSend()}
            disabled={!inputText.trim() || isSending}
            style={{
              padding: '7px 10px',
              background: colorHex,
              color: '#fff',
              border: 'none',
              borderRadius: 7,
              cursor: inputText.trim() && !isSending ? 'pointer' : 'not-allowed',
              opacity: inputText.trim() && !isSending ? 1 : 0.4,
              transition: 'opacity 0.15s',
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Send message (Enter)"
          >
            <FaPaperPlane size={13} />
          </button>
        </div>
      )}
    </div>
  );
}
