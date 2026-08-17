// [Input] ExportChatMessage blocks (text/reasoning/tool) + thread title + i18n labels +
//         optional ExportPendingConfirmation (from exportThreadImage / ChatView).
// [Output] The warm-paper long-image card (Ink & Memory UI Design v2.1 tokens: Warm Canvas bg,
//          dashed Border Paper dividers, Action Brown user bubbles, Memory Yellow accents).
//          Mirrors ChatMessageList visuals: italic left-border reasoning blocks, collapsed
//          tool rows with amber pending badges, dark Terminal output cards — plus a static
//          ToolConfirmationDock-style card pinned at the bottom when a confirmation awaits.
// [Pos] chat share long-image card node in frontend/src/components/chat
// [Sync] 2026-08-03: created for the share dialog export-image option (split from
//                    exportThreadImage to satisfy react-refresh single-export rule).
// [Sync] 2026-08-03: render reasoning/tool blocks and the bottom pending-confirmation card.
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

export interface ExportToolBlock {
  kind: 'tool';
  toolName: string;
  title?: string;
  summary?: string;
  status: 'executing' | 'completed' | 'error';
  /** Per-row amber badge label (待确认 / 待回答) when this part awaits a user decision. */
  pendingLabel?: string;
  /** Terminal-card header label (e.g. localized "Terminal" / "Write"). */
  terminalLabel?: string;
  command?: string;
  output?: string;
  outputTruncated?: boolean;
  exitCode?: string | null;
  /** Right-aligned colored status text on the terminal header (Written / Write failed…). */
  statusLabel?: string;
  /** Completed editor-write parts render as a quiet success row instead of a terminal card. */
  isEditorWrite?: boolean;
}

export type ExportBlock =
  | { kind: 'text'; text: string }
  | { kind: 'reasoning'; text: string }
  | ExportToolBlock;

export interface ExportChatMessage {
  role: 'user' | 'assistant';
  blocks: ExportBlock[];
  files: string[];
}

export interface ExportConfirmationQuestionOption {
  label: string;
  description?: string;
}

export interface ExportConfirmationQuestion {
  question: string;
  required?: boolean;
  description?: string;
  options: ExportConfirmationQuestionOption[];
}

export interface ExportPendingConfirmation {
  kind: 'confirm' | 'askuser' | 'sandbox-network' | 'reject-only';
  title: string;
  badge: string;
  /** Mono detail block for the generic confirm variant (command or truncated JSON). */
  detail?: string;
  /** Pre-localized info rows for the sandbox-network variant ("Host: …" / "Network policy: …"). */
  infoRows?: string[];
  questions?: ExportConfirmationQuestion[];
  primaryActionLabel: string;
  secondaryActionLabel: string;
}

export interface ExportImageLabels {
  you: string;
  assistant: string;
  footer: string;
  thinking: string;
  truncated: string;
}

const EXPORT_MARKDOWN_COMPONENTS: Components = {
  p: ({ children }) => <p style={{ margin: '0 0 0.65em', lineHeight: 1.75 }}>{children}</p>,
  h1: ({ children }) => <h1 style={{ margin: '0.7em 0 0.4em', fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ margin: '0.7em 0 0.4em', fontSize: '1.15rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ margin: '0.7em 0 0.35em', fontSize: '1.02rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{children}</h3>,
  h4: ({ children }) => <h4 style={{ margin: '0.6em 0 0.3em', fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{children}</h4>,
  ul: ({ children }) => <ul style={{ margin: '0 0 0.65em', paddingLeft: '1.25em' }}>{children}</ul>,
  ol: ({ children }) => <ol style={{ margin: '0 0 0.65em', paddingLeft: '1.35em' }}>{children}</ol>,
  li: ({ children }) => <li style={{ margin: '0.2em 0', lineHeight: 1.7 }}>{children}</li>,
  a: ({ children, href }) => <a href={href} style={{ color: 'var(--color-action-link)', textDecoration: 'underline' }}>{children}</a>,
  strong: ({ children }) => <strong style={{ color: 'var(--color-text-primary)', fontWeight: 700 }}>{children}</strong>,
  blockquote: ({ children }) => (
    <blockquote style={{ margin: '0 0 0.65em', padding: '0.1em 0 0.1em 0.9em', borderLeft: '3px solid var(--color-voice-yellow)', color: 'var(--color-text-secondary)' }}>
      {children}
    </blockquote>
  ),
  hr: () => <hr style={{ border: 'none', borderTop: '1px dashed var(--color-border-paper)', margin: '1em 0' }} />,
  code: ({ className, children }) => (
    <code
      className={className}
      style={className ? { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.86em' } : {
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: '0.86em',
        background: 'color-mix(in srgb, var(--color-border-paper) 34%, transparent)',
        borderRadius: '0.3rem',
        padding: '0.08em 0.35em',
      }}
    >
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre style={{
      margin: '0 0 0.8em',
      padding: '0.8rem 1rem',
      background: 'var(--color-bg-paper)',
      border: '1px dashed var(--color-border-paper)',
      borderRadius: '0.85rem',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
      lineHeight: 1.65,
    }}>
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <table style={{ borderCollapse: 'collapse', margin: '0 0 0.8em', width: '100%', fontSize: '0.85em' }}>{children}</table>
  ),
  th: ({ children }) => (
    <th style={{ border: '1px solid var(--color-border-paper)', padding: '0.35em 0.6em', background: 'var(--color-bg-paper)', color: 'var(--color-text-primary)', textAlign: 'left' }}>{children}</th>
  ),
  td: ({ children }) => (
    <td style={{ border: '1px solid var(--color-border-paper)', padding: '0.35em 0.6em' }}>{children}</td>
  ),
};

function ReasoningBlock({ text, label }: { text: string; label: string }) {
  return (
    <div style={{ paddingLeft: '0.85rem', borderLeft: '2px solid var(--color-border-paper)' }}>
      <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', fontStyle: 'italic', marginBottom: '0.35rem' }}>
        ✎ {label}
      </div>
      <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', lineHeight: 1.7, color: 'var(--color-text-secondary)', fontStyle: 'italic', wordBreak: 'break-word' }}>
        {text}
      </div>
    </div>
  );
}

/** Collapsed tool row — mirrors ChatMessageList (amber border/badge while pending). */
function ToolRow({ block }: { block: ExportToolBlock }) {
  const borderColor = block.pendingLabel
    ? '#f59e0b'
    : block.isEditorWrite
      ? 'var(--color-state-success)'
      : 'var(--color-action-link)';
  const displayTitle = block.title || block.toolName;
  return (
    <div style={{ paddingLeft: '0.85rem', borderLeft: `2px solid ${borderColor}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
        {block.pendingLabel ? (
          <span style={{ width: '0.55rem', height: '0.55rem', borderRadius: '999px', background: '#f59e0b', flexShrink: 0 }} />
        ) : block.status === 'executing' ? (
          <span style={{ width: '0.7rem', height: '0.7rem', borderRadius: '999px', border: '2px solid var(--color-action-link)', borderTopColor: 'transparent', flexShrink: 0, boxSizing: 'border-box' }} />
        ) : block.isEditorWrite ? (
          <span style={{ color: 'var(--color-state-success)', flexShrink: 0 }}>✓</span>
        ) : null}
        <span style={{ flex: 1, minWidth: 0, fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {displayTitle}{block.summary ? ` — ${block.summary}` : ''}
        </span>
        {block.pendingLabel ? (
          <span style={{ flexShrink: 0, borderRadius: '999px', padding: '0.1rem 0.5rem', fontSize: '0.72rem', fontWeight: 600, fontStyle: 'normal', color: '#b45309', background: 'color-mix(in srgb, #f59e0b 16%, transparent)' }}>
            {block.pendingLabel}
          </span>
        ) : null}
      </div>
    </div>
  );
}

/** Dark terminal output card — mirrors the ChatMessageList Terminal/Write cards. */
function ToolTerminalCard({ block, truncatedLabel }: { block: ExportToolBlock; truncatedLabel: string }) {
  const exitCodeNumber = block.exitCode != null ? Number(block.exitCode) : null;
  return (
    <div style={{ overflow: 'hidden', borderRadius: '12px', background: 'var(--color-code-bg)', color: 'var(--color-code-text)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', padding: '0.65rem 1rem', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
        <span style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'baseline', gap: '0.55rem' }}>
          <span style={{ flexShrink: 0 }}>‹ {block.terminalLabel ?? 'Terminal'}</span>
          {block.summary ? <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--color-code-text)' }}>{block.summary}</span> : null}
        </span>
        {block.statusLabel ? (
          <span style={{ flexShrink: 0, color: block.status === 'error' ? 'var(--color-state-error)' : block.status === 'completed' ? 'var(--color-state-success)' : 'var(--color-action-link)' }}>
            {block.statusLabel}
          </span>
        ) : null}
      </div>
      <div style={{ padding: '0 1rem 0.9rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.8rem', lineHeight: 1.65 }}>
        {block.command ? (
          <p style={{ margin: '0 0 0.45rem' }}>
            <span style={{ color: 'var(--color-action-link)' }}>$</span> <span style={{ wordBreak: 'break-all' }}>{block.command}</span>
          </p>
        ) : null}
        {block.output ? (
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--color-code-text)' }}>{block.output}</pre>
        ) : null}
        {block.outputTruncated ? (
          <div style={{ marginTop: '0.35rem', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{truncatedLabel}</div>
        ) : null}
      </div>
      {exitCodeNumber != null ? (
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', padding: '0.55rem 1rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.75rem', color: exitCodeNumber === 0 ? 'var(--color-state-success)' : 'var(--color-state-error)' }}>
          Exit code: {block.exitCode}
        </div>
      ) : null}
    </div>
  );
}

function ToolBlockView({ block, truncatedLabel }: { block: ExportToolBlock; truncatedLabel: string }) {
  const hasTerminal = Boolean(block.output || block.command) || Boolean(block.terminalLabel);
  if (hasTerminal && !block.isEditorWrite) {
    return <ToolTerminalCard block={block} truncatedLabel={truncatedLabel} />;
  }
  return <ToolRow block={block} />;
}

/** Static replica of ToolConfirmationDock — rendered once, pinned at the bottom. */
function PendingConfirmationCard({ confirmation }: { confirmation: ExportPendingConfirmation }) {
  return (
    <div style={{
      width: '100%',
      boxSizing: 'border-box',
      borderRadius: '18px',
      border: '1px solid var(--color-border-paper)',
      background: 'var(--color-bg-paper)',
      boxShadow: '0 12px 32px var(--color-shadow-soft)',
      padding: '0.95rem 1.1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.6rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem' }}>
        <span aria-hidden="true" style={{ marginTop: '0.35rem', width: '0.55rem', height: '0.55rem', borderRadius: '999px', background: '#f59e0b', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0, fontSize: '0.95rem', fontWeight: 600, lineHeight: 1.5, color: 'var(--color-text-primary)', wordBreak: 'break-word' }}>
          {confirmation.title}
        </div>
        <span style={{ flexShrink: 0, borderRadius: '999px', padding: '0.15rem 0.55rem', fontSize: '0.72rem', fontWeight: 600, color: '#b45309', background: 'color-mix(in srgb, #f59e0b 16%, transparent)' }}>
          {confirmation.badge}
        </span>
      </div>

      {confirmation.questions?.map((question, questionIndex) => (
        <div key={questionIndex} style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.5 }}>
            {question.question}
            {question.required ? <span style={{ color: 'var(--color-state-error)', marginLeft: '0.2rem' }}>*</span> : null}
          </div>
          {question.description ? (
            <div style={{ fontSize: '0.76rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>{question.description}</div>
          ) : null}
          {question.options.map((option, optionIndex) => (
            <div key={optionIndex} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.55rem', padding: '0.1rem 0 0.1rem 0.15rem' }}>
              <span style={{
                marginTop: '0.18rem',
                width: '0.85rem',
                height: '0.85rem',
                borderRadius: '999px',
                border: '1.5px solid var(--color-text-muted)',
                flexShrink: 0,
                boxSizing: 'border-box',
              }} />
              <span style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.08rem' }}>
                <span style={{ fontSize: '0.85rem', color: 'var(--color-text-primary)', lineHeight: 1.45 }}>{option.label}</span>
                {option.description ? (
                  <span style={{ fontSize: '0.74rem', color: 'var(--color-text-muted)', lineHeight: 1.45 }}>{option.description}</span>
                ) : null}
              </span>
            </div>
          ))}
        </div>
      ))}

      {confirmation.detail ? (
        <div style={{
          borderRadius: '0.75rem',
          border: '1px dashed var(--color-border-paper)',
          background: 'var(--color-bg-app)',
          padding: '0.6rem 0.8rem',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: '0.76rem',
          lineHeight: 1.6,
          color: 'var(--color-text-secondary)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}>
          {confirmation.detail}
        </div>
      ) : null}

      {confirmation.infoRows?.map((row, rowIndex) => (
        <div key={rowIndex} style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', lineHeight: 1.55 }}>{row}</div>
      ))}

      {/* 静态按钮区 — 仅作画面还原，图片中不可点击 */}
      <div style={{ display: 'flex', gap: '0.7rem', marginTop: '0.25rem' }}>
        <span style={{
          flex: confirmation.kind === 'reject-only' ? 1 : 1.4,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.4rem',
          height: '2.5rem',
          borderRadius: '0.9rem',
          background: 'var(--color-export-action-bg)',
          color: 'var(--color-export-action-text, #FFFFFF)',
          fontSize: '0.85rem',
          fontWeight: 600,
        }}>
          {confirmation.kind === 'reject-only' ? '✕' : '✓'} {confirmation.primaryActionLabel}
        </span>
        {confirmation.kind !== 'reject-only' ? <span style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.4rem',
          height: '2.5rem',
          borderRadius: '0.9rem',
          border: '1px solid var(--color-border-paper)',
          background: 'transparent',
          color: 'var(--color-text-secondary)',
          fontSize: '0.85rem',
          fontWeight: 600,
        }}>
          ✕ {confirmation.secondaryActionLabel}
        </span> : null}
      </div>
    </div>
  );
}

export default function ThreadImageCard({ title, messages, labels, dateText, pendingConfirmation }: {
  title: string;
  messages: ExportChatMessage[];
  labels: ExportImageLabels;
  dateText: string;
  pendingConfirmation?: ExportPendingConfirmation | null;
}) {
  return (
    <div style={{
      width: '720px',
      boxSizing: 'border-box',
      padding: '2.9rem 2.75rem 2.5rem',
      background: 'var(--color-bg-app)',
      color: 'var(--color-text-body)',
      fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif",
      fontSize: '0.92rem',
    }}>
      {/* 品牌头部 — 手写感 Logo + Memory Yellow 手绘下划线 + 导出日期 */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <div style={{ fontSize: '1.9rem', fontWeight: 700, color: 'var(--color-text-primary)', lineHeight: 1.1 }}>
            Ink &amp; Memory
          </div>
          <div style={{
            marginTop: '0.35rem',
            width: '4.2rem',
            height: '0.4rem',
            borderRadius: '999px',
            background: 'var(--color-voice-yellow)',
            transform: 'rotate(-1.2deg)',
            opacity: 0.9,
          }} />
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', flexShrink: 0 }}>{dateText}</div>
      </div>

      <div style={{ marginTop: '1.6rem', fontSize: '1.35rem', fontWeight: 700, color: 'var(--color-text-primary)', lineHeight: 1.35, wordBreak: 'break-word' }}>
        {title}
      </div>

      {/* 单一虚线纸边界（轻纸面分区规则） */}
      <div style={{ borderTop: '1.5px dashed var(--color-border-paper)', margin: '1.2rem 0 1.8rem' }} />

      {messages.map((message, index) => (
        message.role === 'user' ? (
          <div key={index} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', margin: '0 0 1.35rem' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginBottom: '0.4rem' }}>{labels.you}</span>
            {message.files.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'flex-end', gap: '0.35rem', marginBottom: '0.45rem', maxWidth: '82%' }}>
                {message.files.map((name, fileIndex) => (
                  <span key={fileIndex} style={{
                    fontSize: '0.72rem',
                    color: 'var(--color-text-secondary)',
                    border: '1px dashed var(--color-border-paper)',
                    borderRadius: '999px',
                    padding: '0.18rem 0.6rem',
                    background: 'var(--color-bg-paper)',
                  }}>
                    {name}
                  </span>
                ))}
              </div>
            ) : null}
            {message.blocks.some((block) => block.kind === 'text' && block.text) ? (
              <div style={{
                maxWidth: '82%',
                boxSizing: 'border-box',
                background: 'var(--color-export-action-bg)',
                color: 'var(--color-export-action-text, #FFFFFF)',
                borderRadius: '1.1rem 1.1rem 0.3rem 1.1rem',
                padding: '0.7rem 1rem',
                lineHeight: 1.7,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {message.blocks
                  .filter((block): block is { kind: 'text'; text: string } => block.kind === 'text')
                  .map((block) => block.text)
                  .join('\n\n')}
              </div>
            ) : null}
          </div>
        ) : (
          <div key={index} style={{ margin: '0 0 1.5rem', display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
              <span style={{ width: '0.55rem', height: '0.55rem', borderRadius: '999px', background: 'var(--color-voice-yellow)', flexShrink: 0 }} />
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>{labels.assistant}</span>
            </div>
            {message.blocks.map((block, blockIndex) => {
              if (block.kind === 'reasoning') {
                return <ReasoningBlock key={blockIndex} text={block.text} label={labels.thinking} />;
              }
              if (block.kind === 'tool') {
                return <ToolBlockView key={blockIndex} block={block} truncatedLabel={labels.truncated} />;
              }
              return (
                <div key={blockIndex} style={{ lineHeight: 1.75, wordBreak: 'break-word' }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={EXPORT_MARKDOWN_COMPONENTS}>
                    {block.text}
                  </ReactMarkdown>
                </div>
              );
            })}
          </div>
        )
      ))}

      {/* 待确认窗口 — 整图只有一个，固定放在最下方（镜像 ToolConfirmationDock） */}
      {pendingConfirmation ? (
        <div style={{ marginTop: '0.5rem' }}>
          <PendingConfirmationCard confirmation={pendingConfirmation} />
        </div>
      ) : null}

      {/* 底部氛围收束 — 虚线边界 + 品牌标语 + Spark Green 灵感星星 */}
      <div style={{ borderTop: '1.5px dashed var(--color-border-paper)', marginTop: '2rem', paddingTop: '1.3rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
        <span style={{ color: 'var(--color-voice-green)', fontSize: '0.85rem' }}>✦</span>
        <span style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{labels.footer}</span>
        <span style={{ color: 'var(--color-voice-green)', fontSize: '0.85rem' }}>✦</span>
      </div>
    </div>
  );
}
