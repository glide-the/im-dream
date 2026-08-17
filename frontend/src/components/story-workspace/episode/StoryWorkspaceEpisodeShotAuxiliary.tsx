// [Input] One selected Shot and server-indexed Prompt, guide and Render Queue facts.
// [Output] Independent, accessible Shot auxiliary disclosures with honest provenance.
// [Pos] Story Workspace Shot inspector auxiliary layer; owns no artifact or selection state.

import { createElement as h, type ReactNode } from 'react';

import type {
  StoryWorkspaceEpisodeArtifactAvailability,
  StoryWorkspaceEpisodeArtifactSection,
  StoryWorkspaceEpisodeAssociationCoverage,
  StoryWorkspaceEpisodeAssociationStatus,
  StoryWorkspaceEpisodePrompt,
  StoryWorkspaceEpisodeRenderQueueEntry,
} from '../../../hooks/story-workspace/contracts';
import type { StoryWorkspaceEpisodeShotNode } from '../../../pages/story-workspace/episodeExecutionViewModel';

export interface StoryWorkspaceEpisodeShotAuxiliaryCoverage {
  readonly shotPrompt: StoryWorkspaceEpisodeAssociationCoverage;
  readonly shotRenderQueue: StoryWorkspaceEpisodeAssociationCoverage;
}

export interface StoryWorkspaceEpisodeShotAuxiliarySourceAvailability {
  readonly prompts: StoryWorkspaceEpisodeArtifactAvailability;
  readonly renderGuide: StoryWorkspaceEpisodeArtifactAvailability;
}

export interface StoryWorkspaceEpisodeShotAuxiliaryProps {
  readonly selectedShot: StoryWorkspaceEpisodeShotNode;
  /** Already indexed by the selected opaque Shot view ID. */
  readonly prompts: readonly StoryWorkspaceEpisodePrompt[];
  /** Already indexed independently by the selected opaque Shot view ID. */
  readonly renderQueueEntries: readonly StoryWorkspaceEpisodeRenderQueueEntry[];
  readonly renderGuideSections: readonly StoryWorkspaceEpisodeArtifactSection[];
  readonly associationCoverage: StoryWorkspaceEpisodeShotAuxiliaryCoverage;
  readonly sourceAvailability: StoryWorkspaceEpisodeShotAuxiliarySourceAvailability;
}

function pending(value: string | number | null): string | number {
  return value === null || value === '' ? '尚未生成' : value;
}

function coverageLabel(coverage: StoryWorkspaceEpisodeAssociationCoverage): string {
  if (coverage.total === 0) return '关联覆盖：尚未生成';
  if (coverage.ratio === null) {
    return `关联覆盖：${coverage.linked} / ${coverage.total}（比例尚未生成）`;
  }
  return `关联覆盖：${coverage.linked} / ${coverage.total}（${Math.round(
    coverage.ratio * 100,
  )}%）`;
}

function associationLabel(status: StoryWorkspaceEpisodeAssociationStatus): string {
  if (status === 'linked') return '已关联';
  if (status === 'unlinked') {
    return '尚未关联：没有声明可验证的 Shot 关系';
  }
  return '孤立引用：声明的 Shot 目标不存在或不一致';
}

function sourceAvailabilityMessage(
  kind: 'prompt' | 'render-guide',
  availability: StoryWorkspaceEpisodeArtifactAvailability,
): ReactNode {
  const prompt = kind === 'prompt';
  if (availability === 'available') {
    return prompt
      ? null
      : h('p', null, '已生成制作指导；真实画面不在本期受审合同内');
  }
  if (availability === 'not_generated') {
    return h('p', { role: 'status' }, prompt ? 'Prompt 尚未生成' : '制作指导尚未生成');
  }
  if (availability === 'invalid') {
    return h(
      'p',
      { role: 'status' },
      prompt
        ? 'Prompt 来源无效；当前条目仅用于关系诊断'
        : '制作指导来源无效；当前条目仅用于关系诊断',
    );
  }
  return h(
    'p',
    { role: 'status' },
    prompt ? 'Prompt 来源当前不可用' : '制作指导来源当前不可用',
  );
}

function DefinitionList({
  values,
}: {
  readonly values: ReadonlyArray<readonly [string, string | number | null]>;
}) {
  return h(
    'dl',
    null,
    values.map(([label, value]) => h(
      'div',
      { key: label },
      h('dt', null, label),
      h('dd', null, pending(value)),
    )),
  );
}

function Revision({
  source,
  value,
}: {
  readonly source: 'Prompt' | 'Render Guide';
  readonly value: string;
}) {
  return h(
    'footer',
    { 'aria-label': '来源信息' },
    `来源：${source} · Revision：${value}`,
  );
}

function PromptItem({ prompt }: { readonly prompt: StoryWorkspaceEpisodePrompt }) {
  return h(
    'li',
    { key: prompt.id },
    h(
      'article',
      { 'aria-label': `Prompt ${prompt.kind}` },
      h('h3', null, `Prompt ${prompt.kind}`),
      h('p', null, '不透明 ID：', prompt.id),
      h('p', null, '关系：', associationLabel(prompt.associationStatus)),
      h('section', null, h('h4', null, '正向描述'), h('p', null, pending(prompt.positive))),
      h('section', null, h('h4', null, '负向描述'), h('p', null, pending(prompt.negative))),
      h(
        'section',
        null,
        h('h4', null, '受控参数'),
        h(DefinitionList, {
          values: [
            ['模型', prompt.parameters.model],
            ['模式', prompt.parameters.mode],
            [
              '时长',
              prompt.parameters.durationSec === null
                ? null
                : `${prompt.parameters.durationSec} 秒`,
            ],
            ['动作强度', prompt.parameters.motionStrength],
            ['镜头运动', prompt.parameters.cameraMotion],
            ['画幅', prompt.parameters.aspectRatio],
          ],
        }),
      ),
      h(
        'section',
        null,
        h('h4', null, '可生成性'),
        h(DefinitionList, {
          values: [
            ['角色锚点', prompt.generability.characterAnchor],
            ['动作可行性', prompt.generability.motionFeasibility],
            ['时长预算', prompt.generability.durationBudget],
            ['备注', prompt.generability.notes],
          ],
        }),
      ),
      h(Revision, { source: 'Prompt', value: prompt.sourceRevision }),
    ),
  );
}

function PromptDisclosure({
  prompts,
  coverage,
  availability,
}: {
  readonly prompts: readonly StoryWorkspaceEpisodePrompt[];
  readonly coverage: StoryWorkspaceEpisodeAssociationCoverage;
  readonly availability: StoryWorkspaceEpisodeArtifactAvailability;
}) {
  const empty = prompts.length === 0
    ? availability === 'available'
      ? h('p', { role: 'status' }, '此 Shot 尚未关联 Prompt')
      : null
    : h('ol', null, prompts.map((prompt) => h(PromptItem, { key: prompt.id, prompt })));
  return h(
    'details',
    { open: true },
    h('summary', null, 'Prompt'),
    h('p', null, '关系：Shot → Prompt'),
    h('p', null, coverageLabel(coverage)),
    sourceAvailabilityMessage('prompt', availability),
    empty,
  );
}

function GuideSection({
  section,
}: {
  readonly section: StoryWorkspaceEpisodeArtifactSection;
}) {
  return h(
    'section',
    { 'aria-label': '制作指导章节' },
    h('h3', null, section.title),
    h('p', null, section.text),
    h(Revision, { source: 'Render Guide', value: section.sourceRevision }),
  );
}

function QueueItem({
  entry,
}: {
  readonly entry: StoryWorkspaceEpisodeRenderQueueEntry;
}) {
  return h(
    'li',
    { key: entry.id },
    h(
      'article',
      { 'aria-label': 'Render Queue 条目' },
      h('h3', null, 'Render Queue'),
      h('p', null, '不透明 ID：', entry.id),
      h('p', null, '关系：', associationLabel(entry.associationStatus)),
      h(DefinitionList, {
        values: [
          [
            '时长',
            entry.durationSec === null ? null : `${entry.durationSec} 秒`,
          ],
          ['风险', entry.risk],
          ['优先级', entry.priority],
          ['Renderer', entry.renderer],
          ['状态', entry.status],
        ],
      }),
      h(Revision, { source: 'Render Guide', value: entry.sourceRevision }),
    ),
  );
}

function QueueDiagnostic({
  entries,
  availability,
}: {
  readonly entries: readonly StoryWorkspaceEpisodeRenderQueueEntry[];
  readonly availability: StoryWorkspaceEpisodeArtifactAvailability;
}) {
  if (entries.length === 0) {
    return availability === 'available'
      ? h('p', { role: 'status' }, '此 Shot 尚未关联 Render Queue')
      : null;
  }
  if (entries.length === 1) return h('p', null, '已关联 1 条 Render Queue');
  return h(
    'p',
    { role: 'status' },
    `重复关联：该 Shot 关联 ${entries.length} 条 Render Queue；未自动选择`,
  );
}

function RenderDisclosure({
  entries,
  sections,
  coverage,
  availability,
}: {
  readonly entries: readonly StoryWorkspaceEpisodeRenderQueueEntry[];
  readonly sections: readonly StoryWorkspaceEpisodeArtifactSection[];
  readonly coverage: StoryWorkspaceEpisodeAssociationCoverage;
  readonly availability: StoryWorkspaceEpisodeArtifactAvailability;
}) {
  return h(
    'details',
    { open: true },
    h('summary', null, '制作指导 / Render Queue'),
    h('p', null, '关系：Shot → Render Queue'),
    h('p', null, coverageLabel(coverage)),
    sourceAvailabilityMessage('render-guide', availability),
    sections.length === 0
      ? null
      : h(
          'section',
          { 'aria-label': '制作指导' },
          sections.map((section) => h(GuideSection, { key: section.id, section })),
        ),
    h(QueueDiagnostic, { entries, availability }),
    entries.length === 0
      ? null
      : h('ol', null, entries.map((entry) => h(QueueItem, { key: entry.id, entry }))),
  );
}

export function StoryWorkspaceEpisodeShotAuxiliary({
  selectedShot,
  prompts,
  renderQueueEntries,
  renderGuideSections,
  associationCoverage,
  sourceAvailability,
}: StoryWorkspaceEpisodeShotAuxiliaryProps) {
  return h(
    'aside',
    {
      'aria-label': `镜头 ${selectedShot.shotId} 辅助视图`,
      className: 'story-workspace-episode-shot-auxiliary',
    },
    h(PromptDisclosure, {
      prompts,
      coverage: associationCoverage.shotPrompt,
      availability: sourceAvailability.prompts,
    }),
    h(RenderDisclosure, {
      entries: renderQueueEntries,
      sections: renderGuideSections,
      coverage: associationCoverage.shotRenderQueue,
      availability: sourceAvailability.renderGuide,
    }),
  );
}
