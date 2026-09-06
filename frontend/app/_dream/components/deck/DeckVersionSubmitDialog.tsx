// [Input] Server-computed Deck draft diff and explicit commit callback.
// [Output] Confirm/cancel modal for creating immutable vN without hidden writes.
// [Pos] Deck content-version submit confirmation inside DeckEditorModal.
// [Sync] 2026-08-16: add first-version and vN+1 confirmation states.

import { useState } from 'react';
import type { DeckContentVersionPreview } from '../../api/deckVersionApi';

interface Props {
  deckName: string;
  preview: DeckContentVersionPreview;
  submitting: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: (description: string) => Promise<boolean>;
}

export default function DeckVersionSubmitDialog({ deckName, preview, submitting, error, onCancel, onConfirm }: Props) {
  const [description, setDescription] = useState('');
  return (
    <div className="deck-version-submit-backdrop" onClick={(event) => event.stopPropagation()} role="presentation">
      <section aria-labelledby="deck-version-submit-title" aria-modal="true" className="deck-version-submit" role="dialog">
        <header>
          <div>
            <span className="deck-version-current__eyebrow">{preview.latest_version ? `基于 v${preview.latest_version}` : '首次提交'}</span>
            <h2 id="deck-version-submit-title">提交 {deckName} 为 v{preview.target_version}</h2>
          </div>
          <button aria-label="关闭提交版本弹窗" className="deck-icon-button" disabled={submitting} onClick={onCancel} type="button">×</button>
        </header>
        <p className="deck-version-submit__lead">提交会冻结当前 Deck 表单内容；历史 Thread 不会自动升级。</p>
        <div className="deck-version-submit__changes" aria-label="版本变更摘要">
          {preview.changes.map((change) => (
            <div key={`${change.scope}-${change.change_type}`}>
              <strong>{change.label}</strong>
              <span>{change.change_type === 'added' ? '新增' : change.change_type === 'removed' ? '移除' : '修改'}{change.fields.length ? ` · ${change.fields.join('、')}` : ''}</span>
            </div>
          ))}
        </div>
        <label className="deck-field-group">
          <span>版本说明（可选）</span>
          <textarea maxLength={200} onChange={(event) => setDescription(event.target.value)} placeholder="说明这次修改的目的" rows={3} value={description} />
        </label>
        {error && <p className="deck-version-panel__status is-error" role="alert">{error}</p>}
        <footer>
          <button className="deck-secondary-button" disabled={submitting} onClick={onCancel} type="button">取消</button>
          <button className="deck-primary-button" disabled={submitting} onClick={() => void onConfirm(description)} type="button">
            {submitting ? '提交中…' : `确认提交 v${preview.target_version}`}
          </button>
        </footer>
      </section>
    </div>
  );
}
