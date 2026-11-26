// [Sync] 2026-11-24: share deferred document rendering with Writing.
// [Input] Validated existing Read result, current Thread and ChatPanel preview container.
// [Output] Compact excerpt, on-demand react-notion-x reading and same-result JSON inspection/download.
// [Pos] Web Chat result presentation; no connector, network, tool or persistence operations.
// [Sync] 2026-11-18: compact borderless preview with title-row download/expand and a two-line excerpt.
import {useMemo, useRef, useState} from 'react';
import {useTranslation} from 'react-i18next';
import Modal from './Modal';
import DeferredNotionDocument from './DeferredNotionDocument';
import {IconDownload, IconFile, IconMaximize} from './Icons';
import {notionPreviewExcerpt, type NotionWorkspacePreviewData} from './notionPreviewProjection';
import './NotionWorkspacePreview.css';

export default function NotionWorkspacePreview({data}: {data: NotionWorkspacePreviewData; threadId: string}) {
  const {t} = useTranslation();
  const [open, setOpen] = useState(false), [json, setJson] = useState(false), [downloadFailed, setDownloadFailed] = useState(false);
  const anchor = useRef<HTMLElement>(null);
  const title = data.title || t('chat.notionPreview.untitled');
  const excerpt = useMemo(() => notionPreviewExcerpt(data.markdown, data.title), [data.markdown, data.title]);
  const detail = useMemo(() => json && data.payload ? JSON.stringify(data.payload, null, 2) : '', [json, data.payload]);
  const close = () => {setOpen(false); setJson(false);};
  const failure = t(`chat.notionPreview.${data.failure}`);
  function download() {
    if (!data.payload) return;
    let url: string | undefined;
    try {
      url = URL.createObjectURL(new Blob([JSON.stringify(data.payload, null, 2)], {type: 'application/json;charset=utf-8'}));
      const link = document.createElement('a');
      link.href = url; link.download = `${data.pageId}.json`; document.body.append(link); link.click(); link.remove();
      setDownloadFailed(false);
    } catch { setDownloadFailed(true); }
    finally { if (url) {const ownedUrl = url; window.setTimeout(() => URL.revokeObjectURL(ownedUrl), 0);} }
  }
  const downloadAction = <button className="notion-preview__download" type="button" onClick={download} disabled={!data.payload} aria-label={t('chat.notionPreview.download')} title={t('chat.notionPreview.download')}><IconDownload/><span>{t('chat.notionPreview.download')}</span></button>;
  return <section ref={anchor} className="notion-preview" data-notion-page={data.pageId} data-state={data.state} aria-label={title}>
    <header className="notion-preview__header">
      <span className="notion-preview__document-icon" aria-hidden="true"><IconFile/></span>
      <div className="notion-preview__identity"><h3 className="notion-preview__title" title={title}>{title}</h3></div>
      <div className="notion-preview__actions">
        {downloadAction}
        <button className="notion-preview__read" type="button" onClick={() => setOpen(true)} aria-haspopup="dialog" aria-label={t('chat.notionPreview.expand', {title})} title={t('chat.notionPreview.expand', {title})}><IconMaximize/></button>
      </div>
    </header>
    {data.state === 'error' ? <p className="notion-preview__failure" role="alert">{failure}</p>
      : <p className="notion-preview__excerpt">{excerpt || t('chat.notionPreview.empty')}</p>}
    {downloadFailed && !open ? <p role="alert">{t('chat.notionPreview.downloadFailed')}</p> : null}
    <Modal open={open} title={title} onClose={close} closeLabel={t('chat.notionPreview.close')}
      variant="conversation-preview" portalContainer={anchor.current?.closest<HTMLElement>('[data-chat-preview-container]') ?? undefined}
      surfaceClassName="notion-preview__reader" toolbarActions={<><button type="button" aria-pressed={json} onClick={() => setJson(value => !value)}>{t(json ? 'chat.notionPreview.body' : 'chat.notionPreview.json')}</button>{downloadAction}</>}>
      {downloadFailed ? <p role="alert">{t('chat.notionPreview.downloadFailed')}</p> : null}
      <div className={`notion-preview__panes${json ? ' notion-preview__panes--json' : ''}`}>
        <article className="notion-preview__body" tabIndex={0} aria-label={t('chat.notionPreview.body')}>
          {data.state === 'error' ? <p role="alert">{failure}</p> : data.markdown.trim() ? <DeferredNotionDocument data={data} renderFailed={t('chat.notionPreview.renderFailed')}/> : <p>{t('chat.notionPreview.empty')}</p>}
        </article>
        {json ? <aside className="notion-preview__json" aria-label={t('chat.notionPreview.json')}><pre tabIndex={0}>{detail}</pre></aside> : null}
      </div>
    </Modal>
  </section>;
}
