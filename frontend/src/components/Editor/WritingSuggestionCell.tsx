// [Input] Persistent WritingSuggestionCell state and explicit generate/retry callbacks from the Writing controller.
// [Output] Render the manual Go deeper trigger and read-only suggestion Cell across streaming, completed, and failed states.
// [Pos] Writing editor suggestion presentation in frontend/src/components/Editor.
// [Sync] 2026-09-01: introduce accessible Token-based persistent suggestion Cells and manual triggers.
// [Sync] 2026-09-01: keep historical suggestion Cells read-only; only the latest Cell exposes Refresh or Retry.

import { useTranslation } from 'react-i18next';
import type { WritingSuggestionCell as WritingSuggestionCellData } from '../../engine/EditorEngine';
import { IconSparkles } from '../chat/Icons';
import './WritingSuggestionCell.css';

interface WritingSuggestionTriggerProps {
  onGenerate: () => void;
}

export function WritingSuggestionTrigger({ onGenerate }: WritingSuggestionTriggerProps) {
  const { t } = useTranslation();
  return (
    <div className="writing-suggestion-trigger">
      <button type="button" className="writing-suggestion-trigger__button" onClick={onGenerate}>
        <IconSparkles aria-hidden="true" />
        <span>{t('writingSuggestion.goDeeper')}</span>
      </button>
    </div>
  );
}

interface WritingSuggestionCellProps {
  cell: WritingSuggestionCellData;
  isLatestSuggestion: boolean;
  onRetry: () => void;
}

function errorTranslationKey(code: string | undefined): string {
  if (code === 'WRITING_THREAD_CREATE_FAILED') return 'writingSuggestion.errors.threadCreate';
  if (code === 'WRITING_THREAD_PERSIST_FAILED') return 'writingSuggestion.errors.threadPersist';
  if (code === 'WRITING_SSE_INTERRUPTED') return 'writingSuggestion.errors.interrupted';
  return 'writingSuggestion.unavailable';
}

export function WritingSuggestionCell({
  cell,
  isLatestSuggestion,
  onRetry,
}: WritingSuggestionCellProps) {
  const { t } = useTranslation();
  const isStreaming = cell.status === 'streaming';
  const displayedContent = cell.content || (isStreaming ? cell.previousContent : '') || '';
  const isPreviousContent = isStreaming && !cell.content && Boolean(cell.previousContent);
  const showAction = isLatestSuggestion
    && (cell.status === 'completed'
      || (cell.status === 'failed' && cell.error?.retryable !== false));

  return (
    <article
      className={`writing-suggestion-cell writing-suggestion-cell--${cell.status}`}
      aria-label={t('writingSuggestion.regionLabel')}
      aria-busy={isStreaming}
      data-suggestion-cell-id={cell.id}
    >
      <div className="writing-suggestion-cell__body">
        {displayedContent ? (
          <p
            className={`writing-suggestion-cell__content${isPreviousContent ? ' writing-suggestion-cell__content--previous' : ''}`}
          >
            {displayedContent}
          </p>
        ) : null}

        {isStreaming ? (
          <div className="writing-suggestion-cell__streaming" role="status">
            <IconSparkles aria-hidden="true" />
            <span className="writing-suggestion-cell__status-text">
              {t('writingSuggestion.loading')}
            </span>
          </div>
        ) : null}

        {cell.status === 'failed' ? (
          <p className="writing-suggestion-cell__error" role="status">
            {t(errorTranslationKey(cell.error?.code))}
          </p>
        ) : null}

        {showAction ? (
          <button type="button" className="writing-suggestion-cell__action" onClick={onRetry}>
            <IconSparkles aria-hidden="true" />
            <span>
              {t(cell.status === 'completed'
                ? 'writingSuggestion.refresh'
                : 'writingSuggestion.retry')}
            </span>
          </button>
        ) : null}
      </div>
    </article>
  );
}
