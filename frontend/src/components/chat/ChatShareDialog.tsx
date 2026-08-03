// [Input] open/exporting/exportFailed state, optional rendered preview, and callbacks from
//         ChatView; i18n labels.
// [Output] Share dialog (Ink & Memory UI Design v2.1 轻纸面弹层): Solid Cream 不透明浮层、
//          虚线 Border Paper 条目边界、Memory Yellow 角标；提供「复制链接」（暂未实现，置灰）
//          与「导出图片」两个选项。导出后切换到预览视图 — 长图定宽展示、超高内部滚动，
//          底部提供「下载图片 / 返回」操作。
// [Pos] chat share dialog node in frontend/src/components/chat
// [Sync] 2026-08-03: created — replaces the direct copy-link share action with an options dialog.
// [Sync] 2026-08-03: add the scrollable long-image preview view with download/back actions.
import { useEffect, type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { IconCopy, IconDownload, IconImage, IconLoader, IconShare, IconX } from './Icons';
import type { RenderedThreadImage } from './exportThreadImage';

interface ChatShareDialogProps {
  open: boolean;
  threadTitle?: string | null;
  exporting: boolean;
  exportFailed: boolean;
  canExport: boolean;
  /** Rendered long image awaiting user confirmation; switches the dialog to preview mode. */
  preview: RenderedThreadImage | null;
  /** True while the merged PNG is being assembled for download. */
  downloading: boolean;
  /** 截取进度（done/total 块数）；null 表示尚未开始。 */
  progress: { done: number; total: number } | null;
  onClose: () => void;
  onExportImage: () => void;
  onDownloadPreview: () => void;
  onDiscardPreview: () => void;
}

export default function ChatShareDialog({
  open,
  threadTitle,
  exporting,
  exportFailed,
  canExport,
  preview,
  downloading,
  progress,
  onClose,
  onExportImage,
  onDownloadPreview,
  onDiscardPreview,
}: ChatShareDialogProps) {
  const { t } = useTranslation();

  const progressPercent = progress && progress.total > 0
    ? Math.min(100, Math.round((progress.done / progress.total) * 100))
    : null;
  // 截取进度条 — Memory Yellow 细条 + 百分比，导出进行中可见。
  const progressBar = exporting && progressPercent !== null ? (
    <div style={{ marginTop: '0.6rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.3rem', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
        <span>{t('chat.share.rendering')}</span>
        <span>{progressPercent}%</span>
      </div>
      <div style={{ height: '0.3rem', borderRadius: '999px', background: 'color-mix(in srgb, var(--color-border-paper) 42%, transparent)', overflow: 'hidden' }}>
        <div style={{ width: `${progressPercent}%`, height: '100%', borderRadius: '999px', background: 'var(--color-voice-yellow)', transition: 'width 0.2s ease' }} />
      </div>
    </div>
  ) : null;

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      // 导出进行中关闭 = 任务转后台运行，不打断。
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  const optionRowStyle: CSSProperties = {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.8rem 0.9rem',
    borderRadius: '0.85rem',
    border: '1px dashed color-mix(in srgb, var(--color-border-paper) 88%, transparent)',
    background: 'transparent',
    textAlign: 'left',
    boxSizing: 'border-box',
  };

  return (
    <div
      role="presentation"
      onClick={() => { onClose(); }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        display: 'grid',
        placeItems: 'center',
        background: 'color-mix(in srgb, var(--color-text-primary) 30%, transparent)',
        padding: '1rem',
        boxSizing: 'border-box',
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('chat.share.title')}
        onClick={(event) => event.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: preview ? '24rem' : '21.5rem',
          borderRadius: '1.1rem',
          border: '1px solid var(--color-border-paper)',
          background: 'var(--color-bg-surface-solid)',
          boxShadow: '0 18px 48px var(--color-shadow-medium)',
          padding: '1.2rem 1.2rem 1.1rem',
          boxSizing: 'border-box',
          fontFamily: "'Excalifont', 'Xiaolai', Georgia, serif",
          transition: 'max-width 0.18s ease',
        }}
      >
        {/* 头部 — 标题 + Memory Yellow 点缀 + 关闭按钮 */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.75rem' }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <IconShare style={{ width: '1rem', height: '1rem', color: 'var(--color-text-primary)', flexShrink: 0 }} />
              <span style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                {preview ? t('chat.share.previewTitle') : t('chat.share.title')}
              </span>
            </div>
            <div style={{ marginTop: '0.3rem', width: '2.6rem', height: '0.28rem', borderRadius: '999px', background: 'var(--color-voice-yellow)', transform: 'rotate(-1deg)', opacity: 0.9 }} />
            {threadTitle ? (
              <div style={{ marginTop: '0.6rem', fontSize: '0.78rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '16rem' }}>
                {threadTitle}
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            title={exporting ? t('chat.share.closeToBackground') : t('chat.history.close')}
            style={{
              width: '1.8rem',
              height: '1.8rem',
              flexShrink: 0,
              border: 'none',
              borderRadius: '0.55rem',
              background: 'transparent',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'grid',
              placeItems: 'center',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-bg-surface)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
          >
            <IconX style={{ width: '1rem', height: '1rem' }} />
          </button>
        </div>

        {preview ? (
          <>
            {/* 预览视图 — 长图定宽展示，超出高度内部滚动；超长对话为多张满分辨率分图无缝堆叠 */}
            <div
              style={{
                marginTop: '1rem',
                maxHeight: 'min(56vh, 26rem)',
                overflowY: 'auto',
                borderRadius: '0.85rem',
                border: '1px dashed color-mix(in srgb, var(--color-border-paper) 88%, transparent)',
                background: 'var(--color-bg-app)',
              }}
            >
              {preview.images.map((dataUrl, imageIndex) => (
                <img
                  key={imageIndex}
                  src={dataUrl}
                  alt={t('chat.share.previewTitle')}
                  style={{ display: 'block', width: '100%', height: 'auto' }}
                />
              ))}
            </div>
            <div style={{ marginTop: '0.55rem', fontSize: '0.72rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {preview.fileName}
              {!preview.partial && preview.images.length > 1 ? ` · ${t('chat.share.partsInfo', { count: preview.images.length })}` : ''}
            </div>
            {/* 预览头已上屏、完整长图仍在后台拼接时的进行态提示 + 进度条 */}
            {preview.partial ? (
              <div style={{ marginTop: '0.6rem' }}>
                {progressBar ?? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.76rem', color: 'var(--color-text-secondary)' }}>
                    <IconLoader style={{ width: '0.85rem', height: '0.85rem', flexShrink: 0, animation: 'spin 1s linear infinite' }} />
                    {t('chat.share.rendering')}
                  </div>
                )}
              </div>
            ) : null}
            {/* 操作行 — 下载图片（主操作） / 返回（次操作） */}
            <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.85rem' }}>
              <button
                type="button"
                onClick={onDownloadPreview}
                disabled={Boolean(preview.partial) || downloading}
                style={{
                  flex: 1.4,
                  height: '2.6rem',
                  border: 'none',
                  borderRadius: '0.9rem',
                  background: 'var(--color-export-action-bg)',
                  color: 'var(--color-export-action-text, #FFFFFF)',
                  cursor: preview.partial || downloading ? 'not-allowed' : 'pointer',
                  opacity: preview.partial || downloading ? 0.65 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.45rem',
                  fontSize: '0.86rem',
                  fontWeight: 600,
                  fontFamily: 'inherit',
                }}
              >
                {downloading ? (
                  <IconLoader style={{ width: '0.95rem', height: '0.95rem', animation: 'spin 1s linear infinite' }} />
                ) : (
                  <IconDownload style={{ width: '0.95rem', height: '0.95rem' }} />
                )}
                {downloading ? t('chat.share.merging') : t('chat.share.download')}
              </button>
              <button
                type="button"
                onClick={onDiscardPreview}
                style={{
                  flex: 1,
                  height: '2.6rem',
                  border: '1px solid var(--color-border-paper)',
                  borderRadius: '0.9rem',
                  background: 'transparent',
                  color: 'var(--color-text-secondary)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.45rem',
                  fontSize: '0.86rem',
                  fontWeight: 600,
                  fontFamily: 'inherit',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-bg-paper)'; e.currentTarget.style.color = 'var(--color-text-primary)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
              >
                {t('chat.share.back')}
              </button>
            </div>
          </>
        ) : exporting ? (
          /* 点分享即触发生成 — 首片预览未就绪前的占位加载视图（带进度条） */
          <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.7rem', padding: '2.2rem 1rem', borderRadius: '0.85rem', border: '1px dashed color-mix(in srgb, var(--color-border-paper) 88%, transparent)', background: 'var(--color-bg-app)' }}>
            <IconLoader style={{ width: '1.3rem', height: '1.3rem', color: 'var(--color-text-secondary)', animation: 'spin 1s linear infinite' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>{t('chat.share.preparingPreview')}</span>
            {progressBar ? <div style={{ width: '100%' }}>{progressBar}</div> : null}
          </div>
        ) : (
          <>
        {/* 选项列表 — 虚线纸边界条目，hover 才出现轻阴影（无卡片设计规则） */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', marginTop: '1rem' }}>
          {/* 复制链接 — 需求暂未实现，置灰 + 即将上线角标 */}
          <div
            aria-disabled="true"
            title={t('chat.share.comingSoon')}
            style={{ ...optionRowStyle, opacity: 0.55, cursor: 'not-allowed' }}
          >
            <IconCopy style={{ width: '1.05rem', height: '1.05rem', flexShrink: 0, color: 'var(--color-text-secondary)' }} />
            <span style={{ flex: 1, minWidth: 0, fontSize: '0.86rem', color: 'var(--color-text-primary)' }}>
              {t('chat.share.copyLink')}
            </span>
            <span style={{
              flexShrink: 0,
              fontSize: '0.68rem',
              fontWeight: 600,
              color: 'var(--color-text-secondary)',
              background: 'color-mix(in srgb, var(--color-voice-yellow) 20%, transparent)',
              borderRadius: '999px',
              padding: '0.16rem 0.55rem',
            }}>
              {t('chat.share.comingSoon')}
            </span>
          </div>

          {/* 导出图片 — 渲染后的长图 */}
          <button
            type="button"
            onClick={onExportImage}
            disabled={exporting || !canExport}
            style={{
              ...optionRowStyle,
              cursor: exporting || !canExport ? 'not-allowed' : 'pointer',
              opacity: !canExport ? 0.55 : 1,
              transition: 'background 0.14s ease, box-shadow 0.14s ease',
            }}
            onMouseEnter={(e) => {
              if (!exporting && canExport) {
                e.currentTarget.style.background = 'var(--color-bg-paper)';
                e.currentTarget.style.boxShadow = '0 1px 4px var(--color-shadow-soft)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {exporting ? (
              <IconLoader style={{ width: '1.05rem', height: '1.05rem', flexShrink: 0, color: 'var(--color-text-secondary)', animation: 'spin 1s linear infinite' }} />
            ) : (
              <IconImage style={{ width: '1.05rem', height: '1.05rem', flexShrink: 0, color: 'var(--color-text-secondary)' }} />
            )}
            <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
              <span style={{ fontSize: '0.86rem', color: 'var(--color-text-primary)' }}>
                {exporting ? t('chat.share.exporting') : t('chat.share.exportImage')}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                {t('chat.share.exportImageHint')}
              </span>
            </span>
          </button>
        </div>

        {exportFailed ? (
          <div style={{ marginTop: '0.7rem', fontSize: '0.76rem', color: 'var(--color-state-error)', textAlign: 'center' }}>
            {t('chat.share.exportFailed')}
          </div>
        ) : null}
          </>
        )}
      </div>
    </div>
  );
}
