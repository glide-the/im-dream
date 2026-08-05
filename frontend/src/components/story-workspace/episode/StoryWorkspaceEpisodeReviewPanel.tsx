/* eslint-disable react-refresh/only-export-components -- The panel exports its pure target-location seam for deterministic callers. */
// [Input] One parsed Review Report, its artifact availability and explicit target selection.
// [Output] Read-only Review facts plus safe navigation for linked opaque target identities.
// [Pos] Story Workspace Episode auxiliary Review layer; never owns narrative content or workflow state.

import { createElement as h, type ReactNode } from 'react';

import type {
  StoryWorkspaceEpisodeArtifactAvailability,
  StoryWorkspaceEpisodeArtifactSection,
  StoryWorkspaceEpisodeReviewReport,
  StoryWorkspaceEpisodeReviewScope,
  StoryWorkspaceEpisodeReviewTarget,
} from '../../../hooks/story-workspace/contracts';

export type StoryWorkspaceEpisodeReviewLocateSelection =
  | { readonly kind: 'narrative-beat'; readonly id: string }
  | { readonly kind: 'scene'; readonly id: string }
  | { readonly kind: 'shot'; readonly id: string };

export interface StoryWorkspaceEpisodeReviewPanelProps {
  readonly review: StoryWorkspaceEpisodeReviewReport | null;
  readonly availability: StoryWorkspaceEpisodeArtifactAvailability;
  readonly currentTargetSelection?: StoryWorkspaceEpisodeReviewLocateSelection | null;
  readonly onLocateTarget: (
    selection: StoryWorkspaceEpisodeReviewLocateSelection,
  ) => void;
}

const LOGICAL_ARTIFACT_LABELS: Readonly<Record<string, string>> = {
  'episode-outline.md': 'Episode Outline',
  'script.md': 'Script',
  'storyboard.yaml': 'Storyboard',
  'prompts/': 'Prompts',
  'renders/': 'Render Guide',
  'review-report.md': 'Review Report',
};

function logicalArtifactLabel(value: string): string {
  return LOGICAL_ARTIFACT_LABELS[value] ?? '未识别的受审产物';
}

function scopeLabel(scope: StoryWorkspaceEpisodeReviewScope): string {
  if (scope === 'script') return '剧本（script）';
  if (scope === 'full-chain') return '全链路（full-chain）';
  return '范围未声明（unknown）';
}

function reportUnavailableMessage(
  availability: StoryWorkspaceEpisodeArtifactAvailability,
): string {
  if (availability === 'not_generated') return '审阅报告尚未生成';
  if (availability === 'invalid') return '审阅报告来源无效，暂无法读取';
  if (availability === 'unavailable') return '审阅报告来源当前不可用';
  return '审阅报告内容尚未形成';
}

function targetSelection(
  target: StoryWorkspaceEpisodeReviewTarget,
): StoryWorkspaceEpisodeReviewLocateSelection | null {
  if (target.associationStatus !== 'linked' || target.targetViewId === null) {
    return null;
  }
  if (target.kind === 'narrative-beat') {
    return { kind: 'narrative-beat', id: target.targetViewId };
  }
  if (target.kind === 'script-scene') {
    return { kind: 'scene', id: target.targetViewId };
  }
  return { kind: 'shot', id: target.targetViewId };
}

export function storyWorkspaceLocateEpisodeReviewTarget(
  target: StoryWorkspaceEpisodeReviewTarget,
  onLocateTarget: (
    selection: StoryWorkspaceEpisodeReviewLocateSelection,
  ) => void,
): boolean {
  const selection = targetSelection(target);
  if (selection === null) return false;
  onLocateTarget(selection);
  return true;
}

function isCurrentTarget(
  selection: StoryWorkspaceEpisodeReviewLocateSelection,
  current: StoryWorkspaceEpisodeReviewLocateSelection | null | undefined,
): boolean {
  return current?.kind === selection.kind && current.id === selection.id;
}

function targetKindLabel(kind: StoryWorkspaceEpisodeReviewTarget['kind']): string {
  if (kind === 'narrative-beat') return '叙事点';
  if (kind === 'script-scene') return '场景';
  return '镜头';
}

function ReviewSection({
  section,
}: {
  readonly section: StoryWorkspaceEpisodeArtifactSection;
}) {
  return h(
    'section',
    { 'aria-label': '审阅章节' },
    h('h3', null, section.title),
    h('p', null, section.text),
    h(
      'footer',
      { 'aria-label': '章节来源信息' },
      `来源：Review Report · Revision：${section.sourceRevision}`,
    ),
  );
}

function LinkedTargets({
  targets,
  current,
  onLocateTarget,
}: {
  readonly targets: readonly StoryWorkspaceEpisodeReviewTarget[];
  readonly current: StoryWorkspaceEpisodeReviewLocateSelection | null | undefined;
  readonly onLocateTarget: StoryWorkspaceEpisodeReviewPanelProps['onLocateTarget'];
}) {
  if (targets.length === 0) return null;
  return h(
    'section',
    { 'aria-label': '已关联审阅定位' },
    h('h3', null, '已关联定位'),
    h(
      'ul',
      null,
      targets.map((target) => {
        const selection = targetSelection(target);
        if (selection === null) return null;
        const label = `${targetKindLabel(target.kind)}：${target.sourceKey}`;
        return h(
          'li',
          { key: target.id },
          h(
            'button',
            {
              type: 'button',
              'aria-current': isCurrentTarget(selection, current) ? 'true' : undefined,
              onClick: () => storyWorkspaceLocateEpisodeReviewTarget(
                target,
                onLocateTarget,
              ),
            },
            `定位${label}`,
          ),
        );
      }),
    ),
  );
}

function DiagnosticTargets({
  title,
  explanation,
  targets,
}: {
  readonly title: '尚未关联' | '孤立引用';
  readonly explanation: string;
  readonly targets: readonly StoryWorkspaceEpisodeReviewTarget[];
}) {
  if (targets.length === 0) return null;
  return h(
    'section',
    { 'aria-label': `${title}审阅引用` },
    h('h3', null, title),
    h('p', null, explanation),
    h(
      'ul',
      null,
      targets.map((target) => h(
        'li',
        { key: target.id },
        `${targetKindLabel(target.kind)}：${target.sourceKey}`,
      )),
    ),
  );
}

function ReviewedArtifacts({
  values,
}: {
  readonly values: readonly string[];
}) {
  return h(
    'section',
    { 'aria-label': '受审产物' },
    h('h3', null, '受审产物'),
    values.length === 0
      ? h('p', null, '尚未声明')
      : h(
          'ul',
          null,
          values.map((value) => h(
            'li',
            { key: value },
            logicalArtifactLabel(value),
          )),
        ),
  );
}

function ReviewedRevisions({
  review,
}: {
  readonly review: StoryWorkspaceEpisodeReviewReport;
}) {
  return h(
    'section',
    { 'aria-label': '受审来源 revisions' },
    h('h3', null, '受审来源 Revisions'),
    review.sourceRevisions.length === 0
      ? h('p', null, '尚未声明')
      : h(
          'ul',
          null,
          review.sourceRevisions.map((item) => h(
            'li',
            { key: `${item.sourceArtifact}:${item.sourceRevision}` },
            `${logicalArtifactLabel(item.sourceArtifact)} · ${item.sourceRevision}`,
          )),
        ),
  );
}

function ReviewContent({
  review,
  currentTargetSelection,
  onLocateTarget,
}: {
  readonly review: StoryWorkspaceEpisodeReviewReport;
  readonly currentTargetSelection: StoryWorkspaceEpisodeReviewLocateSelection | null | undefined;
  readonly onLocateTarget: StoryWorkspaceEpisodeReviewPanelProps['onLocateTarget'];
}) {
  const linked = review.targets.filter(
    (target) => target.associationStatus === 'linked' && target.targetViewId !== null,
  );
  const unlinked = review.targets.filter(
    (target) => target.associationStatus === 'unlinked',
  );
  const orphan = review.targets.filter(
    (target) => target.associationStatus === 'orphan'
      || (target.associationStatus === 'linked' && target.targetViewId === null),
  );
  return h(
    'article',
    { 'aria-label': '只读审阅报告' },
    h('p', null, '只读审阅报告'),
    h(
      'dl',
      null,
      h('div', null, h('dt', null, '审阅范围'), h('dd', null, scopeLabel(review.scope))),
      h(
        'div',
        null,
        h('dt', null, '报告结论'),
        h('dd', null, review.overallVerdict ?? '尚未声明'),
      ),
    ),
    h(ReviewedArtifacts, { values: review.reviewedArtifacts }),
    h(ReviewedRevisions, { review }),
    h(
      'section',
      { 'aria-label': '审阅内容' },
      h('h2', null, '审阅内容'),
      review.sections.length === 0
        ? h('p', null, '审阅章节尚未生成')
        : review.sections.map((section) => h(ReviewSection, {
            key: section.id,
            section,
          })),
    ),
    h(
      'section',
      { 'aria-label': '审阅定位' },
      h('h2', null, '审阅定位'),
      review.targets.length === 0
        ? h('p', null, '尚未声明定位目标')
        : null,
      h(LinkedTargets, {
        targets: linked,
        current: currentTargetSelection,
        onLocateTarget,
      }),
      h(DiagnosticTargets, {
        title: '尚未关联',
        explanation: '没有声明可验证的定位目标，不会猜测故事线位置。',
        targets: unlinked,
      }),
      h(DiagnosticTargets, {
        title: '孤立引用',
        explanation: '声明的定位目标不存在或不一致，不会猜测故事线位置。',
        targets: orphan,
      }),
    ),
    h(
      'footer',
      { 'aria-label': '报告来源信息' },
      `来源：Review Report · Revision：${review.sourceRevision}`,
    ),
  );
}

function ReviewDisclosure({ children }: { readonly children: ReactNode }) {
  return h(
    'details',
    { open: true },
    h('summary', null, 'Review Report'),
    children,
  );
}

export function StoryWorkspaceEpisodeReviewPanel({
  review,
  availability,
  currentTargetSelection = null,
  onLocateTarget,
}: StoryWorkspaceEpisodeReviewPanelProps) {
  const content = review === null || availability !== 'available'
    ? h('p', { role: 'status' }, reportUnavailableMessage(availability))
    : h(ReviewContent, { review, currentTargetSelection, onLocateTarget });
  return h(
    'aside',
    {
      'aria-label': 'Episode Review 辅助视图',
      className: 'story-workspace-episode-review-panel',
    },
    h(ReviewDisclosure, null, content),
  );
}
