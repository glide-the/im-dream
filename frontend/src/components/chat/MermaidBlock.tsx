// [Input] Mermaid chart source text extracted from a ```mermaid fenced code block in chat Markdown.
// [Output] Lazily loaded mermaid SVG render with debounced streaming retries and raw-code fallback.
// [Pos] mermaid-block component node in frontend/src/components/chat
// [Sync] 2026-07-20: created per docs/design/claude-agent/chat-markdown-mermaid.md — dynamic import
//                    singleton, strict securityLevel, base theme mapped from CSS design tokens,
//                    serialized render queue, 300ms debounce for streaming input, non-throwing fallback.
import { memo, useEffect, useRef, useState } from 'react';

type MermaidApi = typeof import('mermaid')['default'];

const RENDER_DEBOUNCE_MS = 300;

let mermaidSingleton: Promise<MermaidApi> | null = null;
let renderQueue: Promise<unknown> = Promise.resolve();

function cssVar(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function loadMermaid(): Promise<MermaidApi> {
  if (!mermaidSingleton) {
    mermaidSingleton = import('mermaid').then((mod) => {
      const mermaid = mod.default;
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: 'base',
        themeVariables: {
          background: 'transparent',
          primaryColor: cssVar('--color-bg-paper', '#ffffff'),
          primaryTextColor: cssVar('--color-text-primary', '#1f2933'),
          primaryBorderColor: cssVar('--color-border-paper', '#d8d2c4'),
          lineColor: cssVar('--color-text-muted', '#6b7280'),
          textColor: cssVar('--color-text-primary', '#1f2933'),
          fontFamily: 'inherit',
        },
      });
      return mermaid;
    });
  }
  return mermaidSingleton;
}

// Serialize mermaid.render calls: mermaid keeps global rendering state and races
// leave orphan error elements in document.body.
function enqueueRender<T>(task: () => Promise<T>): Promise<T> {
  const run = renderQueue.then(task, task);
  renderQueue = run.then(
    () => undefined,
    () => undefined,
  );
  return run;
}

function removeOrphanRenderElement(id: string): void {
  document.getElementById(`d${id}`)?.remove();
  document.getElementById(id)?.remove();
}

interface MermaidBlockProps {
  chart: string;
}

export default memo(function MermaidBlock({ chart }: MermaidBlockProps) {
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const instanceIdRef = useRef(`mermaid-${crypto.randomUUID()}`);
  const seqRef = useRef(0);

  useEffect(() => {
    const seq = ++seqRef.current;
    const timer = window.setTimeout(() => {
      const renderId = `${instanceIdRef.current}-${seq}`;
      loadMermaid()
        .then((mermaid) => enqueueRender(() => mermaid.render(renderId, chart)))
        .then((result) => {
          if (seqRef.current === seq) {
            setSvg(result.svg);
            setFailed(false);
          }
        })
        .catch((error: unknown) => {
          removeOrphanRenderElement(renderId);
          // Expected during streaming: the fenced block is often syntactically incomplete.
          console.warn('[MermaidBlock] render failed, showing source fallback', error);
          if (seqRef.current === seq) {
            setFailed(true);
          }
        });
    }, RENDER_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [chart]);

  return (
    <div
      style={{
        margin: '0.75rem 0',
        padding: '0.75rem',
        borderRadius: '0.75rem',
        border: '1px solid var(--color-border-paper)',
        background: 'var(--color-bg-paper)',
        overflowX: 'auto',
      }}
    >
      {svg ? (
        <div
          style={{ display: 'flex', justifyContent: 'center', minWidth: 0 }}
          // mermaid with securityLevel 'strict' emits sanitized SVG markup.
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      ) : (
        <div>
          <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: '0.4rem' }}>
            {failed ? 'Mermaid 渲染失败，显示源码' : 'Mermaid 渲染中…'}
          </div>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
            <code>{chart}</code>
          </pre>
        </div>
      )}
    </div>
  );
});
