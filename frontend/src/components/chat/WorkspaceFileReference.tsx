// [Input] Parsed workspace:// URI, current Chat Thread identity, Workspace Mode state, runtime API base, and bearer auth token.
// [Output] Abortable authenticated image thumbnail/shared Mermaid-style zoom preview or user-activated regular-file download with stable fail-closed states.
// [Pos] workspace file Markdown reference component in frontend/src/components/chat
// [Sync] 2026-08-22: initial blob-backed image/download rendering; credentials and Thread identity remain runtime-only and never enter Markdown.
// [Sync] 2026-08-22: resolve all user-facing loading/error/download states through the existing chat i18n namespace.
// [Sync] 2026-08-22: constrain Workspace images to the v2.1 paper-card footprint and open the same ephemeral blob in an accessible full-size modal.
// [Sync] 2026-08-23: reuse the shared authenticated Workspace access helper also consumed by long-image export.
// [Sync] 2026-08-23: align successful images with Mermaid's exact media frame and immersive download/close/zoom skeleton.
// [Sync] 2026-08-23: scope immersive zoom to the full-size image node instead of scaling its paper sheet.

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { IconDownload, IconMaximize } from './Icons';
import Modal from './Modal';
import { parseWorkspaceUri, type WorkspaceUriParseResult } from './workspaceUri';
import {
  fetchWorkspaceFile,
  fetchWorkspaceImageBlob,
  WorkspaceFileRequestError,
  type WorkspaceFileRequestFailure,
} from './workspaceFileAccess';
import './MarkdownMedia.css';
import './WorkspaceFileReference.css';

type WorkspaceAvailability = 'loading' | 'enabled' | 'disabled';

type ImageState =
  | { readonly kind: 'loading' }
  | { readonly kind: 'success'; readonly objectUrl: string }
  | { readonly kind: 'error'; readonly failure: WorkspaceFileRequestFailure };

interface WorkspaceReferenceProps {
  readonly uri: string;
  readonly threadId?: string;
  readonly workspaceAvailability: WorkspaceAvailability;
}

interface WorkspaceImageProps extends WorkspaceReferenceProps {
  readonly alt?: string;
}

interface WorkspaceLinkProps extends WorkspaceReferenceProps {
  readonly children: ReactNode;
}

function failureKey(failure: WorkspaceFileRequestFailure): string {
  switch (failure) {
    case 'access': return 'chat.workspaceFile.access';
    case 'disabled': return 'chat.workspaceFile.disabled';
    case 'invalid': return 'chat.workspaceFile.invalid';
    case 'missing': return 'chat.workspaceFile.missing';
    case 'unsupported': return 'chat.workspaceFile.unsupported';
    case 'retryable': return 'chat.workspaceFile.retryable';
  }
}

const statusStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  flexWrap: 'wrap',
  gap: '0.35rem',
  maxWidth: '100%',
  borderRadius: '0.6rem',
  border: '1px solid var(--color-border-paper)',
  background: 'var(--color-bg-surface)',
  color: 'var(--color-text-muted)',
  padding: '0.45rem 0.65rem',
  fontSize: '0.8rem',
  lineHeight: 1.5,
} as const;

const linkButtonStyle = {
  border: 0,
  background: 'transparent',
  color: 'var(--color-action-link)',
  cursor: 'pointer',
  font: 'inherit',
  padding: 0,
  textDecoration: 'underline',
} as const;

function staticFailure(
  parsed: WorkspaceUriParseResult,
  threadId: string | undefined,
  availability: WorkspaceAvailability,
): WorkspaceFileRequestFailure | null {
  if (!parsed.ok) return 'invalid';
  if (availability === 'disabled') return 'disabled';
  if (availability === 'enabled' && !threadId) return 'missing';
  return null;
}

export function WorkspaceFileLink({
  uri,
  threadId,
  workspaceAvailability,
  children,
}: WorkspaceLinkProps) {
  const { t } = useTranslation();
  const parsed = useMemo(() => parseWorkspaceUri(uri), [uri]);
  const [failure, setFailure] = useState<WorkspaceFileRequestFailure | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const fixedFailure = staticFailure(parsed, threadId, workspaceAvailability);

  useEffect(() => {
    setFailure(null);
    setDownloaded(false);
  }, [threadId, uri, workspaceAvailability]);

  const download = async () => {
    if (!parsed.ok || !threadId || workspaceAvailability !== 'enabled' || downloading) return;
    setDownloading(true);
    setFailure(null);
    setDownloaded(false);
    try {
      const response = await fetchWorkspaceFile(parsed, threadId);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = parsed.fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
      setDownloaded(true);
    } catch (reason) {
      setFailure(reason instanceof WorkspaceFileRequestError ? reason.failure : 'retryable');
    } finally {
      setDownloading(false);
    }
  };

  if (workspaceAvailability === 'loading' && parsed.ok) {
    return <span role="status" data-workspace-file-state="loading" style={statusStyle}>{t('chat.workspaceFile.checking')}</span>;
  }
  if (fixedFailure) {
    return <span data-workspace-file-state={fixedFailure} style={statusStyle}>{children} — {t(failureKey(fixedFailure))}</span>;
  }

  const currentFailure = failure;
  return (
    <span data-workspace-file-state={currentFailure ?? (downloaded ? 'success' : 'ready')} style={statusStyle}>
      <button type="button" style={linkButtonStyle} disabled={downloading} aria-busy={downloading} onClick={() => { void download(); }}>
        {children}
      </button>
      {downloading ? <span role="status">{t('chat.workspaceFile.downloading')}</span> : null}
      {downloaded ? <span role="status">{t('chat.workspaceFile.downloadStarted')}</span> : null}
      {currentFailure ? <span role="alert">{t(failureKey(currentFailure))}</span> : null}
    </span>
  );
}

export function WorkspaceImage({
  uri,
  threadId,
  workspaceAvailability,
  alt = '',
}: WorkspaceImageProps) {
  const { t } = useTranslation();
  const parsed = useMemo(() => parseWorkspaceUri(uri), [uri]);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<ImageState>({ kind: 'loading' });
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewZoom, setPreviewZoom] = useState(100);
  const fixedFailure = staticFailure(parsed, threadId, workspaceAvailability);

  useEffect(() => {
    if (!parsed.ok || !threadId || workspaceAvailability !== 'enabled' || !parsed.canPreviewImage) return;
    const abort = new AbortController();
    let objectUrl: string | null = null;
    setState({ kind: 'loading' });

    void (async () => {
      try {
        const blob = await fetchWorkspaceImageBlob(parsed, threadId, abort.signal);
        objectUrl = URL.createObjectURL(blob);
        setState({ kind: 'success', objectUrl });
      } catch (reason) {
        if (reason instanceof DOMException && reason.name === 'AbortError') return;
        setState({
          kind: 'error',
          failure: reason instanceof WorkspaceFileRequestError ? reason.failure : 'retryable',
        });
      }
    })();

    return () => {
      abort.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attempt, parsed, threadId, workspaceAvailability]);

  if (workspaceAvailability === 'loading' && parsed.ok) {
    return <span role="status" data-workspace-file-state="loading" style={statusStyle}>{t('chat.workspaceFile.loadingImage')}</span>;
  }
  if (fixedFailure) {
    return <span data-workspace-file-state={fixedFailure} style={statusStyle}>{alt || t('chat.workspaceFile.imageAlt')} — {t(failureKey(fixedFailure))}</span>;
  }
  if (parsed.ok && !parsed.canPreviewImage) {
    return (
      <span data-workspace-file-state="unsupported" style={statusStyle}>
        {t(failureKey('unsupported'))}
        <WorkspaceFileLink uri={uri} threadId={threadId} workspaceAvailability={workspaceAvailability}>
          {alt || parsed.fileName}
        </WorkspaceFileLink>
      </span>
    );
  }
  if (state.kind === 'success') {
    const previewName = alt.trim() || (parsed.ok ? parsed.fileName : t('chat.workspaceFile.imageAlt'));
    const downloadLoadedImage = () => {
      const anchor = document.createElement('a');
      anchor.href = state.objectUrl;
      anchor.download = parsed.ok ? parsed.fileName : 'workspace-image';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    };
    const openPreview = () => {
      setPreviewZoom(100);
      setPreviewOpen(true);
    };
    return (
      <>
        <span className="markdown-media-block" data-markdown-media-kind="workspace-image">
          <span className="markdown-media-block__toolbar">
            <span className="markdown-media-block__label">{previewName}</span>
            <button
              type="button"
              className="markdown-media-block__action"
              title={t('chat.workspaceFile.previewAction', { name: previewName })}
              aria-label={t('chat.workspaceFile.previewAction', { name: previewName })}
              aria-haspopup="dialog"
              onClick={openPreview}
            >
              <IconMaximize />
            </button>
            <button
              type="button"
              className="markdown-media-block__action"
              title={t('chat.workspaceFile.downloadImage')}
              aria-label={t('chat.workspaceFile.downloadImage')}
              onClick={downloadLoadedImage}
            >
              <IconDownload />
            </button>
          </span>
          <span className="markdown-media-block__content">
            <button
              type="button"
              className="workspace-image-reference__trigger"
              aria-label={t('chat.workspaceFile.previewAction', { name: previewName })}
              aria-haspopup="dialog"
              onClick={openPreview}
            >
              <img
                className="workspace-image-reference__thumbnail"
                src={state.objectUrl}
                alt={alt}
                loading="lazy"
                decoding="async"
                data-workspace-file-state="success"
                data-workspace-file-preview="thumbnail"
                onError={() => {
                  setPreviewOpen(false);
                  URL.revokeObjectURL(state.objectUrl);
                  setState({ kind: 'error', failure: 'unsupported' });
                }}
              />
            </button>
          </span>
        </span>
        <Modal
          open={previewOpen}
          title={t('chat.workspaceFile.previewTitle', { name: previewName })}
          closeLabel={t('chat.workspaceFile.closePreview')}
          variant="media-preview"
          onClose={() => setPreviewOpen(false)}
          toolbarActions={(
            <button
              type="button"
              className="modal-toolbar-button"
              title={t('chat.workspaceFile.downloadImage')}
              aria-label={t('chat.workspaceFile.downloadImage')}
              onClick={downloadLoadedImage}
            >
              <IconDownload />
            </button>
          )}
          zoom={{
            value: previewZoom,
            onChange: setPreviewZoom,
            zoomOutLabel: t('chat.mediaPreview.zoomOut'),
            zoomInLabel: t('chat.mediaPreview.zoomIn'),
          }}
        >
          <figure className="markdown-media-preview__sheet workspace-image-reference__fullsize-frame">
            <img
              className="workspace-image-reference__fullsize markdown-media-preview__zoom-target"
              src={state.objectUrl}
              alt={alt || previewName}
              data-workspace-file-preview="fullsize"
            />
          </figure>
        </Modal>
      </>
    );
  }
  if (state.kind === 'error') {
    return (
      <span data-workspace-file-state={state.failure} style={statusStyle}>
        <span role="alert">{alt || t('chat.workspaceFile.imageAlt')} — {t(failureKey(state.failure))}</span>
        {state.failure === 'retryable' ? (
          <button type="button" style={linkButtonStyle} onClick={() => setAttempt((value) => value + 1)}>{t('chat.workspaceFile.retry')}</button>
        ) : null}
      </span>
    );
  }
  return <span role="status" data-workspace-file-state="loading" style={statusStyle}>{alt || t('chat.workspaceFile.imageAlt')} — {t('chat.workspaceFile.loading')}</span>;
}
