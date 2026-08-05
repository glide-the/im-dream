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

export type StoryWorkspaceEpisodeNavigationKind =
  | 'episode'
  | 'narrative-beat'
  | 'scene'
  | 'shot';

export interface StoryWorkspaceEpisodeSelection {
  readonly kind: StoryWorkspaceEpisodeNavigationKind;
  readonly id: string;
}

export interface StoryWorkspaceEpisodeNavigationItem
  extends StoryWorkspaceEpisodeSourceFact {
  readonly id: string;
  readonly kind: StoryWorkspaceEpisodeNavigationKind;
  readonly parentId: string | null;
  readonly level: 1 | 2 | 3 | 4;
}

export interface StoryWorkspaceEpisodeNavigationNeighbors {
  readonly previousId: string | null;
  readonly nextId: string | null;
  readonly parentId: string | null;
  readonly firstChildId: string | null;
}

export type StoryWorkspaceEpisodeNavigationKey =
  | 'ArrowUp'
  | 'ArrowDown'
  | 'ArrowLeft'
  | 'ArrowRight';

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
    readonly kind: StoryWorkspaceEpisodeNavigationKind;
    readonly sourceArtifact: string | null;
    readonly sourceRevision: string | null;
    readonly sourceAvailability: StoryWorkspaceEpisodeSourceAvailability;
  },
  parentId: string | null,
  level: StoryWorkspaceEpisodeNavigationItem['level'],
): StoryWorkspaceEpisodeNavigationItem {
  return {
    id: node.id,
    kind: node.kind,
    parentId,
    level,
    sourceArtifact: node.sourceArtifact,
    sourceRevision: node.sourceRevision,
    sourceAvailability: node.sourceAvailability,
  };
}

export function storyWorkspaceEpisodeNavigationItems(
  viewModel: StoryWorkspaceEpisodeExecutionViewModel,
  expandedIds: ReadonlySet<string>,
): readonly StoryWorkspaceEpisodeNavigationItem[] {
  if (viewModel.episode === null || viewModel.storyArc === null) {
    return [];
  }
  const items: StoryWorkspaceEpisodeNavigationItem[] = [
    navigationItem(viewModel.episode, null, 1),
  ];
  for (const beatId of viewModel.storyArc.narrativeBeatIds) {
    const beat = viewModel.narrativeBeatsById[beatId];
    if (beat === undefined) continue;
    items.push(navigationItem(beat, viewModel.episode.id, 2));
    if (!expandedIds.has(beat.id)) continue;
    for (const sceneId of beat.sceneIds) {
      const scene = viewModel.scenesById[sceneId];
      if (scene === undefined) continue;
      items.push(navigationItem(scene, beat.id, 3));
      if (!expandedIds.has(scene.id)) continue;
      for (const shotId of scene.shotIds) {
        const shot = viewModel.shotsById[shotId];
        if (shot !== undefined) {
          items.push(navigationItem(shot, scene.id, 4));
        }
      }
    }
  }
  return items;
}

export function storyWorkspaceEpisodeNavigationNeighbors(
  items: readonly StoryWorkspaceEpisodeNavigationItem[],
  currentId: string,
): StoryWorkspaceEpisodeNavigationNeighbors {
  const index = items.findIndex((item) => item.id === currentId);
  if (index < 0) {
    return {
      previousId: null,
      nextId: null,
      parentId: null,
      firstChildId: null,
    };
  }
  const current = items[index];
  return {
    previousId: items[index - 1]?.id ?? null,
    nextId: items[index + 1]?.id ?? null,
    parentId: current.parentId,
    firstChildId: items.find((item) => item.parentId === current.id)?.id ?? null,
  };
}

export function storyWorkspaceEpisodeNavigationTarget(
  items: readonly StoryWorkspaceEpisodeNavigationItem[],
  currentId: string,
  key: StoryWorkspaceEpisodeNavigationKey,
): string | null {
  const neighbors = storyWorkspaceEpisodeNavigationNeighbors(items, currentId);
  if (key === 'ArrowUp') return neighbors.previousId;
  if (key === 'ArrowDown') return neighbors.nextId;
  if (key === 'ArrowLeft') return neighbors.parentId;
  return neighbors.firstChildId;
}
