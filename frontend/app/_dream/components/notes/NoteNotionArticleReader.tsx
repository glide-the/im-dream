// [Input] URL selected in the current note and its validated page identity.
// [Output] Cancellable authenticated article read, original link, retry and shared Notion rendering.
// [Pos] Ephemeral Writing reader. Closing releases the body and request.
import {useEffect, useState} from 'react';
import {useTranslation} from 'react-i18next';
import {fetchJson, ResourceConnectorApiError} from '../../api/resourceConnectorApi';
import Modal from '../chat/Modal';
import DeferredNotionDocument from '../chat/DeferredNotionDocument';
import type {NotionDocumentData} from '../chat/notionRecordMapAdapter';
import type {NotionArticleLink} from './notionArticleLinks';
import '../chat/NotionWorkspacePreview.css';

type Feedback = 'connection' | 'scope' | 'access' | 'changed' | 'failed';
function feedback(error: unknown): Feedback {
  if (error instanceof ResourceConnectorApiError) {
    if (['NOTION_AUTH_EXPIRED', 'NOTION_CONNECTOR_UNAVAILABLE'].includes(error.code)) return 'connection';
    if (['NOTION_RESOURCE_NOT_SELECTED', 'NOTION_SNAPSHOT_NOT_READY'].includes(error.code)) return 'scope';
    if (error.code === 'NOTION_CONTEXT_CHANGED') return 'changed';
    if (error.status === 403 || error.code === 'NOTION_RESOURCE_UNAVAILABLE') return 'access';
  }
  return 'failed';
}

export default function NoteNotionArticleReader({link, onClose}: {link: NotionArticleLink; onClose: () => void}) {
  const {t} = useTranslation();
  const [result, setResult] = useState<NotionDocumentData | Feedback | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const data = await fetchJson<Partial<NotionDocumentData> | null>(
          `/api/connectors/notion/articles/${link.pageId}`, {signal: controller.signal, cache: 'no-store'});
        if (typeof data?.pageId !== 'string' || data.pageId.replaceAll('-', '').toLowerCase() !== link.pageId
          || typeof data.title !== 'string' || typeof data.markdown !== 'string') throw Error('Invalid article response');
        if (!controller.signal.aborted) setResult({pageId: data.pageId, title: data.title, markdown: data.markdown});
      } catch (error) {
        if (!controller.signal.aborted) setResult(feedback(error));
      }
    }
    void load();
    return () => controller.abort();
  }, [link.pageId, attempt]);

  const data = typeof result === 'object' ? result : null;
  return <Modal open onClose={onClose} title={data?.title || link.label} closeLabel={t('chat.notionPreview.close')}
    variant="conversation-preview" surfaceClassName="notion-preview__reader"
    toolbarActions={<a className="note-article-original" href={link.href} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">{t('noteArticle.original')}</a>}>
    <article className="notion-preview__body" tabIndex={0} aria-label={t('chat.notionPreview.body')}>
      {result === null && <p role="status">{t('chat.notionPreview.loading')}</p>}
      {typeof result === 'string' && <p role="alert">{t(`noteArticle.${result}`)} <button type="button" onClick={() => {
        setResult(null);
        setAttempt(value => value + 1);
      }}>{t('chat.notionPreview.retry')}</button></p>}
      {data && (data.markdown.trim()
        ? <DeferredNotionDocument data={data} renderFailed={t('noteArticle.renderFailed')}/>
        : <p>{t('chat.notionPreview.empty')}</p>)}
    </article>
  </Modal>;
}
