/* eslint-disable react-refresh/only-export-components -- The controlled tree exports its pure keyboard seam for deterministic callers. */
// [Input] Episode execution view-model plus controlled selection and expansion state.
// [Output] Accessible storyline navigation and progressive Episode/Beat/Scene/Shot reading surface.
// [Pos] Story Workspace Episode narrative workbench; auxiliary artifact detail remains externally owned.

import {
  createElement as h,
  type KeyboardEvent,
  type ReactNode,
} from 'react';

import type { StoryWorkspaceEpisodeOverview } from '../../../hooks/story-workspace/contracts';
import {
  STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
  STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
  storyWorkspaceEpisodeNavigationAction,
  storyWorkspaceEpisodeNavigationItems,
  storyWorkspaceEpisodeSelectionKey,
  type StoryWorkspaceEpisodeExecutionViewModel,
  type StoryWorkspaceEpisodeNavigationItem,
  type StoryWorkspaceEpisodeSelection,
} from '../../../pages/story-workspace/episodeExecutionViewModel';

export interface StoryWorkspaceEpisodeNarrativeWorkbenchProps {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly selection: StoryWorkspaceEpisodeSelection;
  readonly expandedKeys: ReadonlySet<string>;
  readonly onSelection: (selection: StoryWorkspaceEpisodeSelection) => void;
  readonly onExpanded: (
    selection: StoryWorkspaceEpisodeSelection,
    expanded: boolean,
  ) => void;
  readonly onEscape: (selection: StoryWorkspaceEpisodeSelection) => void;
  readonly episodeOverview?: StoryWorkspaceEpisodeOverview | null;
  readonly auxiliarySlot?: ReactNode;
  readonly onAuxiliarySelection?: (
    selection: StoryWorkspaceEpisodeSelection,
  ) => void;
}

export interface StoryWorkspaceEpisodeNarrativeKeyInput {
  readonly key: string;
  readonly items: readonly StoryWorkspaceEpisodeNavigationItem[];
  readonly selection: StoryWorkspaceEpisodeSelection;
  readonly onSelection: (selection: StoryWorkspaceEpisodeSelection) => void;
  readonly onExpanded: (
    selection: StoryWorkspaceEpisodeSelection,
    expanded: boolean,
  ) => void;
  readonly onEscape: (selection: StoryWorkspaceEpisodeSelection) => void;
}

function isAuxiliarySelection(selection: StoryWorkspaceEpisodeSelection): boolean {
  return selection.kind === 'auxiliary-group'
    || selection.kind === 'prompt'
    || selection.kind === 'render-queue'
    || selection.kind === 'review-target';
}

export function storyWorkspaceSelectEpisodeNarrativeItem(
  selection: StoryWorkspaceEpisodeSelection,
  onSelection: (selection: StoryWorkspaceEpisodeSelection) => void,
  onAuxiliarySelection?: (selection: StoryWorkspaceEpisodeSelection) => void,
): void {
  onSelection(selection);
  if (isAuxiliarySelection(selection)) onAuxiliarySelection?.(selection);
}

export function storyWorkspaceHandleEpisodeNarrativeKey({
  key,
  items,
  selection,
  onSelection,
  onExpanded,
  onEscape,
}: StoryWorkspaceEpisodeNarrativeKeyInput): boolean {
  if (key === 'Escape') {
    onEscape(selection);
    return true;
  }
  if (key === 'Enter' || key === ' ') {
    onSelection(selection);
    return true;
  }
  if (
    key !== 'ArrowUp'
    && key !== 'ArrowDown'
    && key !== 'ArrowLeft'
    && key !== 'ArrowRight'
  ) return false;

  const result = storyWorkspaceEpisodeNavigationAction(items, selection, key);
  if (
    result.action === 'move-sibling'
    || result.action === 'move-parent'
    || result.action === 'move-first-child'
  ) {
    if (result.target !== null) onSelection(result.target);
  } else if (result.action === 'expand' && result.target !== null) {
    onExpanded(result.target, true);
  } else if (result.action === 'collapse' && result.target !== null) {
    onExpanded(result.target, false);
  }
  return true;
}

function pending(value: string | number | null | undefined): string | number {
  return value === null || value === undefined || value === ''
    ? '尚未生成'
    : value;
}

function Provenance({
  artifact,
  revision,
}: {
  readonly artifact: string | null;
  readonly revision: string | null;
}) {
  return h(
    'footer',
    { 'aria-label': '来源信息' },
    h('span', null, '来源：', pending(artifact)),
    ' · ',
    h('span', null, 'Revision：', pending(revision)),
  );
}

function TextList({
  title,
  values,
}: {
  readonly title: string;
  readonly values: readonly string[];
}) {
  return h(
    'section',
    null,
    h('h3', null, title),
    values.length === 0
      ? h('p', null, '尚未生成')
      : h('ul', null, values.map((value) => h('li', { key: value }, value))),
  );
}

function navigationLabel(
  item: StoryWorkspaceEpisodeNavigationItem,
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
): string {
  if (item.kind === 'episode') {
    return viewModel.episode?.title ?? 'Episode Overview';
  }
  if (item.kind === 'narrative-beat') {
    const beat = viewModel.narrativeBeatsById[item.id];
    return beat === undefined ? '叙事点尚未生成' : `${beat.sourceKey} ${beat.title}`;
  }
  if (item.kind === 'scene') {
    const scene = viewModel.scenesById[item.id];
    return scene === undefined ? '场景尚未生成' : `${scene.sourceKey} ${scene.title}`;
  }
  if (item.kind === 'shot') {
    return viewModel.shotsById[item.id]?.shotId ?? '镜头尚未生成';
  }
  if (item.kind === 'auxiliary-group') {
    return item.id === STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID
      ? '尚未关联'
      : '孤立引用';
  }
  if (item.kind === 'prompt') return 'Prompt · 尚未关联';
  if (item.kind === 'render-queue') return 'Render Queue · 尚未关联';
  if (item.kind === 'review-target') return 'Review · 尚未关联';
  return '故事线';
}

function EpisodeOverviewContent({
  viewModel,
  overview,
}: {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly overview: StoryWorkspaceEpisodeOverview | null;
}) {
  const episode = viewModel.episode;
  const hasScenes = Object.keys(viewModel.scenesById).length > 0;
  const hasShots = Object.keys(viewModel.shotsById).length > 0;
  return h(
    'article',
    { 'aria-label': 'Episode Overview' },
    h('p', null, 'Episode Overview'),
    h('h2', null, pending(overview?.title ?? episode?.title)),
    h(TextList, { title: '故事目标', values: overview?.storyGoals ?? [] }),
    h(
      'section',
      null,
      h('h3', null, '核心冲突'),
      h('p', null, pending(overview?.coreConflict)),
    ),
    h(
      'section',
      null,
      h('h3', null, 'Hook'),
      h('p', null, pending(overview?.hook)),
    ),
    hasScenes ? null : h('p', { role: 'status' }, '场景尚未生成'),
    hasShots ? null : h('p', { role: 'status' }, '镜头尚未生成'),
    h(Provenance, {
      artifact: overview?.sourceArtifact ?? episode?.sourceArtifact ?? null,
      revision: overview?.sourceRevision ?? episode?.sourceRevision ?? null,
    }),
  );
}

function BeatContent({
  viewModel,
  id,
}: {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly id: string;
}) {
  const beat = viewModel.narrativeBeatsById[id];
  if (beat === undefined) return h('p', { role: 'status' }, '叙事点尚未生成');
  return h(
    'article',
    { 'aria-label': 'Narrative Beat' },
    h('p', null, beat.sourceKey),
    h('h2', null, beat.title),
    h('section', null, h('h3', null, '叙事功能'), h('p', null, pending(beat.narrativeFunction))),
    h('section', null, h('h3', null, '摘要'), h('p', null, pending(beat.summary))),
    h(TextList, { title: '场景目标', values: beat.sceneGoals }),
    h(TextList, { title: '对白节拍', values: beat.keyDialogueBeats }),
    beat.sceneIds.length === 0 ? h('p', { role: 'status' }, '场景尚未生成') : null,
    h(Provenance, { artifact: beat.sourceArtifact, revision: beat.sourceRevision }),
  );
}

function SceneContent({
  viewModel,
  id,
}: {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly id: string;
}) {
  const scene = viewModel.scenesById[id];
  if (scene === undefined) return h('p', { role: 'status' }, '场景尚未生成');
  const dialogue = scene.dialogue.length === 0
    ? h('p', null, '尚未生成')
    : h(
        'ol',
        null,
        scene.dialogue.map((line) => h(
          'li',
          { key: `${line.speaker}:${line.text}` },
          h('strong', null, line.speaker),
          line.qualifier === null ? null : `（${line.qualifier}）`,
          '：',
          line.text,
        )),
      );
  return h(
    'article',
    { 'aria-label': 'Script Scene' },
    h('p', null, scene.sourceKey),
    h('h2', null, scene.heading),
    h(TextList, { title: '动作', values: scene.actions }),
    h('section', null, h('h3', null, '对白'), dialogue),
    scene.shotIds.length === 0 ? h('p', { role: 'status' }, '镜头尚未生成') : null,
    h(Provenance, { artifact: scene.sourceArtifact, revision: scene.sourceRevision }),
  );
}

function ShotContent({
  viewModel,
  id,
}: {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly id: string;
}) {
  const shot = viewModel.shotsById[id];
  if (shot === undefined) return h('p', { role: 'status' }, '镜头尚未生成');
  const definition = (title: string, value: string | number | null) => h(
    'div',
    { key: title },
    h('dt', null, title),
    h('dd', null, pending(value)),
  );
  const characters = shot.characters.length === 0
    ? h('p', null, '尚未生成')
    : h(
        'ul',
        null,
        shot.characters.map((character) => h(
          'li',
          { key: character.ref },
          character.displayName ?? character.ref,
          ' · ',
          pending(character.depthPlane),
          ' · ',
          pending(character.action),
          ' · ',
          pending(character.emotion),
        )),
      );
  const dialogue = shot.dialogue.length === 0
    ? h('p', null, '尚未生成')
    : h(
        'ol',
        null,
        shot.dialogue.map((line) => h(
          'li',
          { key: `${line.speaker}:${line.line}` },
          h('strong', null, line.speaker),
          '：',
          line.line,
        )),
      );
  return h(
    'article',
    { 'aria-label': 'Shot Detail' },
    h('p', null, '详细分镜'),
    h('h2', null, shot.shotId),
    h('section', null, h('h3', null, '镜头意图'), h('p', null, pending(shot.visual))),
    h(
      'dl',
      null,
      definition('景别', shot.shotType),
      definition('角度', shot.camera.angle),
      definition('高度', shot.camera.height),
      definition('运动', shot.camera.movement),
      definition('镜头', shot.camera.lens),
      definition(
        '时长',
        shot.timing.durationSec === null ? null : `${shot.timing.durationSec} 秒`,
      ),
      definition('入场转场', shot.timing.transitionIn),
      definition('出场转场', shot.timing.transitionOut),
    ),
    h('section', null, h('h3', null, '角色'), characters),
    h('section', null, h('h3', null, '对白'), dialogue),
    h(Provenance, { artifact: shot.sourceArtifact, revision: shot.sourceRevision }),
  );
}

function NarrativeContent({
  viewModel,
  selection,
  episodeOverview,
}: {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly selection: StoryWorkspaceEpisodeSelection;
  readonly episodeOverview: StoryWorkspaceEpisodeOverview | null;
}) {
  if (selection.kind === 'episode' || selection.kind === 'story-arc') {
    return h(EpisodeOverviewContent, { viewModel, overview: episodeOverview });
  }
  if (selection.kind === 'narrative-beat') {
    return h(BeatContent, { viewModel, id: selection.id });
  }
  if (selection.kind === 'scene') {
    return h(SceneContent, { viewModel, id: selection.id });
  }
  if (selection.kind === 'shot') {
    return h(ShotContent, { viewModel, id: selection.id });
  }
  return h(
    'section',
    { 'aria-label': '辅助选择' },
    h(
      'h2',
      null,
      selection.id === STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID
        ? '孤立引用'
        : '尚未关联',
    ),
    h('p', null, '辅助内容请在右侧视图中查看。'),
    h(Provenance, { artifact: null, revision: null }),
  );
}

export function StoryWorkspaceEpisodeNarrativeWorkbench({
  viewModel,
  selection,
  expandedKeys,
  onSelection,
  onExpanded,
  onEscape,
  episodeOverview = null,
  auxiliarySlot,
  onAuxiliarySelection,
}: StoryWorkspaceEpisodeNarrativeWorkbenchProps) {
  const items = storyWorkspaceEpisodeNavigationItems(viewModel, expandedKeys);
  if (viewModel.episode === null || items.length === 0) {
    return h('section', { role: 'status' }, '故事线尚未生成');
  }
  const requestedKey = storyWorkspaceEpisodeSelectionKey(selection);
  const activeItem = items.find(
    (item) => storyWorkspaceEpisodeSelectionKey(item) === requestedKey,
  ) ?? items[0];
  const activeSelection: StoryWorkspaceEpisodeSelection = {
    kind: activeItem.kind,
    id: activeItem.id,
  };
  const select = (nextSelection: StoryWorkspaceEpisodeSelection) => {
    storyWorkspaceSelectEpisodeNarrativeItem(
      nextSelection,
      onSelection,
      onAuxiliarySelection,
    );
  };
  const handleKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    item: StoryWorkspaceEpisodeNavigationItem,
  ) => {
    const handled = storyWorkspaceHandleEpisodeNarrativeKey({
      key: event.key,
      items,
      selection: { kind: item.kind, id: item.id },
      onSelection: select,
      onExpanded,
      onEscape,
    });
    if (handled) event.preventDefault();
  };
  const activeKey = storyWorkspaceEpisodeSelectionKey(activeSelection);
  const treeItems = items.map((item) => {
    const itemSelection: StoryWorkspaceEpisodeSelection = {
      kind: item.kind,
      id: item.id,
    };
    const itemKey = storyWorkspaceEpisodeSelectionKey(itemSelection);
    const active = itemKey === activeKey;
    return h(
      'li',
      { key: itemKey, role: 'none' },
      h(
        'button',
        {
          type: 'button',
          role: 'treeitem',
          'aria-level': item.level,
          'aria-current': active ? 'true' : undefined,
          'aria-selected': active,
          'aria-expanded': item.children.length > 0 ? item.expanded : undefined,
          tabIndex: active ? 0 : -1,
          onClick: () => select(itemSelection),
          onKeyDown: (event: KeyboardEvent<HTMLButtonElement>) => handleKeyDown(event, item),
        },
        navigationLabel(item, viewModel),
      ),
    );
  });

  return h(
    'section',
    { 'aria-label': 'Episode 叙事工作台' },
    h(
      'nav',
      { 'aria-label': '故事线导航' },
      h('ul', { role: 'tree', 'aria-label': 'Episode 故事线' }, treeItems),
    ),
    h(
      'section',
      { 'aria-label': '叙事内容工作面' },
      h(NarrativeContent, { viewModel, selection, episodeOverview }),
    ),
    auxiliarySlot === undefined
      ? null
      : h('aside', { 'aria-label': 'Episode 辅助视图' }, auxiliarySlot),
  );
}
