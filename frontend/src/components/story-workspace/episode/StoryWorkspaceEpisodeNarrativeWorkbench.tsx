/* eslint-disable react-refresh/only-export-components -- The controlled tree exports its pure keyboard seam for deterministic callers. */
// [Input] Episode execution view-model plus controlled selection and expansion state.
// [Output] Accessible storyline navigation and progressive Episode/Beat/Scene/Shot reading surface.
// [Pos] Story Workspace Episode narrative workbench; auxiliary artifact detail remains externally owned.

import {
  createElement as h,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react';

import type {
  StoryWorkspaceEpisodeArtifactManifestEntry,
  StoryWorkspaceEpisodeOverview,
} from '../../../hooks/story-workspace/contracts';
import type { StoryWorkspaceEpisodeReadableArtifact } from './StoryWorkspaceEpisodeArtifactReader';
import {
  storyWorkspaceEpisodeNavigationAction,
  storyWorkspaceEpisodeNavigationItems,
  storyWorkspaceEpisodeSelectionKey,
  type StoryWorkspaceEpisodeExecutionViewModel,
  type StoryWorkspaceEpisodeNavigationItem,
  type StoryWorkspaceEpisodeSelection,
} from '../../../pages/story-workspace/episodeExecutionViewModel';

export interface StoryWorkspaceEpisodeNarrativeWorkbenchProps {
  readonly episodeCode: string;
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
  readonly artifactProgress?: readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
  readonly onArtifactRead?: (artifact: StoryWorkspaceEpisodeReadableArtifact) => void;
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

const STORYLINE_SHEET_ID = 'story-workspace-episode-storyline-sheet';
const STORYLINE_NARROW_QUERY = '(max-width: 767px)';

const ARTIFACT_PROGRESS_LABELS: Readonly<Record<string, string>> = {
  'episode-outline.md': '分集大纲',
  'script.md': '剧本',
  'storyboard.yaml': '分镜',
  'prompts/': 'Prompts',
  'renders/': '渲染指引',
  'review-report.md': '审阅报告',
};

const ARTIFACT_PROGRESS_AVAILABILITY = {
  available: '已生成',
  not_generated: '尚未生成',
  invalid: '来源无效',
  unavailable: '当前不可用',
} as const;

const RENDER_GUIDE_PROGRESS_AVAILABILITY = {
  ...ARTIFACT_PROGRESS_AVAILABILITY,
  available: '已准备',
  not_generated: '尚未准备',
} as const;

const ARTIFACT_PROGRESS_READER_TARGETS:
Readonly<Partial<Record<string, StoryWorkspaceEpisodeReadableArtifact>>> = {
  'episode-outline.md': 'episode-outline.md',
  'script.md': 'script.md',
  'storyboard.yaml': 'storyboard.yaml',
  'review-report.md': 'review-report.md',
};

function initialNarrowLayout(): boolean {
  return typeof window !== 'undefined' && window.matchMedia(STORYLINE_NARROW_QUERY).matches;
}

function artifactProgressAvailabilityLabel(
  artifact: StoryWorkspaceEpisodeArtifactManifestEntry,
): string {
  const labels = artifact.relativeKey === 'renders/'
    ? RENDER_GUIDE_PROGRESS_AVAILABILITY
    : ARTIFACT_PROGRESS_AVAILABILITY;
  return labels[artifact.availability];
}

function storylineSheetFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(
    'button:not(:disabled):not([tabindex="-1"]), a[href]:not([tabindex="-1"]), '
      + 'input:not(:disabled):not([tabindex="-1"]), textarea:not(:disabled):not([tabindex="-1"]), '
      + 'select:not(:disabled):not([tabindex="-1"]), [tabindex]:not([tabindex="-1"])',
  )).filter((element) => !element.hidden);
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
  if (key === 'Home' || key === 'End') {
    const boundaryItem = key === 'Home' ? items[0] : items[items.length - 1];
    if (boundaryItem !== undefined) {
      onSelection({ kind: boundaryItem.kind, id: boundaryItem.id });
    }
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

function CharacterBeats({
  values,
}: {
  readonly values: StoryWorkspaceEpisodeOverview['characterBeats'];
}) {
  if (values.length === 0) {
    return h('section', null, h('h3', null, '人物弧光'), h('p', null, '尚未生成'));
  }
  return h(
    'section',
    null,
    h('h3', null, '人物弧光'),
    h(
      'ol',
      null,
      values.map((beat) => h(
        'li',
        { key: beat.id },
        h('h4', null, beat.sourceKey),
        h(
          'dl',
          null,
          h('div', null, h('dt', null, '角色'), h('dd', null, pending(beat.characterId))),
          h('div', null, h('dt', null, '行动'), h('dd', null, pending(beat.action))),
          h('div', null, h('dt', null, '起始状态'), h('dd', null, pending(beat.startState))),
          h('div', null, h('dt', null, '触发'), h('dd', null, pending(beat.trigger))),
          h('div', null, h('dt', null, '选择'), h('dd', null, pending(beat.choice))),
          h('div', null, h('dt', null, '结束状态'), h('dd', null, pending(beat.endState))),
          h('div', null, h('dt', null, '可见证据'), h('dd', null, pending(beat.visibleEvidence))),
        ),
      )),
    ),
  );
}

function navigationLabel(
  item: StoryWorkspaceEpisodeNavigationItem,
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
): string {
  const associationLabel = item.auxiliaryGroup === 'orphan'
    ? '孤立引用'
    : '尚未关联';
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
    return associationLabel;
  }
  if (item.kind === 'prompt') return `Prompt · ${associationLabel}`;
  if (item.kind === 'render-queue') return `Render Queue · ${associationLabel}`;
  if (item.kind === 'review-target') return `Review · ${associationLabel}`;
  return '故事线';
}

function EpisodeOverviewContent({
  episodeCode,
  viewModel,
  overview,
  artifactProgress,
  onArtifactRead,
}: {
  readonly episodeCode: string;
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly overview: StoryWorkspaceEpisodeOverview | null;
  readonly artifactProgress: readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
  readonly onArtifactRead?: (artifact: StoryWorkspaceEpisodeReadableArtifact) => void;
}) {
  const episode = viewModel.episode;
  const hasScenes = Object.keys(viewModel.scenesById).length > 0;
  const hasShots = Object.keys(viewModel.shotsById).length > 0;
  return h(
    'article',
    { 'aria-label': 'Episode Overview' },
    h('p', null, 'Episode Overview'),
    h('h2', null, pending(overview?.title ?? episode?.title)),
    h(
      'ol',
      {
        'aria-label': `${episodeCode} 产物进度`,
        className: 'story-workspace-episode-artifact-progress',
      },
      artifactProgress.map((artifact) => {
        const label = ARTIFACT_PROGRESS_LABELS[artifact.relativeKey] ?? '受控产物';
        const readerTarget = ARTIFACT_PROGRESS_READER_TARGETS[artifact.relativeKey] ?? null;
        return h(
          'li',
          { key: artifact.relativeKey },
          h('strong', null, label),
          h('span', null, artifactProgressAvailabilityLabel(artifact)),
          artifact.availability === 'available'
            && readerTarget !== null
            && onArtifactRead !== undefined
            ? h(
              'button',
              {
                type: 'button',
                'aria-label': `阅读${label}`,
                onClick: () => onArtifactRead(readerTarget),
              },
              '阅读',
            )
            : null,
        );
      }),
    ),
    h('section', null, h('h3', null, '系列'), h('p', null, pending(overview?.series))),
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
    h(CharacterBeats, { values: overview?.characterBeats ?? [] }),
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
    h('section', null, h('h3', null, '情绪基调'), h('p', null, pending(beat.emotionTone))),
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
    h('h2', null, scene.title),
    h('p', null, scene.heading),
    h(TextList, { title: '动作', values: scene.actions }),
    h('section', null, h('h3', null, '对白'), dialogue),
    h(TextList, { title: '镜头提示', values: scene.cameraCues }),
    scene.shotIds.length === 0 ? h('p', { role: 'status' }, '镜头尚未生成') : null,
    h(Provenance, { artifact: scene.sourceArtifact, revision: scene.sourceRevision }),
  );
}

function ShotContent({
  viewModel,
  id,
  onReturnScene,
}: {
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly id: string;
  readonly onReturnScene: (selection: StoryWorkspaceEpisodeSelection) => void;
}) {
  const shot = viewModel.shotsById[id];
  if (shot === undefined) return h('p', { role: 'status' }, '镜头尚未生成');
  const scene = shot.scriptSceneId === null
    ? undefined
    : viewModel.scenesById[shot.scriptSceneId];
  const beat = shot.narrativeBeatId === null
    ? undefined
    : viewModel.narrativeBeatsById[shot.narrativeBeatId];
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
          { key: `${line.speaker}:${line.type}:${line.line}` },
          h('strong', null, line.speaker),
          '：',
          line.line,
          ' · ',
          h('span', null, line.type),
        )),
      );
  const scriptContext = scene === undefined
    ? h('p', { role: 'status' }, '尚未关联剧本场景')
    : h(
        'div',
        null,
        h('h4', null, `${scene.sourceKey} ${scene.title}`),
        h('p', null, scene.heading),
        h(TextList, { title: '场景动作', values: scene.actions }),
        h(
          'section',
          null,
          h('h4', null, '场景对白'),
          scene.dialogue.length === 0
            ? h('p', null, '尚未生成')
            : h(
                'ol',
                null,
                scene.dialogue.map((line) => h(
                  'li',
                  { key: `${line.speaker}:${line.qualifier ?? ''}:${line.text}` },
                  h('strong', null, line.speaker),
                  line.qualifier === null ? null : `（${line.qualifier}）`,
                  '：',
                  line.text,
                )),
              ),
        ),
      );
  const breadcrumb = [
    viewModel.episode?.title ?? 'Episode Overview',
    beat?.sourceKey ?? '叙事点尚未关联',
    scene?.sourceKey ?? '场景尚未关联',
    shot.shotId,
  ].join(' / ');
  return h(
    'article',
    { 'aria-label': 'Shot Detail' },
    h('p', { 'aria-label': '分镜位置' }, breadcrumb),
    scene === undefined
      ? null
      : h(
          'button',
          {
            type: 'button',
            'aria-label': `返回场景：${scene.title}`,
            onClick: () => onReturnScene({ kind: 'scene', id: scene.id }),
          },
          `返回场景：${scene.title}`,
        ),
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
    h('section', null, h('h3', null, '剧本上下文'), scriptContext),
    h(
      'footer',
      { 'aria-label': '来源信息' },
      h(
        'p',
        null,
        '来源：',
        `${scene?.sourceArtifact ?? '尚未生成'} ${scene?.sourceRevision ?? '尚未生成'}`,
        ' · ',
        `${shot.sourceArtifact} ${shot.sourceRevision ?? '尚未生成'}`,
      ),
      h(
        'p',
        null,
        '关联：script_scene_ref → ',
        pending(shot.declaredScriptSceneRef),
        ' · narrative_beat_ref → ',
        pending(shot.declaredNarrativeBeatRef),
        ' · shot_id → ',
        shot.shotId,
      ),
    ),
  );
}

function NarrativeContent({
  episodeCode,
  viewModel,
  selection,
  episodeOverview,
  artifactProgress,
  onArtifactRead,
  onNavigate,
  auxiliaryGroup,
}: {
  readonly episodeCode: string;
  readonly viewModel: StoryWorkspaceEpisodeExecutionViewModel;
  readonly selection: StoryWorkspaceEpisodeSelection;
  readonly episodeOverview: StoryWorkspaceEpisodeOverview | null;
  readonly artifactProgress: readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
  readonly onArtifactRead?: (artifact: StoryWorkspaceEpisodeReadableArtifact) => void;
  readonly onNavigate: (selection: StoryWorkspaceEpisodeSelection) => void;
  readonly auxiliaryGroup: StoryWorkspaceEpisodeNavigationItem['auxiliaryGroup'];
}) {
  if (selection.kind === 'episode' || selection.kind === 'story-arc') {
    return h(EpisodeOverviewContent, {
      viewModel,
      episodeCode,
      overview: episodeOverview,
      artifactProgress,
      onArtifactRead,
    });
  }
  if (selection.kind === 'narrative-beat') {
    return h(BeatContent, { viewModel, id: selection.id });
  }
  if (selection.kind === 'scene') {
    return h(SceneContent, { viewModel, id: selection.id });
  }
  if (selection.kind === 'shot') {
    return h(ShotContent, { viewModel, id: selection.id, onReturnScene: onNavigate });
  }
  const orphan = auxiliaryGroup === 'orphan';
  const associationLabel = orphan ? '孤立引用' : '尚未关联';
  const artifactLabel = selection.kind === 'prompt'
    ? 'Prompt'
    : selection.kind === 'render-queue'
      ? 'Render Queue'
      : selection.kind === 'review-target'
        ? 'Review'
        : null;
  return h(
    'section',
    { 'aria-label': '辅助选择' },
    h(
      'h2',
      null,
      artifactLabel === null ? associationLabel : `${artifactLabel} · ${associationLabel}`,
    ),
    h(
      'p',
      null,
      orphan
        ? '这些产物声明了上游引用，但目标不存在或不一致，暂不并入故事线。'
        : '这些产物没有声明可验证的上游引用，暂不并入故事线。',
    ),
    h(Provenance, { artifact: null, revision: null }),
  );
}

export function StoryWorkspaceEpisodeNarrativeWorkbench({
  episodeCode,
  viewModel,
  selection,
  expandedKeys,
  onSelection,
  onExpanded,
  onEscape,
  episodeOverview = null,
  artifactProgress = [],
  onArtifactRead,
  auxiliarySlot,
  onAuxiliarySelection,
}: StoryWorkspaceEpisodeNarrativeWorkbenchProps) {
  const itemRefs = useRef(new Map<string, HTMLButtonElement>());
  const focusToken = useRef(0);
  const focusIntent = useRef<{ readonly token: number; readonly targetKey: string } | null>(null);
  const storylineTriggerRef = useRef<HTMLButtonElement>(null);
  const storylineSheetRef = useRef<HTMLElement>(null);
  const storylineFocusIntent = useRef<'open' | 'close' | null>(null);
  const [isNarrowLayout, setIsNarrowLayout] = useState(initialNarrowLayout);
  const [storylineOpen, setStorylineOpen] = useState(() => !initialNarrowLayout());
  const items = storyWorkspaceEpisodeNavigationItems(viewModel, expandedKeys);
  const requestedKey = storyWorkspaceEpisodeSelectionKey(selection);
  const activeItem = items.find(
    (item) => storyWorkspaceEpisodeSelectionKey(item) === requestedKey,
  ) ?? items[0];
  const activeSelection: StoryWorkspaceEpisodeSelection | null = activeItem === undefined
    ? null
    : { kind: activeItem.kind, id: activeItem.id };
  const activeKey = activeSelection === null
    ? null
    : storyWorkspaceEpisodeSelectionKey(activeSelection);
  useLayoutEffect(() => {
    const intent = focusIntent.current;
    if (intent === null) return;
    focusIntent.current = null;
    if (
      activeKey === null
      || intent.token !== focusToken.current
      || intent.targetKey !== activeKey
    ) return;
    itemRefs.current.get(intent.targetKey)?.focus();
  }, [activeKey]);
  useLayoutEffect(() => {
    const intent = storylineFocusIntent.current;
    if (intent === 'open' && isNarrowLayout && storylineOpen) {
      storylineFocusIntent.current = null;
      if (activeKey !== null) itemRefs.current.get(activeKey)?.focus();
    } else if (intent === 'close' && isNarrowLayout && !storylineOpen) {
      storylineFocusIntent.current = null;
      storylineTriggerRef.current?.focus();
    }
  }, [activeKey, isNarrowLayout, storylineOpen]);
  useEffect(() => {
    const media = window.matchMedia(STORYLINE_NARROW_QUERY);
    const synchronize = (matches: boolean) => {
      const storylineOwnsFocus = storylineSheetRef.current?.contains(document.activeElement) === true;
      storylineFocusIntent.current = matches && storylineOwnsFocus ? 'close' : null;
      setIsNarrowLayout(matches);
      setStorylineOpen(!matches);
    };
    const onChange = (event: MediaQueryListEvent) => synchronize(event.matches);
    synchronize(media.matches);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);
  if (viewModel.episode === null || activeSelection === null) {
    return h('section', { role: 'status' }, '故事线尚未生成');
  }
  const select = (nextSelection: StoryWorkspaceEpisodeSelection) => {
    storyWorkspaceSelectEpisodeNarrativeItem(
      nextSelection,
      onSelection,
      onAuxiliarySelection,
    );
  };
  const selectAndFocus = (nextSelection: StoryWorkspaceEpisodeSelection) => {
    const targetKey = storyWorkspaceEpisodeSelectionKey(nextSelection);
    if (targetKey === activeKey) {
      focusIntent.current = null;
      select(nextSelection);
      return;
    }
    const token = focusToken.current + 1;
    focusToken.current = token;
    focusIntent.current = { token, targetKey };
    select(nextSelection);
  };
  const handleContentKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== 'Escape') return;
    event.preventDefault();
    event.stopPropagation();
    focusToken.current += 1;
    focusIntent.current = null;
    onEscape(activeSelection);
    itemRefs.current.get(storyWorkspaceEpisodeSelectionKey(activeSelection))?.focus();
  };
  const closeStoryline = () => {
    if (!isNarrowLayout) return;
    storylineFocusIntent.current = 'close';
    setStorylineOpen(false);
  };
  const openStoryline = () => {
    storylineFocusIntent.current = 'open';
    setStorylineOpen(true);
  };
  const handleStorylineSheetKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!isNarrowLayout || !storylineOpen) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      closeStoryline();
      return;
    }
    if (event.key !== 'Tab' || storylineSheetRef.current === null) return;
    const focusable = storylineSheetFocusableElements(storylineSheetRef.current);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (first === undefined || last === undefined) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
  const handleKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    item: StoryWorkspaceEpisodeNavigationItem,
  ) => {
    const handled = storyWorkspaceHandleEpisodeNarrativeKey({
      key: event.key,
      items,
      selection: { kind: item.kind, id: item.id },
      onSelection: selectAndFocus,
      onExpanded,
      onEscape,
    });
    if (handled) event.preventDefault();
  };
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
          ref: (node: HTMLButtonElement | null) => {
            if (node === null) itemRefs.current.delete(itemKey);
            else itemRefs.current.set(itemKey, node);
          },
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
      'button',
      {
        type: 'button',
        className: 'story-workspace-episode-storyline-toggle',
        'aria-controls': STORYLINE_SHEET_ID,
        'aria-expanded': storylineOpen,
        'aria-label': '打开故事线',
        ref: storylineTriggerRef,
        onClick: openStoryline,
      },
      '故事线',
    ),
    h(
      'div',
      { 'aria-label': 'Episode 主工作面' },
      h(
        'aside',
        {
          className: 'story-workspace-episode-storyline-sheet',
          id: STORYLINE_SHEET_ID,
          hidden: isNarrowLayout && !storylineOpen,
          role: isNarrowLayout ? 'dialog' : undefined,
          'aria-modal': isNarrowLayout ? true : undefined,
          'aria-label': isNarrowLayout ? '故事线' : undefined,
          ref: storylineSheetRef,
          onKeyDownCapture: handleStorylineSheetKeyDown,
        },
        h(
          'header',
          { className: 'story-workspace-episode-storyline-sheet__header' },
          h('p', null, '故事线'),
          h(
            'button',
            {
              type: 'button',
              'aria-label': '关闭故事线',
              onClick: closeStoryline,
            },
            '关闭',
          ),
        ),
        h(
          'nav',
          { 'aria-label': '故事线导航' },
          h('ul', { role: 'tree', 'aria-label': 'Episode 故事线' }, treeItems),
        ),
      ),
      h(
        'section',
        { 'aria-label': 'Episode 内容工作面' },
        h(
          'section',
          { 'aria-label': '叙事内容工作面', onKeyDown: handleContentKeyDown },
          h(NarrativeContent, {
            viewModel,
            selection: activeSelection,
            episodeCode,
            episodeOverview,
            artifactProgress,
            onArtifactRead,
            onNavigate: selectAndFocus,
            auxiliaryGroup: activeItem.auxiliaryGroup,
          }),
        ),
        auxiliarySlot === undefined
          ? null
          : h('aside', { 'aria-label': 'Episode 辅助视图' }, auxiliarySlot),
      ),
    ),
  );
}
