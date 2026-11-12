// [Sync] 2026-11-12: explain model-selection and pending-turn conflicts through localized recovery copy.
// [Input] Persistent WritingSuggestionCell state and explicit generate/retry callbacks from the Writing controller.
// [Output] Render manual suggestions, retry feedback and existing subscription/model recovery links across streaming, completed, and failed states.
// [Pos] Writing editor suggestion presentation in frontend/app/_dream/components/Editor.
// [Sync] 2026-09-01: introduce accessible Token-based persistent suggestion Cells and manual triggers.
// [Sync] 2026-09-01: keep historical suggestion Cells read-only; only the latest Cell exposes Refresh or Retry.

import { useTranslation } from 'react-i18next';
import type { WritingSuggestionCell as WritingSuggestionCellData } from '../../engine/EditorEngine';
import { STORY_WORKSPACE_PATHS } from '../../router/storyWorkspacePath';
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
  if (code === 'GATEWAY_MODEL_SELECTION_STALE' || code === 'GATEWAY_MODEL_SELECTION_CONFLICT') {
    return 'writingSuggestion.errors.modelSelection';
  }
  if (code === 'CHAT_INPUT_USE_QUEUE') return 'writingSuggestion.errors.busy';
  if (code === 'CHAT_INPUT_RECONCILIATION_REQUIRED') return 'writingSuggestion.errors.pendingInput';
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
  const showModelRecovery = isLatestSuggestion && cell.status === 'failed'
    && (cell.error?.code === 'GATEWAY_MODEL_SELECTION_STALE'
      || cell.error?.code === 'GATEWAY_MODEL_SELECTION_CONFLICT');
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

        {showModelRecovery ? (
          <div>
            <a className="writing-suggestion-cell__action" href={STORY_WORKSPACE_PATHS.subscription}>
              {t('writingSuggestion.checkSubscription')}
            </a>
            <a className="writing-suggestion-cell__action" href={STORY_WORKSPACE_PATHS['settings-model']}>
              {t('writingSuggestion.checkModel')}
            </a>
          </div>
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
