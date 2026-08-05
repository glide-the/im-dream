// [Input] Parsed Episode artifact surface with explicit opaque associations.
// [Output] Pure storyline hierarchy, auxiliary indexes and keyboard navigation coverage.
// [Pos] Story Workspace Episode execution view-model Node seam (Task 3 U6).

import { expect, test } from '@playwright/test';
import type {
  StoryWorkspaceEpisodeArtifactSurface,
  StoryWorkspaceEpisodeAssociationCoverage,
  StoryWorkspaceEpisodeAuxiliaryProjection,
  StoryWorkspaceEpisodeNarrativeProjection,
} from '../../../hooks/story-workspace/contracts';
import {
  storyWorkspaceBuildEpisodeExecutionViewModel,
  storyWorkspaceEpisodeCoverageLabel,
  storyWorkspaceEpisodeDefaultSelection,
  storyWorkspaceEpisodeNavigationItems,
  storyWorkspaceEpisodeNavigationNeighbors,
  storyWorkspaceEpisodeNavigationTarget,
} from '../episodeExecutionViewModel';

const opaqueId = (value: number) => value.toString(16).padStart(32, '0');
const revision = (value: string) => `sha256:${value.repeat(64)}`;

const EPISODE_ID = opaqueId(1);
const ARC_ID = opaqueId(2);
const BEAT_ID = opaqueId(3);
const EMPTY_BEAT_ID = opaqueId(4);
const SCENE_ID = opaqueId(5);
const UNLINKED_SCENE_ID = opaqueId(6);
const ORPHAN_SCENE_ID = opaqueId(7);
const SHOT_ID = opaqueId(8);
const UNLINKED_SHOT_ID = opaqueId(9);
const ORPHAN_SHOT_ID = opaqueId(10);
const PROMPT_ID = opaqueId(11);
const UNLINKED_PROMPT_ID = opaqueId(12);
const ORPHAN_PROMPT_ID = opaqueId(13);
const QUEUE_ID = opaqueId(14);
const UNLINKED_QUEUE_ID = opaqueId(15);
const REVIEW_SHOT_ID = opaqueId(16);
const REVIEW_UNKNOWN_ID = opaqueId(17);

function coverage(linked: number, total: number): StoryWorkspaceEpisodeAssociationCoverage {
  return {
    availability: total === 0 ? 'unavailable' : 'available',
    linked,
    total,
    ratio: total === 0 ? null : linked / total,
  };
}

function narrative(): StoryWorkspaceEpisodeNarrativeProjection {
  return {
    episodeId: EPISODE_ID,
    storyArcId: ARC_ID,
    overview: {
      title: '雨夜重逢',
      series: '归途',
      storyGoals: ['让主角做出选择'],
      coreConflict: '留下或离开',
      hook: '熟悉的背影出现',
      sourceArtifact: 'episode-outline.md',
      sourceRevision: revision('a'),
      generatedFrom: null,
      characterBeats: [],
    },
    narrativeBeats: [
      {
        id: BEAT_ID,
        sourceKey: 'SC-01',
        title: '失去控制',
        assetSceneRef: null,
        narrativeFunction: '触发冲突',
        emotionTone: '紧张',
        summary: '主角停下脚步。',
        sceneGoals: ['暴露犹豫'],
        keyDialogueBeats: [],
        sourceArtifact: 'episode-outline.md',
        sourceRevision: revision('a'),
        generatedFrom: null,
      },
      {
        id: EMPTY_BEAT_ID,
        sourceKey: 'SC-02',
        title: '做出选择',
        assetSceneRef: null,
        narrativeFunction: null,
        emotionTone: null,
        summary: null,
        sceneGoals: [],
        keyDialogueBeats: [],
        sourceArtifact: 'episode-outline.md',
        sourceRevision: revision('a'),
        generatedFrom: null,
      },
    ],
    scenes: [
      {
        id: UNLINKED_SCENE_ID,
        sourceKey: 'S02',
        title: '候车室',
        heading: 'INT. 候车室 - 夜',
        assetSceneRef: null,
        narrativeBeatId: null,
        declaredNarrativeBeatRef: null,
        associationStatus: 'unlinked',
        actions: [],
        dialogue: [],
        cameraCues: [],
        sourceArtifact: 'script.md',
        sourceRevision: revision('b'),
        generatedFrom: null,
      },
      {
        id: SCENE_ID,
        sourceKey: 'S01',
        title: '站台',
        heading: 'EXT. 站台 - 夜',
        assetSceneRef: null,
        narrativeBeatId: BEAT_ID,
        declaredNarrativeBeatRef: 'SC-01',
        associationStatus: 'linked',
        actions: ['林默停步。'],
        dialogue: [],
        cameraCues: [],
        sourceArtifact: 'script.md',
        sourceRevision: revision('b'),
        generatedFrom: null,
      },
      {
        id: ORPHAN_SCENE_ID,
        sourceKey: 'S03',
        title: '未知场景',
        heading: 'EXT. UNKNOWN - NIGHT',
        assetSceneRef: null,
        narrativeBeatId: null,
        declaredNarrativeBeatRef: 'SC-99',
        associationStatus: 'orphan',
        actions: [],
        dialogue: [],
        cameraCues: [],
        sourceArtifact: 'script.md',
        sourceRevision: revision('b'),
        generatedFrom: null,
      },
    ],
    shots: [
      {
        id: UNLINKED_SHOT_ID,
        shotId: 'SUP-E01-01',
        assetSceneRef: null,
        declaredScriptSceneRef: null,
        declaredNarrativeBeatRef: null,
        scriptSceneId: null,
        narrativeBeatId: null,
        associationStatus: 'unlinked',
        shotType: 'insert',
        characters: [],
        camera: { angle: null, height: null, movement: null, lens: null },
        visual: '雨水落下。',
        dialogue: [],
        timing: { durationSec: 1, transitionIn: null, transitionOut: null },
        sourceArtifact: 'storyboard.yaml',
        sourceRevision: revision('c'),
        generatedFrom: null,
      },
      {
        id: SHOT_ID,
        shotId: 'S01-E01-SH01',
        assetSceneRef: null,
        declaredScriptSceneRef: 'S01',
        declaredNarrativeBeatRef: 'SC-01',
        scriptSceneId: SCENE_ID,
        narrativeBeatId: BEAT_ID,
        associationStatus: 'linked',
        shotType: 'wide',
        characters: [],
        camera: { angle: 'eye', height: null, movement: 'static', lens: null },
        visual: '雨夜站台。',
        dialogue: [],
        timing: { durationSec: 3, transitionIn: null, transitionOut: null },
        sourceArtifact: 'storyboard.yaml',
        sourceRevision: revision('c'),
        generatedFrom: null,
      },
      {
        id: ORPHAN_SHOT_ID,
        shotId: 'S99-E01-SH01',
        assetSceneRef: null,
        declaredScriptSceneRef: 'S99',
        declaredNarrativeBeatRef: null,
        scriptSceneId: null,
        narrativeBeatId: null,
        associationStatus: 'orphan',
        shotType: null,
        characters: [],
        camera: { angle: null, height: null, movement: null, lens: null },
        visual: null,
        dialogue: [],
        timing: { durationSec: null, transitionIn: null, transitionOut: null },
        sourceArtifact: 'storyboard.yaml',
        sourceRevision: revision('c'),
        generatedFrom: null,
      },
    ],
    associations: {
      beatSceneCoverage: coverage(1, 3),
      sceneShotCoverage: coverage(1, 3),
      missingLinks: ['S02 has no narrative beat'],
      orphanArtifacts: ['S03', 'S99-E01-SH01'],
    },
  };
}

function auxiliary(): StoryWorkspaceEpisodeAuxiliaryProjection {
  return {
    manifestRevision: revision('d'),
    prompts: {
      total: 3,
      nextCursor: null,
      items: [
        {
          id: PROMPT_ID,
          shotId: 'S01-E01-SH01',
          kind: 'image',
          shotViewId: SHOT_ID,
          associationStatus: 'linked',
          positive: 'rainy platform',
          negative: null,
          parameters: {
            model: null, mode: null, durationSec: null, motionStrength: null,
            cameraMotion: null, aspectRatio: null,
          },
          generability: {
            characterAnchor: null, motionFeasibility: null,
            durationBudget: null, notes: null,
          },
          sourceArtifact: 'prompts/S01-E01-SH01.yaml',
          sourceRevision: revision('e'),
        },
        {
          id: UNLINKED_PROMPT_ID,
          shotId: 'S01-E01-SH01',
          kind: 'video',
          shotViewId: null,
          associationStatus: 'unlinked',
          positive: 'must not join by shotId',
          negative: null,
          parameters: {
            model: null, mode: null, durationSec: null, motionStrength: null,
            cameraMotion: null, aspectRatio: null,
          },
          generability: {
            characterAnchor: null, motionFeasibility: null,
            durationBudget: null, notes: null,
          },
          sourceArtifact: 'prompts/unlinked.yaml',
          sourceRevision: revision('e'),
        },
        {
          id: ORPHAN_PROMPT_ID,
          shotId: 'S99-E01-SH01',
          kind: 'image',
          shotViewId: null,
          associationStatus: 'orphan',
          positive: 'orphan',
          negative: null,
          parameters: {
            model: null, mode: null, durationSec: null, motionStrength: null,
            cameraMotion: null, aspectRatio: null,
          },
          generability: {
            characterAnchor: null, motionFeasibility: null,
            durationBudget: null, notes: null,
          },
          sourceArtifact: 'prompts/orphan.yaml',
          sourceRevision: revision('e'),
        },
      ],
    },
    renderGuide: {
      sections: [],
      queue: {
        total: 2,
        nextCursor: null,
        items: [
          {
            id: QUEUE_ID,
            shotId: 'S01-E01-SH01',
            shotViewId: SHOT_ID,
            associationStatus: 'linked',
            durationSec: 3,
            risk: null,
            priority: 'high',
            renderer: null,
            status: 'pending',
            sourceArtifact: 'renders/render-guide.md',
            sourceRevision: revision('f'),
          },
          {
            id: UNLINKED_QUEUE_ID,
            shotId: 'S01-E01-SH01',
            shotViewId: null,
            associationStatus: 'unlinked',
            durationSec: 3,
            risk: null,
            priority: null,
            renderer: null,
            status: 'pending',
            sourceArtifact: 'renders/render-guide.md',
            sourceRevision: revision('f'),
          },
        ],
      },
      sourceArtifact: 'renders/render-guide.md',
      sourceRevision: revision('f'),
    },
    review: {
      scope: 'full-chain',
      overallVerdict: null,
      reviewedArtifacts: [],
      sourceRevisions: [],
      sections: [],
      targets: [
        {
          id: REVIEW_SHOT_ID,
          kind: 'shot',
          sourceKey: 'S01-E01-SH01',
          targetViewId: SHOT_ID,
          associationStatus: 'linked',
          sectionId: opaqueId(18),
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_UNKNOWN_ID,
          kind: 'shot',
          sourceKey: 'S01-E01-SH01',
          targetViewId: null,
          associationStatus: 'unlinked',
          sectionId: opaqueId(19),
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
      ],
      sourceArtifact: 'review-report.md',
      sourceRevision: revision('1'),
    },
    associations: {
      shotPromptCoverage: coverage(1, 3),
      shotRenderQueueCoverage: coverage(1, 3),
      totalPrompts: 3,
      totalQueueEntries: 2,
      orphanPrompts: [ORPHAN_PROMPT_ID],
      orphanQueueEntries: [],
      duplicateQueueShotIds: [],
    },
  };
}

function surface(
  narrativeProjection: StoryWorkspaceEpisodeNarrativeProjection | null = narrative(),
  auxiliaryProjection: StoryWorkspaceEpisodeAuxiliaryProjection | null = auxiliary(),
): StoryWorkspaceEpisodeArtifactSurface {
  return {
    runId: `run_${'2'.repeat(32)}`,
    opaqueEpisodeId: narrativeProjection?.episodeId ?? null,
    manifestRevision: revision('2'),
    etag: revision('2'),
    bindingAvailability: 'bound',
    bindingRecovery: {
      autoRepairAttempted: false,
      canDispatch: false,
      publicReason: null,
    },
    artifacts: [],
    narrative: narrativeProjection,
    auxiliary: auxiliaryProjection,
  };
}

test('builds Episode → Arc → Beat → Scene → Shot only from opaque relationship ids', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());

  expect(viewModel.episode).toMatchObject({
    id: EPISODE_ID,
    storyArcId: ARC_ID,
    sourceArtifact: 'episode-outline.md',
    sourceRevision: revision('a'),
    sourceAvailability: 'available',
  });
  expect(viewModel.storyArc).toMatchObject({
    id: ARC_ID,
    episodeId: EPISODE_ID,
    narrativeBeatIds: [BEAT_ID, EMPTY_BEAT_ID],
  });
  expect(viewModel.narrativeBeatsById[BEAT_ID]).toMatchObject({
    id: BEAT_ID,
    sceneIds: [SCENE_ID],
    shotIds: [SHOT_ID],
  });
  expect(viewModel.scenesById[SCENE_ID]).toMatchObject({
    id: SCENE_ID,
    narrativeBeatId: BEAT_ID,
    shotIds: [SHOT_ID],
  });
  expect(viewModel.shotsById[SHOT_ID]).toMatchObject({
    id: SHOT_ID,
    scriptSceneId: SCENE_ID,
    narrativeBeatId: BEAT_ID,
  });
  expect(Object.keys(viewModel.narrativeBeatsById)).not.toContain('0');
  expect(Object.keys(viewModel.scenesById)).not.toContain('1');
  expect(Object.keys(viewModel.shotsById)).not.toContain('1');
});

test('keeps unlinked and orphan narrative nodes in separate explicit groups', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());

  expect(viewModel.unlinked.scenes.map((item) => item.id)).toEqual([UNLINKED_SCENE_ID]);
  expect(viewModel.unlinked.shots.map((item) => item.id)).toEqual([UNLINKED_SHOT_ID]);
  expect(viewModel.orphans.scenes.map((item) => item.id)).toEqual([ORPHAN_SCENE_ID]);
  expect(viewModel.orphans.shots.map((item) => item.id)).toEqual([ORPHAN_SHOT_ID]);
});

test('keeps an outline-only Episode readable with unavailable later artifact sources', () => {
  const outline = narrative();
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...outline,
    scenes: [],
    shots: [],
    associations: {
      beatSceneCoverage: coverage(0, 0),
      sceneShotCoverage: coverage(0, 0),
      missingLinks: [],
      orphanArtifacts: [],
    },
  }, null));

  expect(viewModel.episode?.title).toBe('雨夜重逢');
  expect(viewModel.storyArc?.narrativeBeatIds).toEqual([BEAT_ID, EMPTY_BEAT_ID]);
  expect(viewModel.narrativeBeatsById[BEAT_ID].sourceArtifact).toBe('episode-outline.md');
  expect(viewModel.unlinked.scenes).toEqual([]);
  expect(viewModel.coverage.sceneShot.label).toBe('尚未生成');
  expect(viewModel.promptsByShotViewId).toEqual({});
  expect(viewModel.renderQueueByShotViewId).toEqual({});
});

test('preserves opaque hierarchy identity as script and storyboard arrive progressively', () => {
  const complete = narrative();
  const outlineOnly = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...complete,
    scenes: [],
    shots: [],
  }, null));
  const scriptAvailable = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...complete,
    shots: [],
  }, null));
  const storyboardAvailable = storyWorkspaceBuildEpisodeExecutionViewModel(surface(
    complete,
    null,
  ));

  expect([
    outlineOnly.episode?.id,
    scriptAvailable.episode?.id,
    storyboardAvailable.episode?.id,
  ]).toEqual([EPISODE_ID, EPISODE_ID, EPISODE_ID]);
  expect([
    outlineOnly.storyArc?.id,
    scriptAvailable.storyArc?.id,
    storyboardAvailable.storyArc?.id,
  ]).toEqual([ARC_ID, ARC_ID, ARC_ID]);
  expect([
    outlineOnly.narrativeBeatsById[BEAT_ID].id,
    scriptAvailable.narrativeBeatsById[BEAT_ID].id,
    storyboardAvailable.narrativeBeatsById[BEAT_ID].id,
  ]).toEqual([BEAT_ID, BEAT_ID, BEAT_ID]);
  expect(outlineOnly.scenesById[SCENE_ID]).toBeUndefined();
  expect(scriptAvailable.scenesById[SCENE_ID].id).toBe(SCENE_ID);
  expect(scriptAvailable.shotsById[SHOT_ID]).toBeUndefined();
  expect(storyboardAvailable.shotsById[SHOT_ID].id).toBe(SHOT_ID);
});

test('indexes prompts and render queue independently by explicit shotViewId', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());

  expect(viewModel.promptsByShotViewId[SHOT_ID].map((item) => item.id)).toEqual([
    PROMPT_ID,
  ]);
  expect(viewModel.renderQueueByShotViewId[SHOT_ID].map((item) => item.id)).toEqual([
    QUEUE_ID,
  ]);
  expect(viewModel.unlinked.prompts.map((item) => item.id)).toEqual([
    UNLINKED_PROMPT_ID,
  ]);
  expect(viewModel.unlinked.renderQueueEntries.map((item) => item.id)).toEqual([
    UNLINKED_QUEUE_ID,
  ]);
  expect(viewModel.orphans.prompts.map((item) => item.id)).toEqual([
    ORPHAN_PROMPT_ID,
  ]);
  expect(viewModel).not.toHaveProperty('promptRenderAssociations');
});

test('locates review targets only by explicit targetViewId', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());

  expect(viewModel.reviewTargetsByTargetViewId[SHOT_ID].map((item) => item.id)).toEqual([
    REVIEW_SHOT_ID,
  ]);
  expect(viewModel.unlinked.reviewTargets.map((item) => item.id)).toEqual([
    REVIEW_UNKNOWN_ID,
  ]);
  expect(viewModel.reviewTargetsByTargetViewId['S01-E01-SH01']).toBeUndefined();
});

test('renders zero-denominator association coverage as 尚未生成', () => {
  expect(storyWorkspaceEpisodeCoverageLabel(coverage(0, 0))).toBe('尚未生成');
  expect(storyWorkspaceEpisodeCoverageLabel(coverage(1, 2))).toBe('50%');

  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());
  expect(viewModel.coverage.beatScene.label).toBe('33%');
  expect(viewModel.coverage.shotPrompt.label).toBe('33%');
});

test('provides Episode default selection and pure expanded-tree keyboard adjacency', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());
  const items = storyWorkspaceEpisodeNavigationItems(
    viewModel,
    new Set([BEAT_ID, SCENE_ID]),
  );

  expect(storyWorkspaceEpisodeDefaultSelection(viewModel)).toEqual({
    kind: 'episode',
    id: EPISODE_ID,
  });
  expect(items.map((item) => item.id)).toEqual([
    EPISODE_ID,
    BEAT_ID,
    SCENE_ID,
    SHOT_ID,
    EMPTY_BEAT_ID,
  ]);
  expect(storyWorkspaceEpisodeNavigationNeighbors(items, SCENE_ID)).toEqual({
    previousId: BEAT_ID,
    nextId: SHOT_ID,
    parentId: BEAT_ID,
    firstChildId: SHOT_ID,
  });
  expect(storyWorkspaceEpisodeNavigationTarget(items, SCENE_ID, 'ArrowRight')).toBe(
    SHOT_ID,
  );
  expect(storyWorkspaceEpisodeNavigationTarget(items, SCENE_ID, 'ArrowLeft')).toBe(
    BEAT_ID,
  );
  expect(storyWorkspaceEpisodeNavigationTarget(items, SCENE_ID, 'ArrowDown')).toBe(
    SHOT_ID,
  );
  expect(storyWorkspaceEpisodeNavigationTarget(items, SCENE_ID, 'ArrowUp')).toBe(
    BEAT_ID,
  );
});

test('returns no selection or navigation nodes when the Episode projection is unavailable', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface(null, null));

  expect(viewModel.episode).toBeNull();
  expect(viewModel.storyArc).toBeNull();
  expect(storyWorkspaceEpisodeDefaultSelection(viewModel)).toBeNull();
  expect(storyWorkspaceEpisodeNavigationItems(viewModel, new Set())).toEqual([]);
});
