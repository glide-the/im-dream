// [Input] A selected Agent-generated Story Workspace resource and server provenance.
// [Output] Editable proposal detail with confirm/reject review actions.
// [Pos] Dream right-rail business review surface.
// [Sync] 2026-08-04: mount StoryWorkspaceSurfaceLinkButton in the proposal
//                    detail area (Task 4, design_004 §4); surfaces resolve via
//                    the source receipt's chat thread, link state arrives as
//                    server-aggregated props (hidden while absent).

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  confirmReviewResource,
  getReviewResource,
  patchReviewResource,
  rejectReviewResource,
  type StoryWorkspaceReviewResource,
  type StoryWorkspaceReviewResourceType,
  type StoryWorkspaceStoryDetail,
} from '../../../api/storyWorkspaceReviewApi';
import type { StoryWorkspaceOutputReceipt } from '../../../lib/story-workspace-events';
import { useWorkspaceSurfaces } from '../../../hooks/story-workspace';
import type { StoryWorkspaceSurfaceLinkState } from '../../../hooks/story-workspace/contracts';
import { StoryWorkspaceSurfaceLinkButton } from '../StoryWorkspaceSurfaceLinkButton';

export interface StoryWorkspaceReviewSelection {
  resourceType: StoryWorkspaceReviewResourceType;
  resourceId: string;
}

/**
 * Server-aggregated Dream surface link context for the selected proposal
 * (design_004 §4.1). Optional: while no server aggregation binds proposals
 * to runs, callers omit it and the link stays hidden.
 */
export interface StoryWorkspaceReviewSurfaceLink {
  runId: string | null;
  episodeId?: string | null;
  state: StoryWorkspaceSurfaceLinkState | null;
}

export interface StoryWorkspaceReviewDetailProps {
  selection: StoryWorkspaceReviewSelection;
  sourceReceipt?: StoryWorkspaceOutputReceipt | null;
  surfaceLink?: StoryWorkspaceReviewSurfaceLink | null;
  onChanged: (resource: StoryWorkspaceReviewResource) => void;
  onSelectResource?: (selection: StoryWorkspaceReviewSelection) => void;
}

type Draft = Record<string, string>;

const RESOURCE_LABELS: Record<StoryWorkspaceReviewResourceType, string> = {
  story: '故事提案',
  character: '角色提案',
  scene: '场景提案',
};

function draftFromResource(
  type: StoryWorkspaceReviewResourceType,
  resource: StoryWorkspaceReviewResource,
): Draft {
  if (type === 'story') {
    const story = resource as StoryWorkspaceReviewResource & {
      title: string; description?: string | null; content?: string | null; type: string;
    };
    return {
      title: story.title,
      description: story.description ?? '',
      content: story.content ?? '',
      type: story.type,
    };
  }
  if (type === 'character') {
    const character = resource as StoryWorkspaceReviewResource & {
      name: string; identity?: string | null; personality?: string | null;
      background?: string | null; catchphrase?: string | null; tags?: string[];
    };
    return {
      name: character.name,
      identity: character.identity ?? '',
      personality: character.personality ?? '',
      background: character.background ?? '',
      catchphrase: character.catchphrase ?? '',
      tags: (character.tags ?? []).join('，'),
    };
  }
  const scene = resource as StoryWorkspaceReviewResource & {
    name: string; description?: string | null; order_index?: number;
  };
  return {
    name: scene.name,
    description: scene.description ?? '',
    order_index: String(scene.order_index ?? 0),
  };
}

function patchFromDraft(type: StoryWorkspaceReviewResourceType, draft: Draft) {
  if (type === 'story') {
    return {
      title: draft.title.trim(),
      description: draft.description.trim() || null,
      content: draft.content.trim() || null,
      type: draft.type,
    };
  }
  if (type === 'character') {
    return {
      name: draft.name.trim(),
      identity: draft.identity.trim() || null,
      personality: draft.personality.trim() || null,
      background: draft.background.trim() || null,
      catchphrase: draft.catchphrase.trim() || null,
      tags: draft.tags.split(/[，,]/).map((tag) => tag.trim()).filter(Boolean),
    };
  }
  return {
    name: draft.name.trim(),
    description: draft.description.trim() || null,
    order_index: Number.parseInt(draft.order_index, 10) || 0,
  };
}

export function StoryWorkspaceReviewDetail({
  selection,
  sourceReceipt,
  surfaceLink,
  onChanged,
  onSelectResource,
}: StoryWorkspaceReviewDetailProps) {
  const [resource, setResource] = useState<StoryWorkspaceReviewResource | null>(null);
  const [draft, setDraft] = useState<Draft>({});
  const [reviewNotes, setReviewNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dream surface discovery needs the originating chat thread; only fetch when
  // aggregated link state is actually supplied (undefined = hidden, DEC-028).
  const surfaces = useWorkspaceSurfaces(
    surfaceLink?.runId && surfaceLink.state ? sourceReceipt?.chat_thread_id : undefined,
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await getReviewResource(selection.resourceType, selection.resourceId);
      setResource(next);
      setDraft(draftFromResource(selection.resourceType, next));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '无法加载审阅内容。');
    } finally {
      setLoading(false);
    }
  }, [selection.resourceId, selection.resourceType]);

  useEffect(() => {
    void load();
  }, [load]);

  const isPending = resource?.review_status === 'pending';
  const title = useMemo(() => (
    draft.title || draft.name || RESOURCE_LABELS[selection.resourceType]
  ), [draft.name, draft.title, selection.resourceType]);

  const update = (field: string, value: string) => {
    setDraft((current) => ({ ...current, [field]: value }));
  };

  const saveDraft = useCallback(async () => {
    const next = await patchReviewResource(
      selection.resourceType,
      selection.resourceId,
      patchFromDraft(selection.resourceType, draft),
    );
    setResource(next);
    setDraft(draftFromResource(selection.resourceType, next));
    return next;
  }, [draft, selection.resourceId, selection.resourceType]);

  const runAction = async (action: 'save' | 'confirm' | 'reject') => {
    if (saving) return;
    if (action === 'reject' && !reviewNotes.trim()) {
      setError('请填写驳回原因，Agent 将据此继续修改。');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      let next = action === 'reject' ? resource : await saveDraft();
      if (action === 'confirm') {
        next = await confirmReviewResource(selection.resourceType, selection.resourceId);
      } else if (action === 'reject') {
        next = await rejectReviewResource(
          selection.resourceType,
          selection.resourceId,
          reviewNotes.trim(),
        );
      }
      if (next) {
        setResource(next);
        setDraft(draftFromResource(selection.resourceType, next));
        onChanged(next);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '审阅操作失败。');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <p className="story-workspace-review-detail__state">正在加载提案…</p>;
  if (!resource) {
    return (
      <div className="story-workspace-review-detail__state">
        <p>{error ?? '提案不存在或无权查看。'}</p>
        <button className="workflow-button" onClick={() => void load()} type="button">重新加载</button>
      </div>
    );
  }

  const deckName = sourceReceipt?.deck_name_zh
    || sourceReceipt?.deck_name
    || sourceReceipt?.deck_name_en;
  const storyDetail = selection.resourceType === 'story'
    ? resource as StoryWorkspaceStoryDetail
    : null;

  return (
    <article className="story-workspace-review-detail">
      <header className="story-workspace-review-detail__hero">
        <span>{RESOURCE_LABELS[selection.resourceType]}</span>
        <h3>{title}</h3>
        <p data-review-status={resource.review_status}>
          {resource.review_status === 'pending'
            ? '等待你的决定'
            : resource.review_status === 'confirmed'
              ? storyDetail?.status === 'published' ? '已确认 · 后续发布已完成' : '已确认'
              : '已驳回'}
        </p>
      </header>

      {sourceReceipt && (
        <dl className="story-workspace-review-detail__source">
          <div><dt>来源</dt><dd>Dream Chat</dd></div>
          <div><dt>Deck</dt><dd>{deckName || '未使用 Deck'}</dd></div>
          <div><dt>Thread</dt><dd><code>{sourceReceipt.chat_thread_id}</code></dd></div>
        </dl>
      )}

      {surfaceLink && (
        <StoryWorkspaceSurfaceLinkButton
          episodeId={surfaceLink.episodeId}
          runId={surfaceLink.runId}
          state={surfaceLink.state}
          surfaces={surfaces}
        />
      )}

      <div className="story-workspace-review-detail__fields">
        {selection.resourceType === 'story' && (
          <>
            <label>标题<input disabled={!isPending || saving} value={draft.title} onChange={(event) => update('title', event.target.value)} /></label>
            <label>类型<select disabled={!isPending || saving} value={draft.type} onChange={(event) => update('type', event.target.value)}><option value="short">短剧</option><option value="long">长篇</option><option value="script">剧本</option><option value="outline">大纲</option></select></label>
            <label>创作说明<textarea disabled={!isPending || saving} rows={3} value={draft.description} onChange={(event) => update('description', event.target.value)} /></label>
            <label>正文<textarea disabled={!isPending || saving} rows={9} value={draft.content} onChange={(event) => update('content', event.target.value)} /></label>
          </>
        )}
        {selection.resourceType === 'character' && (
          <>
            <label>角色名<input disabled={!isPending || saving} value={draft.name} onChange={(event) => update('name', event.target.value)} /></label>
            <label>身份<textarea disabled={!isPending || saving} rows={2} value={draft.identity} onChange={(event) => update('identity', event.target.value)} /></label>
            <label>性格<textarea disabled={!isPending || saving} rows={3} value={draft.personality} onChange={(event) => update('personality', event.target.value)} /></label>
            <label>背景<textarea disabled={!isPending || saving} rows={4} value={draft.background} onChange={(event) => update('background', event.target.value)} /></label>
            <label>口头禅<input disabled={!isPending || saving} value={draft.catchphrase} onChange={(event) => update('catchphrase', event.target.value)} /></label>
            <label>标签<input disabled={!isPending || saving} value={draft.tags} onChange={(event) => update('tags', event.target.value)} /></label>
          </>
        )}
        {selection.resourceType === 'scene' && (
          <>
            <label>场景名<input disabled={!isPending || saving} value={draft.name} onChange={(event) => update('name', event.target.value)} /></label>
            <label>顺序<input disabled={!isPending || saving} min={0} type="number" value={draft.order_index} onChange={(event) => update('order_index', event.target.value)} /></label>
            <label>场景描述<textarea disabled={!isPending || saving} rows={7} value={draft.description} onChange={(event) => update('description', event.target.value)} /></label>
          </>
        )}
      </div>

      {storyDetail && ((storyDetail.characters?.length ?? 0) > 0 || (storyDetail.scenes?.length ?? 0) > 0) && (
        <section className="story-workspace-review-detail__bundle" aria-label="提案结构">
          <header><h4>提案结构</h4><p>确认故事会一并批准当前关联的角色与场景，并进入发布执行。</p></header>
          {storyDetail.characters?.map((character) => (
            <button
              key={character.id}
              onClick={() => onSelectResource?.({ resourceType: 'character', resourceId: character.id })}
              type="button"
            >
              <span>角色</span><strong>{character.name}</strong><small>{character.review_status === 'pending' ? '待审阅' : character.review_status}</small>
            </button>
          ))}
          {storyDetail.scenes?.map((scene) => (
            <button
              key={scene.id}
              onClick={() => onSelectResource?.({ resourceType: 'scene', resourceId: scene.id })}
              type="button"
            >
              <span>场景 {scene.order_index + 1}</span><strong>{scene.name}</strong><small>{scene.review_status === 'pending' ? '待审阅' : scene.review_status}</small>
            </button>
          ))}
        </section>
      )}

      {isPending && (
        <section className="story-workspace-review-detail__decision" aria-label="审阅决定">
          <label>驳回说明<textarea disabled={saving} placeholder="指出需要 Agent 修改的内容" rows={3} value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} /></label>
          {error && <p role="alert">{error}</p>}
          <div>
            <button className="workflow-button" disabled={saving} onClick={() => void runAction('reject')} type="button">驳回并保留意见</button>
            <button className="workflow-button" disabled={saving} onClick={() => void runAction('save')} type="button">保存修改</button>
            <button className="workflow-button workflow-button--primary" disabled={saving} onClick={() => void runAction('confirm')} type="button">
              {selection.resourceType === 'story' ? '确认提案并执行发布' : '保存并确认'}
            </button>
          </div>
        </section>
      )}
      {!isPending && error && <p role="alert" className="story-workspace-review-detail__error">{error}</p>}
    </article>
  );
}
