// [Input] Strict Episode artifact surface parsed at the browser contract boundary.
// [Output] Pure storyline hierarchy, detached artifacts, contextual indexes and navigation facts.
// [Pos] Story Workspace Episode execution projection; contains no React or browser persistence state.

import type {
  StoryWorkspaceEpisodeAssociationCoverage,
  StoryWorkspaceEpisodeArtifactSurface,
  StoryWorkspaceEpisodeNarrativeBeat,
  StoryWorkspaceEpisodePrompt,
  StoryWorkspaceEpisodeRenderQueueEntry,
  StoryWorkspaceEpisodeReviewTarget,
  StoryWorkspaceEpisodeScriptScene,
  StoryWorkspaceEpisodeStoryboardShot,
} from '../../hooks/story-workspace/contracts';

export type StoryWorkspaceEpisodeSourceAvailability = 'available' | 'unavailable';

interface StoryWorkspaceEpisodeSourceFact {
  readonly sourceArtifact: string | null;
  readonly sourceRevision: string | null;
  readonly sourceAvailability: StoryWorkspaceEpisodeSourceAvailability;
}

export interface StoryWorkspaceEpisodeNode extends StoryWorkspaceEpisodeSourceFact {
  readonly kind: 'episode';
  readonly id: string;
  readonly title: string | null;
  readonly storyArcId: string;
}

export interface StoryWorkspaceEpisodeStoryArcNode extends StoryWorkspaceEpisodeSourceFact {
  readonly kind: 'story-arc';
  readonly id: string;
  readonly episodeId: string;
  readonly narrativeBeatIds: readonly string[];
}

export interface StoryWorkspaceEpisodeNarrativeBeatNode
  extends StoryWorkspaceEpisodeNarrativeBeat {
  readonly kind: 'narrative-beat';
  readonly sceneIds: readonly string[];
  readonly shotIds: readonly string[];
  readonly sourceAvailability: StoryWorkspaceEpisodeSourceAvailability;
}

export interface StoryWorkspaceEpisodeSceneNode extends StoryWorkspaceEpisodeScriptScene {
  readonly kind: 'scene';
  readonly shotIds: readonly string[];
  readonly sourceAvailability: StoryWorkspaceEpisodeSourceAvailability;
}

export interface StoryWorkspaceEpisodeShotNode extends StoryWorkspaceEpisodeStoryboardShot {
  readonly kind: 'shot';
  readonly sourceAvailability: StoryWorkspaceEpisodeSourceAvailability;
}

export interface StoryWorkspaceEpisodeDetachedArtifacts {
  readonly scenes: readonly StoryWorkspaceEpisodeSceneNode[];
  readonly shots: readonly StoryWorkspaceEpisodeShotNode[];
  readonly prompts: readonly StoryWorkspaceEpisodePrompt[];
  readonly renderQueueEntries: readonly StoryWorkspaceEpisodeRenderQueueEntry[];
  readonly reviewTargets: readonly StoryWorkspaceEpisodeReviewTarget[];
}

export interface StoryWorkspaceEpisodeCoverageView {
  readonly availability: StoryWorkspaceEpisodeAssociationCoverage['availability'];
  readonly linked: number;
  readonly total: number;
  readonly ratio: number | null;
  readonly label: string;
}

export interface StoryWorkspaceEpisodeExecutionCoverage {
  readonly beatScene: StoryWorkspaceEpisodeCoverageView;
  readonly sceneShot: StoryWorkspaceEpisodeCoverageView;
  readonly shotPrompt: StoryWorkspaceEpisodeCoverageView;
  readonly shotRenderQueue: StoryWorkspaceEpisodeCoverageView;
}

export interface StoryWorkspaceEpisodeExecutionViewModel {
  readonly episode: StoryWorkspaceEpisodeNode | null;
  readonly storyArc: StoryWorkspaceEpisodeStoryArcNode | null;
  readonly narrativeBeatsById: Readonly<Record<string, StoryWorkspaceEpisodeNarrativeBeatNode>>;
  readonly scenesById: Readonly<Record<string, StoryWorkspaceEpisodeSceneNode>>;
  readonly shotsById: Readonly<Record<string, StoryWorkspaceEpisodeShotNode>>;
  readonly promptsByShotViewId: Readonly<Record<string, readonly StoryWorkspaceEpisodePrompt[]>>;
  readonly renderQueueByShotViewId: Readonly<
    Record<string, readonly StoryWorkspaceEpisodeRenderQueueEntry[]>
  >;
  readonly reviewTargetsByTargetViewId: Readonly<
    Record<string, readonly StoryWorkspaceEpisodeReviewTarget[]>
  >;
  readonly unlinked: StoryWorkspaceEpisodeDetachedArtifacts;
  readonly orphans: StoryWorkspaceEpisodeDetachedArtifacts;
  readonly coverage: StoryWorkspaceEpisodeExecutionCoverage;
}

export const STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID =
  'story-workspace-episode-unlinked';
export const STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID =
  'story-workspace-episode-orphans';

export type StoryWorkspaceEpisodeSelectionKind =
  | 'episode'
  | 'story-arc'
  | 'narrative-beat'
  | 'scene'
  | 'shot'
  | 'prompt'
  | 'render-queue'
  | 'review-target'
  | 'auxiliary-group';

export interface StoryWorkspaceEpisodeSelection {
  readonly kind: StoryWorkspaceEpisodeSelectionKind;
  readonly id: string;
}

export interface StoryWorkspaceEpisodeNavigationItem
  extends StoryWorkspaceEpisodeSourceFact {
  readonly id: string;
  readonly kind: StoryWorkspaceEpisodeSelectionKind;
  readonly level: 1 | 2 | 3 | 4;
  readonly canonicalParent: StoryWorkspaceEpisodeSelection | null;
  readonly navigationParent: StoryWorkspaceEpisodeSelection | null;
  readonly auxiliaryGroup: 'unlinked' | 'orphan' | null;
  readonly children: readonly StoryWorkspaceEpisodeSelection[];
  readonly expanded: boolean;
}

export interface StoryWorkspaceEpisodeNavigationNeighbors {
  readonly previousSibling: StoryWorkspaceEpisodeSelection | null;
  readonly nextSibling: StoryWorkspaceEpisodeSelection | null;
  readonly parent: StoryWorkspaceEpisodeSelection | null;
  readonly firstChild: StoryWorkspaceEpisodeSelection | null;
}

export type StoryWorkspaceEpisodeNavigationKey =
  | 'ArrowUp'
  | 'ArrowDown'
  | 'ArrowLeft'
  | 'ArrowRight';

export type StoryWorkspaceEpisodeNavigationActionKind =
  | 'move-sibling'
  | 'expand'
  | 'collapse'
  | 'move-parent'
  | 'move-first-child'
  | 'noop';

export interface StoryWorkspaceEpisodeNavigationAction {
  readonly action: StoryWorkspaceEpisodeNavigationActionKind;
  readonly target: StoryWorkspaceEpisodeSelection | null;
}

const unavailableCoverage: StoryWorkspaceEpisodeAssociationCoverage = {
  availability: 'unavailable',
  linked: 0,
  total: 0,
  ratio: null,
};

function sourceAvailability(
  artifact: string | null,
  revision: string | null,
): StoryWorkspaceEpisodeSourceAvailability {
  return artifact !== null && revision !== null ? 'available' : 'unavailable';
}

function recordById<T extends { readonly id: string }>(
  values: readonly T[],
  label: string,
): Record<string, T> {
  const entries: Array<readonly [string, T]> = [];
  const ids = new Set<string>();
  for (const value of values) {
    if (ids.has(value.id)) {
      throw new Error(`${label} contains duplicate opaque id.`);
    }
    ids.add(value.id);
    entries.push([value.id, value]);
  }
  return Object.fromEntries(entries);
}

function appendIndexed<T>(
  target: Record<string, T[]>,
  id: string,
  value: T,
): void {
  const values = target[id];
  if (values === undefined) {
    target[id] = [value];
    return;
  }
  values.push(value);
}

function coverageView(
  coverage: StoryWorkspaceEpisodeAssociationCoverage,
): StoryWorkspaceEpisodeCoverageView {
  return {
    ...coverage,
    label: storyWorkspaceEpisodeCoverageLabel(coverage),
  };
}

export function storyWorkspaceEpisodeCoverageLabel(
  coverage: StoryWorkspaceEpisodeAssociationCoverage,
): string {
  if (coverage.total === 0 || coverage.availability === 'unavailable') {
    return '尚未生成';
  }
  return `${Math.round((coverage.linked / coverage.total) * 100)}%`;
}

export function storyWorkspaceBuildEpisodeExecutionViewModel(
  surface: StoryWorkspaceEpisodeArtifactSurface,
): StoryWorkspaceEpisodeExecutionViewModel {
  const narrative = surface.narrative;
  const beats = (narrative?.narrativeBeats ?? []).map(
    (beat): StoryWorkspaceEpisodeNarrativeBeatNode => ({
      ...beat,
      kind: 'narrative-beat',
      sceneIds: [],
      shotIds: [],
      sourceAvailability: sourceAvailability(beat.sourceArtifact, beat.sourceRevision),
    }),
  );
  const baseScenes = (narrative?.scenes ?? []).map(
    (scene): StoryWorkspaceEpisodeSceneNode => ({
      ...scene,
      kind: 'scene',
      shotIds: [],
      sourceAvailability: sourceAvailability(scene.sourceArtifact, scene.sourceRevision),
    }),
  );
  const shots = (narrative?.shots ?? []).map(
    (shot): StoryWorkspaceEpisodeShotNode => ({
      ...shot,
      kind: 'shot',
      sourceAvailability: sourceAvailability(shot.sourceArtifact, shot.sourceRevision),
    }),
  );

  const baseBeatsById = recordById(beats, 'narrative beats');
  const baseScenesById = recordById(baseScenes, 'script scenes');
  const shotsById = recordById(shots, 'storyboard shots');
  const sceneIdsByBeatId: Record<string, string[]> = {};
  const shotIdsBySceneId: Record<string, string[]> = {};
  const shotIdsByBeatId: Record<string, string[]> = {};
  const unlinkedScenes: StoryWorkspaceEpisodeSceneNode[] = [];
  const orphanScenes: StoryWorkspaceEpisodeSceneNode[] = [];
  const unlinkedShots: StoryWorkspaceEpisodeShotNode[] = [];
  const orphanShots: StoryWorkspaceEpisodeShotNode[] = [];

  for (const scene of baseScenes) {
    if (scene.associationStatus === 'unlinked') {
      unlinkedScenes.push(scene);
      continue;
    }
    if (
      scene.associationStatus !== 'linked'
      || scene.narrativeBeatId === null
      || baseBeatsById[scene.narrativeBeatId] === undefined
    ) {
      orphanScenes.push(scene);
      continue;
    }
    appendIndexed(sceneIdsByBeatId, scene.narrativeBeatId, scene.id);
  }

  for (const shot of shots) {
    if (shot.associationStatus === 'unlinked') {
      unlinkedShots.push(shot);
      continue;
    }
    const scene = shot.scriptSceneId === null
      ? undefined
      : baseScenesById[shot.scriptSceneId];
    if (
      shot.associationStatus !== 'linked'
      || scene === undefined
      || shot.narrativeBeatId !== scene.narrativeBeatId
    ) {
      orphanShots.push(shot);
      continue;
    }
    appendIndexed(shotIdsBySceneId, scene.id, shot.id);
    if (
      scene.associationStatus === 'linked'
      && scene.narrativeBeatId !== null
      && baseBeatsById[scene.narrativeBeatId] !== undefined
    ) {
      appendIndexed(shotIdsByBeatId, scene.narrativeBeatId, shot.id);
    }
  }

  const scenes = baseScenes.map((scene): StoryWorkspaceEpisodeSceneNode => ({
    ...scene,
    shotIds: shotIdsBySceneId[scene.id] ?? [],
  }));
  const scenesById = recordById(scenes, 'script scene view nodes');
  const narrativeBeats = beats.map(
    (beat): StoryWorkspaceEpisodeNarrativeBeatNode => ({
      ...beat,
      sceneIds: sceneIdsByBeatId[beat.id] ?? [],
      shotIds: shotIdsByBeatId[beat.id] ?? [],
    }),
  );
  const narrativeBeatsById = recordById(
    narrativeBeats,
    'narrative beat view nodes',
  );

  const promptsByShotViewId: Record<string, StoryWorkspaceEpisodePrompt[]> = {};
  const renderQueueByShotViewId: Record<
    string,
    StoryWorkspaceEpisodeRenderQueueEntry[]
  > = {};
  const reviewTargetsByTargetViewId: Record<
    string,
    StoryWorkspaceEpisodeReviewTarget[]
  > = {};
  const unlinkedPrompts: StoryWorkspaceEpisodePrompt[] = [];
  const orphanPrompts: StoryWorkspaceEpisodePrompt[] = [];
  const unlinkedRenderQueueEntries: StoryWorkspaceEpisodeRenderQueueEntry[] = [];
  const orphanRenderQueueEntries: StoryWorkspaceEpisodeRenderQueueEntry[] = [];
  const unlinkedReviewTargets: StoryWorkspaceEpisodeReviewTarget[] = [];
  const orphanReviewTargets: StoryWorkspaceEpisodeReviewTarget[] = [];

  for (const prompt of surface.auxiliary?.prompts.items ?? []) {
    if (prompt.associationStatus === 'unlinked') {
      unlinkedPrompts.push(prompt);
    } else if (
      prompt.associationStatus === 'linked'
      && prompt.shotViewId !== null
      && shotsById[prompt.shotViewId] !== undefined
    ) {
      appendIndexed(promptsByShotViewId, prompt.shotViewId, prompt);
    } else {
      orphanPrompts.push(prompt);
    }
  }

  for (const queueEntry of surface.auxiliary?.renderGuide?.queue.items ?? []) {
    if (queueEntry.associationStatus === 'unlinked') {
      unlinkedRenderQueueEntries.push(queueEntry);
    } else if (
      queueEntry.associationStatus === 'linked'
      && queueEntry.shotViewId !== null
      && shotsById[queueEntry.shotViewId] !== undefined
    ) {
      appendIndexed(renderQueueByShotViewId, queueEntry.shotViewId, queueEntry);
    } else {
      orphanRenderQueueEntries.push(queueEntry);
    }
  }

  const reviewTargetIds: Readonly<Record<StoryWorkspaceEpisodeReviewTarget['kind'], Set<string>>> = {
    'narrative-beat': new Set(Object.keys(narrativeBeatsById)),
    'script-scene': new Set(Object.keys(scenesById)),
    shot: new Set(Object.keys(shotsById)),
  };
  for (const target of surface.auxiliary?.review?.targets ?? []) {
    if (target.associationStatus === 'unlinked') {
      unlinkedReviewTargets.push(target);
    } else if (
      target.associationStatus === 'linked'
      && target.targetViewId !== null
      && reviewTargetIds[target.kind].has(target.targetViewId)
    ) {
      appendIndexed(reviewTargetsByTargetViewId, target.targetViewId, target);
    } else {
      orphanReviewTargets.push(target);
    }
  }

  const overview = narrative?.overview;
  const episode = narrative === null
    ? null
    : {
        kind: 'episode' as const,
        id: narrative.episodeId,
        title: overview?.title ?? null,
        storyArcId: narrative.storyArcId,
        sourceArtifact: overview?.sourceArtifact ?? null,
        sourceRevision: overview?.sourceRevision ?? null,
        sourceAvailability: sourceAvailability(
          overview?.sourceArtifact ?? null,
          overview?.sourceRevision ?? null,
        ),
      };
  const storyArc = narrative === null
    ? null
    : {
        kind: 'story-arc' as const,
        id: narrative.storyArcId,
        episodeId: narrative.episodeId,
        narrativeBeatIds: narrativeBeats.map((beat) => beat.id),
        sourceArtifact: overview?.sourceArtifact ?? null,
        sourceRevision: overview?.sourceRevision ?? null,
        sourceAvailability: sourceAvailability(
          overview?.sourceArtifact ?? null,
          overview?.sourceRevision ?? null,
        ),
      };

  return {
    episode,
    storyArc,
    narrativeBeatsById,
    scenesById,
    shotsById,
    promptsByShotViewId,
    renderQueueByShotViewId,
    reviewTargetsByTargetViewId,
    unlinked: {
      scenes: unlinkedScenes.map((scene) => scenesById[scene.id]),
      shots: unlinkedShots,
      prompts: unlinkedPrompts,
      renderQueueEntries: unlinkedRenderQueueEntries,
      reviewTargets: unlinkedReviewTargets,
    },
    orphans: {
      scenes: orphanScenes.map((scene) => scenesById[scene.id]),
      shots: orphanShots,
      prompts: orphanPrompts,
      renderQueueEntries: orphanRenderQueueEntries,
      reviewTargets: orphanReviewTargets,
    },
    coverage: {
      beatScene: coverageView(
        narrative?.associations.beatSceneCoverage ?? unavailableCoverage,
      ),
      sceneShot: coverageView(
        narrative?.associations.sceneShotCoverage ?? unavailableCoverage,
      ),
      shotPrompt: coverageView(
        surface.auxiliary?.associations.shotPromptCoverage ?? unavailableCoverage,
      ),
      shotRenderQueue: coverageView(
        surface.auxiliary?.associations.shotRenderQueueCoverage
          ?? unavailableCoverage,
      ),
    },
  };
}

export function storyWorkspaceEpisodeDefaultSelection(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
): StoryWorkspaceEpisodeSelection | null {
  return viewModel.episode === null
    ? null
    : { kind: 'episode', id: viewModel.episode.id };
}

function navigationItem(
  node: {
    readonly id: string;
    readonly kind: StoryWorkspaceEpisodeSelectionKind;
    readonly sourceArtifact: string | null;
    readonly sourceRevision: string | null;
    readonly sourceAvailability: StoryWorkspaceEpisodeSourceAvailability;
  },
  options: {
    readonly level: StoryWorkspaceEpisodeNavigationItem['level'];
    readonly canonicalParent: StoryWorkspaceEpisodeSelection | null;
    readonly navigationParent: StoryWorkspaceEpisodeSelection | null;
    readonly auxiliaryGroup: 'unlinked' | 'orphan' | null;
    readonly children?: readonly StoryWorkspaceEpisodeSelection[];
    readonly expanded?: boolean;
  },
): StoryWorkspaceEpisodeNavigationItem {
  return {
    id: node.id,
    kind: node.kind,
    level: options.level,
    canonicalParent: options.canonicalParent,
    navigationParent: options.navigationParent,
    auxiliaryGroup: options.auxiliaryGroup,
    children: options.children ?? [],
    expanded: options.expanded ?? false,
    sourceArtifact: node.sourceArtifact,
    sourceRevision: node.sourceRevision,
    sourceAvailability: node.sourceAvailability,
  };
}

export function storyWorkspaceEpisodeSelectionKey(
  selection: StoryWorkspaceEpisodeSelection,
): string {
  return `${selection.kind}:${selection.id}`;
}

function itemSelection(
  item: Pick<StoryWorkspaceEpisodeNavigationItem, 'kind' | 'id'>,
): StoryWorkspaceEpisodeSelection {
  return { kind: item.kind, id: item.id };
}

function auxiliaryNavigationNodes(
  artifacts: StoryWorkspaceEpisodeDetachedArtifacts,
): Array<{
  readonly id: string;
  readonly kind: StoryWorkspaceEpisodeSelectionKind;
  readonly sourceArtifact: string;
  readonly sourceRevision: string | null;
  readonly sourceAvailability: StoryWorkspaceEpisodeSourceAvailability;
}> {
  return [
    ...artifacts.scenes,
    ...artifacts.shots,
    ...artifacts.prompts.map((prompt) => ({
      ...prompt,
      kind: 'prompt' as const,
      sourceAvailability: 'available' as const,
    })),
    ...artifacts.renderQueueEntries.map((entry) => ({
      ...entry,
      kind: 'render-queue' as const,
      sourceAvailability: 'available' as const,
    })),
    ...artifacts.reviewTargets.map((target) => ({
      ...target,
      kind: 'review-target' as const,
      sourceAvailability: 'available' as const,
    })),
  ];
}

function appendAuxiliaryNavigationGroup(
  items: StoryWorkspaceEpisodeNavigationItem[],
  artifacts: StoryWorkspaceEpisodeDetachedArtifacts,
  group: 'unlinked' | 'orphan',
  expandedKeys: ReadonlySet<string>,
): void {
  const nodes = auxiliaryNavigationNodes(artifacts);
  if (nodes.length === 0) return;
  const groupSelection: StoryWorkspaceEpisodeSelection = {
    kind: 'auxiliary-group',
    id: group === 'unlinked'
      ? STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID
      : STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
  };
  const expanded = expandedKeys.has(
    storyWorkspaceEpisodeSelectionKey(groupSelection),
  );
  items.push(navigationItem({
    ...groupSelection,
    sourceArtifact: null,
    sourceRevision: null,
    sourceAvailability: 'unavailable',
  }, {
    level: 1,
    canonicalParent: null,
    navigationParent: null,
    auxiliaryGroup: group,
    children: nodes.map(itemSelection),
    expanded,
  }));
  if (!expanded) return;
  for (const node of nodes) {
    items.push(navigationItem(node, {
      level: 2,
      canonicalParent: null,
      navigationParent: groupSelection,
      auxiliaryGroup: group,
    }));
  }
}

export function storyWorkspaceEpisodeNavigationItems(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  expandedKeys: ReadonlySet<string>,
): readonly StoryWorkspaceEpisodeNavigationItem[] {
  if (viewModel.episode === null || viewModel.storyArc === null) {
    return [];
  }
  const episodeSelection: StoryWorkspaceEpisodeSelection = {
    kind: 'episode',
    id: viewModel.episode.id,
  };
  const beatSelections = viewModel.storyArc.narrativeBeatIds.map((id) => ({
    kind: 'narrative-beat' as const,
    id,
  }));
  const items: StoryWorkspaceEpisodeNavigationItem[] = [
    navigationItem(viewModel.episode, {
      level: 1,
      canonicalParent: null,
      navigationParent: null,
      auxiliaryGroup: null,
      children: beatSelections,
      expanded: true,
    }),
  ];
  for (const beatId of viewModel.storyArc.narrativeBeatIds) {
    const beat = viewModel.narrativeBeatsById[beatId];
    if (beat === undefined) continue;
    const beatSelection = itemSelection(beat);
    const sceneSelections = beat.sceneIds.map((id) => ({
      kind: 'scene' as const,
      id,
    }));
    const beatExpanded = expandedKeys.has(
      storyWorkspaceEpisodeSelectionKey(beatSelection),
    );
    items.push(navigationItem(beat, {
      level: 2,
      canonicalParent: { kind: 'story-arc', id: viewModel.storyArc.id },
      navigationParent: episodeSelection,
      auxiliaryGroup: null,
      children: sceneSelections,
      expanded: beatExpanded,
    }));
    if (!beatExpanded) continue;
    for (const sceneId of beat.sceneIds) {
      const scene = viewModel.scenesById[sceneId];
      if (scene === undefined) continue;
      const sceneSelection = itemSelection(scene);
      const shotSelections = scene.shotIds.map((id) => ({
        kind: 'shot' as const,
        id,
      }));
      const sceneExpanded = expandedKeys.has(
        storyWorkspaceEpisodeSelectionKey(sceneSelection),
      );
      items.push(navigationItem(scene, {
        level: 3,
        canonicalParent: beatSelection,
        navigationParent: beatSelection,
        auxiliaryGroup: null,
        children: shotSelections,
        expanded: sceneExpanded,
      }));
      if (!sceneExpanded) continue;
      for (const shotId of scene.shotIds) {
        const shot = viewModel.shotsById[shotId];
        if (shot !== undefined) {
          items.push(navigationItem(shot, {
            level: 4,
            canonicalParent: sceneSelection,
            navigationParent: sceneSelection,
            auxiliaryGroup: null,
          }));
        }
      }
    }
  }
  appendAuxiliaryNavigationGroup(
    items,
    viewModel.unlinked,
    'unlinked',
    expandedKeys,
  );
  appendAuxiliaryNavigationGroup(
    items,
    viewModel.orphans,
    'orphan',
    expandedKeys,
  );
  return items;
}

export function storyWorkspaceEpisodeNavigationNeighbors(
  items: readonly StoryWorkspaceEpisodeNavigationItem[],
  currentSelection: StoryWorkspaceEpisodeSelection,
): StoryWorkspaceEpisodeNavigationNeighbors {
  const currentKey = storyWorkspaceEpisodeSelectionKey(currentSelection);
  const current = items.find(
    (item) => storyWorkspaceEpisodeSelectionKey(itemSelection(item)) === currentKey,
  );
  if (current === undefined) {
    return {
      previousSibling: null,
      nextSibling: null,
      parent: null,
      firstChild: null,
    };
  }
  const parentKey = current.navigationParent === null
    ? null
    : storyWorkspaceEpisodeSelectionKey(current.navigationParent);
  const siblings = items.filter((item) => {
    const itemParentKey = item.navigationParent === null
      ? null
      : storyWorkspaceEpisodeSelectionKey(item.navigationParent);
    return itemParentKey === parentKey && item.level === current.level;
  });
  const siblingIndex = siblings.findIndex(
    (item) => storyWorkspaceEpisodeSelectionKey(itemSelection(item)) === currentKey,
  );
  return {
    previousSibling: siblings[siblingIndex - 1] === undefined
      ? null
      : itemSelection(siblings[siblingIndex - 1]),
    nextSibling: siblings[siblingIndex + 1] === undefined
      ? null
      : itemSelection(siblings[siblingIndex + 1]),
    parent: current.navigationParent,
    firstChild: current.children[0] ?? null,
  };
}

export function storyWorkspaceEpisodeNavigationAction(
  items: readonly StoryWorkspaceEpisodeNavigationItem[],
  currentSelection: StoryWorkspaceEpisodeSelection,
  key: StoryWorkspaceEpisodeNavigationKey,
): StoryWorkspaceEpisodeNavigationAction {
  const currentKey = storyWorkspaceEpisodeSelectionKey(currentSelection);
  const current = items.find(
    (item) => storyWorkspaceEpisodeSelectionKey(itemSelection(item)) === currentKey,
  );
  if (current === undefined) return { action: 'noop', target: null };
  const neighbors = storyWorkspaceEpisodeNavigationNeighbors(
    items,
    currentSelection,
  );
  if (key === 'ArrowUp' || key === 'ArrowDown') {
    const target = key === 'ArrowUp'
      ? neighbors.previousSibling
      : neighbors.nextSibling;
    return target === null
      ? { action: 'noop', target: null }
      : { action: 'move-sibling', target };
  }
  if (key === 'ArrowRight') {
    if (current.children.length === 0) return { action: 'noop', target: null };
    if (!current.expanded) return { action: 'expand', target: currentSelection };
    return { action: 'move-first-child', target: neighbors.firstChild };
  }
  if (
    current.kind !== 'episode'
    && current.expanded
    && current.children.length > 0
  ) {
    return { action: 'collapse', target: currentSelection };
  }
  return neighbors.parent === null
    ? { action: 'noop', target: null }
    : { action: 'move-parent', target: neighbors.parent };
}

function recordValues<T>(record: Readonly<Record<string, readonly T[]>>): T[] {
  return Object.values(record).flatMap((items) => [...items]);
}

function selectionExists(
  selection: StoryWorkspaceEpisodeSelection,
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
): boolean {
  if (selection.kind === 'episode') return viewModel.episode?.id === selection.id;
  if (selection.kind === 'story-arc') return viewModel.storyArc?.id === selection.id;
  if (selection.kind === 'narrative-beat') {
    return viewModel.narrativeBeatsById[selection.id] !== undefined;
  }
  if (selection.kind === 'scene') return viewModel.scenesById[selection.id] !== undefined;
  if (selection.kind === 'shot') return viewModel.shotsById[selection.id] !== undefined;
  if (selection.kind === 'prompt') {
    return [
      ...recordValues(viewModel.promptsByShotViewId),
      ...viewModel.unlinked.prompts,
      ...viewModel.orphans.prompts,
    ].some((item) => item.id === selection.id);
  }
  if (selection.kind === 'render-queue') {
    return [
      ...recordValues(viewModel.renderQueueByShotViewId),
      ...viewModel.unlinked.renderQueueEntries,
      ...viewModel.orphans.renderQueueEntries,
    ].some((item) => item.id === selection.id);
  }
  if (selection.kind === 'review-target') {
    return [
      ...recordValues(viewModel.reviewTargetsByTargetViewId),
      ...viewModel.unlinked.reviewTargets,
      ...viewModel.orphans.reviewTargets,
    ].some((item) => item.id === selection.id);
  }
  const artifacts = selection.id === STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID
    ? viewModel.unlinked
    : selection.id === STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID
      ? viewModel.orphans
      : null;
  return artifacts !== null && auxiliaryNavigationNodes(artifacts).length > 0;
}

function firstExistingSelection(
  candidates: readonly (StoryWorkspaceEpisodeSelection | null)[],
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
): StoryWorkspaceEpisodeSelection | null {
  return candidates.find(
    (candidate): candidate is StoryWorkspaceEpisodeSelection => (
      candidate !== null && selectionExists(candidate, viewModel)
    ),
  ) ?? storyWorkspaceEpisodeDefaultSelection(viewModel);
}

function findPrompt(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  id: string,
): StoryWorkspaceEpisodePrompt | undefined {
  return [
    ...recordValues(viewModel.promptsByShotViewId),
    ...viewModel.unlinked.prompts,
    ...viewModel.orphans.prompts,
  ].find((item) => item.id === id);
}

function findQueueEntry(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  id: string,
): StoryWorkspaceEpisodeRenderQueueEntry | undefined {
  return [
    ...recordValues(viewModel.renderQueueByShotViewId),
    ...viewModel.unlinked.renderQueueEntries,
    ...viewModel.orphans.renderQueueEntries,
  ].find((item) => item.id === id);
}

function findReviewTarget(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  id: string,
): StoryWorkspaceEpisodeReviewTarget | undefined {
  return [
    ...recordValues(viewModel.reviewTargetsByTargetViewId),
    ...viewModel.unlinked.reviewTargets,
    ...viewModel.orphans.reviewTargets,
  ].find((item) => item.id === id);
}

function sceneAncestorSelections(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  sceneId: string | null,
): StoryWorkspaceEpisodeSelection[] {
  if (sceneId === null) return [];
  const scene = viewModel.scenesById[sceneId];
  if (scene === undefined) return [];
  const selections: StoryWorkspaceEpisodeSelection[] = [
    { kind: 'scene', id: scene.id },
  ];
  if (scene.narrativeBeatId !== null) {
    selections.push({ kind: 'narrative-beat', id: scene.narrativeBeatId });
  }
  return selections;
}

function shotAncestorSelections(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  shotId: string | null,
): StoryWorkspaceEpisodeSelection[] {
  if (shotId === null) return [];
  const shot = viewModel.shotsById[shotId];
  if (shot === undefined) return [];
  const selections: StoryWorkspaceEpisodeSelection[] = [
    { kind: 'shot', id: shot.id },
  ];
  const scene = shot.scriptSceneId === null
    ? undefined
    : viewModel.scenesById[shot.scriptSceneId];
  if (scene !== undefined && scene.shotIds.includes(shot.id)) {
    selections.push(...sceneAncestorSelections(viewModel, scene.id));
  }
  return selections;
}

function reviewTargetAncestorSelections(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  target: StoryWorkspaceEpisodeReviewTarget | undefined,
): StoryWorkspaceEpisodeSelection[] {
  if (target?.targetViewId === null || target?.targetViewId === undefined) return [];
  if (target.kind === 'shot') {
    return shotAncestorSelections(viewModel, target.targetViewId);
  }
  if (target.kind === 'script-scene') {
    return sceneAncestorSelections(viewModel, target.targetViewId);
  }
  return [{ kind: 'narrative-beat', id: target.targetViewId }];
}

export function storyWorkspaceReconcileEpisodeSelection(
  previousSelection: StoryWorkspaceEpisodeSelection | null,
  previousViewModel: StoryWorkspaceEpisodeExecutionViewModel,
  nextViewModel: StoryWorkspaceEpisodeExecutionViewModel,
): StoryWorkspaceEpisodeSelection | null {
  if (previousSelection === null) {
    return storyWorkspaceEpisodeDefaultSelection(nextViewModel);
  }
  if (selectionExists(previousSelection, nextViewModel)) return previousSelection;

  if (previousSelection.kind === 'shot') {
    return firstExistingSelection(
      shotAncestorSelections(previousViewModel, previousSelection.id),
      nextViewModel,
    );
  }
  if (previousSelection.kind === 'scene') {
    return firstExistingSelection(
      sceneAncestorSelections(previousViewModel, previousSelection.id),
      nextViewModel,
    );
  }
  if (previousSelection.kind === 'prompt') {
    const prompt = findPrompt(previousViewModel, previousSelection.id);
    return firstExistingSelection(
      shotAncestorSelections(previousViewModel, prompt?.shotViewId ?? null),
      nextViewModel,
    );
  }
  if (previousSelection.kind === 'render-queue') {
    const queueEntry = findQueueEntry(previousViewModel, previousSelection.id);
    return firstExistingSelection(
      shotAncestorSelections(previousViewModel, queueEntry?.shotViewId ?? null),
      nextViewModel,
    );
  }
  if (previousSelection.kind === 'review-target') {
    const target = findReviewTarget(previousViewModel, previousSelection.id);
    return firstExistingSelection(
      reviewTargetAncestorSelections(previousViewModel, target),
      nextViewModel,
    );
  }
  return storyWorkspaceEpisodeDefaultSelection(nextViewModel);
}
