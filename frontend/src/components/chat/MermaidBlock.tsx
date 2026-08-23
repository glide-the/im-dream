// [Input] Mermaid chart source text extracted from a ```mermaid fenced code block in chat Markdown.
// [Output] Lazily loaded mermaid SVG render with debounced streaming retries and raw-code fallback;
//          shared media toolbar offers preview/source, copy, enlarge, and PNG export, with the unified immersive zoom viewer.
// [Pos] mermaid-block component node in frontend/src/components/chat
// [Sync] 2026-07-20: created per docs/design/claude-agent/chat-markdown-mermaid.md — dynamic import
//                    singleton, strict securityLevel, base theme mapped from CSS design tokens,
//                    serialized render queue, 300ms debounce for streaming input, non-throwing fallback.
// [Sync] 2026-07-20: 新增图表工具栏（设计文档 §2.6）— 预览/源码分段切换、复用 useCopy 复制
//                    完整 ```mermaid 围栏文本、viewBox 尺寸 + 2x scale canvas 栅格化导出 PNG；
//                    渲染失败时强制源码视图。
// [Sync] 2026-07-20: i18n — toolbar labels/titles and render status copy resolve through the
//                    chat.mermaid namespace (en + zh) via useTranslation.
// [Sync] 2026-08-23: reuse the exact Markdown media frame and immersive Modal skeleton shared with Workspace images; add enlarge beside copy.
// [Sync] 2026-08-23: scope immersive zoom to the rendered diagram node so the shared paper sheet keeps its fitted geometry.
import { memo, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useCopy } from '../../hooks/useCopy';
import { IconCheck, IconCopy, IconDownload, IconLoader, IconMaximize } from './Icons';
import Modal from './Modal';
import './MarkdownMedia.css';

type MermaidApi = typeof import('mermaid')['default'];
type ViewMode = 'preview' | 'source';

const RENDER_DEBOUNCE_MS = 300;
const EXPORT_SCALE = 2;

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

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('svg image decode failed'));
    image.src = url;
  });
}

function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = fileName;
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}

// Rasterize the rendered SVG into a PNG download. mermaid emits transparent SVGs
// sized via viewBox/max-width, so write explicit dimensions and paint the paper
// background before drawing.
async function exportSvgAsPng(svgMarkup: string): Promise<void> {
  const doc = new DOMParser().parseFromString(svgMarkup, 'image/svg+xml');
  const svgEl = doc.documentElement;
  const viewBox = (svgEl.getAttribute('viewBox') ?? '').split(/[\s,]+/).map(Number);
  const width = viewBox.length === 4 && viewBox[2] > 0 ? viewBox[2] : 800;
  const height = viewBox.length === 4 && viewBox[3] > 0 ? viewBox[3] : 600;
  svgEl.setAttribute('width', String(width));
  svgEl.setAttribute('height', String(height));

  const serialized = new XMLSerializer().serializeToString(svgEl);
  const url = URL.createObjectURL(new Blob([serialized], { type: 'image/svg+xml;charset=utf-8' }));
  try {
    const image = await loadImage(url);
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(width * EXPORT_SCALE);
    canvas.height = Math.round(height * EXPORT_SCALE);
    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('canvas 2d context unavailable');
    }
    context.scale(EXPORT_SCALE, EXPORT_SCALE);
    context.fillStyle = cssVar('--color-bg-paper', '#ffffff');
    context.fillRect(0, 0, width, height);
    context.drawImage(image, 0, 0, width, height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
    if (!blob) {
      throw new Error('png encode failed');
    }
    downloadBlob(blob, `mermaid-diagram-${Date.now()}.png`);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function ToolbarButton({ title, onClick, disabled, children }: { title: string; onClick: () => void; disabled?: boolean; children: ReactNode }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      className="markdown-media-block__action"
    >
      {children}
    </button>
  );
}

interface MermaidBlockProps {
  chart: string;
}

export default memo(function MermaidBlock({ chart }: MermaidBlockProps) {
  const { t } = useTranslation();
  const { copied, copy } = useCopy();
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('preview');
  const [isExporting, setIsExporting] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewZoom, setPreviewZoom] = useState(100);
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

  const handleExport = useCallback(() => {
    if (!svg || isExporting) {
      return;
    }
    setIsExporting(true);
    exportSvgAsPng(svg)
      .catch((error: unknown) => {
        console.warn('[MermaidBlock] png export failed', error);
      })
      .finally(() => setIsExporting(false));
  }, [svg, isExporting]);

  const showPreview = viewMode === 'preview' && svg !== null;
  // Copy the complete fenced Markdown block, not just the chart source.
  const fencedMarkdown = `\`\`\`mermaid\n${chart.replace(/\n+$/, '')}\n\`\`\``;

  return (
    <>
      <div className="markdown-media-block" data-markdown-media-kind="mermaid">
        <div className="markdown-media-block__toolbar">
          <span className="markdown-media-block__label">
            {failed ? t('chat.mermaid.renderFailed') : svg ? 'Mermaid' : t('chat.mermaid.rendering')}
          </span>
          <div className="markdown-media-block__segmented">
            {(['preview', 'source'] as const).map((mode) => {
              const active = showPreview === (mode === 'preview');
              const disabled = mode === 'preview' && svg === null;
              return (
                <button
                  key={mode}
                  type="button"
                  disabled={disabled}
                  onClick={() => setViewMode(mode)}
                  className="markdown-media-block__segment"
                  aria-pressed={active}
                >
                  {mode === 'preview' ? t('chat.mermaid.preview') : t('chat.mermaid.source')}
                </button>
              );
            })}
          </div>
          <ToolbarButton title={t('chat.mermaid.copySource')} onClick={() => copy(fencedMarkdown)}>
            {copied ? <IconCheck /> : <IconCopy />}
          </ToolbarButton>
          <ToolbarButton
            title={t('chat.mermaid.enlarge')}
            onClick={() => {
              setPreviewZoom(100);
              setPreviewOpen(true);
            }}
            disabled={!svg}
          >
            <IconMaximize />
          </ToolbarButton>
          <ToolbarButton title={t('chat.mermaid.exportPng')} onClick={handleExport} disabled={!svg || isExporting}>
            {isExporting ? <IconLoader /> : <IconDownload />}
          </ToolbarButton>
        </div>
        <div className="markdown-media-block__content">
          {showPreview ? (
            <div
              className="markdown-media-block__preview"
              // mermaid with securityLevel 'strict' emits sanitized SVG markup.
              dangerouslySetInnerHTML={{ __html: svg }}
            />
          ) : (
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
              <code>{chart}</code>
            </pre>
          )}
        </div>
      </div>
      <Modal
        open={previewOpen && svg !== null}
        title={t('chat.mermaid.previewTitle')}
        closeLabel={t('chat.mediaPreview.close')}
        variant="media-preview"
        onClose={() => setPreviewOpen(false)}
        toolbarActions={(
          <button
            type="button"
            className="modal-toolbar-button"
            title={t('chat.mermaid.exportPng')}
            aria-label={t('chat.mermaid.exportPng')}
            disabled={isExporting}
            onClick={handleExport}
          >
            {isExporting ? <IconLoader /> : <IconDownload />}
          </button>
        )}
        zoom={{
          value: previewZoom,
          onChange: setPreviewZoom,
          zoomOutLabel: t('chat.mediaPreview.zoomOut'),
          zoomInLabel: t('chat.mediaPreview.zoomIn'),
        }}
      >
        <figure className="markdown-media-preview__sheet markdown-media-preview__sheet--diagram">
          <div
            className="markdown-media-preview__diagram markdown-media-preview__zoom-target"
            // The same strict Mermaid SVG is reused; the preview never reparses source or accepts HTML.
            dangerouslySetInnerHTML={{ __html: svg ?? '' }}
          />
        </figure>
      </Modal>
    </>
  );
});
