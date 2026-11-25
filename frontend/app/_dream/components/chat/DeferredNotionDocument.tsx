// [Input] Page identity, title and Markdown obtained by the calling surface.
// [Output] Lazy shared Notion page reader with localized render failure and retry.
// [Pos] Shared document rendering for Chat results and Writing article links.
import {Component, lazy, Suspense, useMemo, useState, type ReactNode} from 'react';
import {useTranslation} from 'react-i18next';
import type {NotionDocumentData} from './notionRecordMapAdapter';

class DocumentBoundary extends Component<{children: ReactNode; fallback: ReactNode}, {failed: boolean}> {
  state = {failed: false};
  static getDerivedStateFromError() {return {failed: true};}
  render() {return this.state.failed ? this.props.fallback : this.props.children;}
}
export default function DeferredNotionDocument({data, renderFailed}: {data: NotionDocumentData; renderFailed: string}) {
  const {t} = useTranslation();
  const [attempt, setAttempt] = useState(0);
  // A fresh lazy instance permits an explicit retry after a rejected module/render attempt.
  const Document = useMemo(() => {void attempt; return lazy(() => import('./NotionPageDocument'));}, [attempt]);
  return <DocumentBoundary key={attempt} fallback={<p role="alert">{renderFailed} <button type="button" onClick={() => setAttempt(value => value + 1)}>{t('chat.notionPreview.retry')}</button></p>}>
    <Suspense fallback={<p role="status">{t('chat.notionPreview.loading')}</p>}><Document data={data}/></Suspense>
  </DocumentBoundary>;
}
