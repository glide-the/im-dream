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
  storyWorkspaceParseEpisodeArtifactSurface,
} from '../../../hooks/story-workspace/contracts';
import {
  STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
  STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
  storyWorkspaceBuildEpisodeExecutionViewModel,
  storyWorkspaceEpisodeCoverageLabel,
  storyWorkspaceEpisodeDefaultSelection,
  storyWorkspaceEpisodeNavigationAction,
  storyWorkspaceEpisodeNavigationItems,
  storyWorkspaceEpisodeNavigationNeighbors,
  storyWorkspaceEpisodeSelectionKey,
  storyWorkspaceReconcileEpisodeSelection,
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
const REVIEW_SHOT_SECTION_ID = opaqueId(18);
const REVIEW_UNKNOWN_SECTION_ID = opaqueId(19);
const REVIEW_SCENE_ID = opaqueId(20);
const REVIEW_BEAT_ID = opaqueId(21);
const REVIEW_ORPHAN_ID = opaqueId(22);
const REVIEW_SCENE_SECTION_ID = opaqueId(23);
const REVIEW_BEAT_SECTION_ID = opaqueId(24);
const REVIEW_ORPHAN_SECTION_ID = opaqueId(25);

const ARTIFACT_SPECS = [
  ['episode-outline.md', 'plan_episode', ['episode_overview', 'storyline_navigator', 'narrative_workbench']],
  ['script.md', 'write_script', ['narrative_workbench', 'shot_inspector']],
  ['storyboard.yaml', 'regenerate_storyboard', ['narrative_workbench', 'shot_inspector']],
  ['prompts/', 'generate_prompts', ['shot_inspector', 'prompt_view']],
  ['renders/', 'prepare_render_guide', ['shot_inspector', 'render_view']],
  ['review-report.md', 'review_full_chain', ['review_view', 'shot_inspector']],
] as const;

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
      sections: [
        {
          id: REVIEW_SHOT_SECTION_ID,
          level: 2,
          title: '镜头结论',
          text: '镜头关系明确。',
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_UNKNOWN_SECTION_ID,
          level: 2,
          title: '未定位结论',
          text: '尚未建立目标关系。',
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_SCENE_SECTION_ID,
          level: 2,
          title: '场景结论',
          text: '场景关系明确。',
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_BEAT_SECTION_ID,
          level: 2,
          title: '叙事点结论',
          text: '叙事点关系明确。',
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_ORPHAN_SECTION_ID,
          level: 2,
          title: '孤立结论',
          text: '没有显式目标。',
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
      ],
      targets: [
        {
          id: REVIEW_SHOT_ID,
          kind: 'shot',
          sourceKey: 'S01-E01-SH01',
          targetViewId: SHOT_ID,
          associationStatus: 'linked',
          sectionId: REVIEW_SHOT_SECTION_ID,
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_UNKNOWN_ID,
          kind: 'shot',
          sourceKey: 'S01-E01-SH01',
          targetViewId: null,
          associationStatus: 'unlinked',
          sectionId: REVIEW_UNKNOWN_SECTION_ID,
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_SCENE_ID,
          kind: 'script-scene',
          sourceKey: 'S01',
          targetViewId: SCENE_ID,
          associationStatus: 'linked',
          sectionId: REVIEW_SCENE_SECTION_ID,
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_BEAT_ID,
          kind: 'narrative-beat',
          sourceKey: 'SC-01',
          targetViewId: BEAT_ID,
          associationStatus: 'linked',
          sectionId: REVIEW_BEAT_SECTION_ID,
          sourceArtifact: 'review-report.md',
          sourceRevision: revision('1'),
        },
        {
          id: REVIEW_ORPHAN_ID,
          kind: 'shot',
          sourceKey: 'S01-E01-SH01',
          targetViewId: null,
          associationStatus: 'orphan',
          sectionId: REVIEW_ORPHAN_SECTION_ID,
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
  const available = new Set<string>();
  if (narrativeProjection?.overview.sourceArtifact !== null) {
    available.add('episode-outline.md');
  }
  if ((narrativeProjection?.scenes.length ?? 0) > 0) available.add('script.md');
  if ((narrativeProjection?.shots.length ?? 0) > 0) available.add('storyboard.yaml');
  if ((auxiliaryProjection?.prompts.items.length ?? 0) > 0) available.add('prompts/');
  if (auxiliaryProjection !== null && auxiliaryProjection.renderGuide !== null) {
    available.add('renders/');
  }
  if (auxiliaryProjection !== null && auxiliaryProjection.review !== null) {
    available.add('review-report.md');
  }
  const wireSurface = {
    runId: `run_${'2'.repeat(32)}`,
    opaqueEpisodeId: EPISODE_ID,
    manifestRevision: revision('2'),
    etag: revision('2'),
    bindingAvailability: 'bound',
    bindingRecovery: {
      autoRepairAttempted: false,
      canDispatch: true,
      publicReason: null,
    },
    artifacts: ARTIFACT_SPECS.map(([relativeKey, producerAction, consumers]) => ({
      relativeKey,
      availability: available.has(relativeKey) ? 'available' : 'not_generated',
      contentRevision: available.has(relativeKey) ? revision('3') : null,
      mtime: available.has(relativeKey) ? '2026-08-06T01:02:03Z' : null,
      size: available.has(relativeKey) ? 128 : null,
      producerAction,
      consumers: [...consumers],
    })),
    narrative: narrativeProjection,
    auxiliary: auxiliaryProjection === null
      ? null
      : { ...auxiliaryProjection, manifestRevision: revision('2') },
  };
  return storyWorkspaceParseEpisodeArtifactSurface(wireSurface);
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
  expect(viewModel.reviewTargetsByTargetViewId[SCENE_ID].map((item) => item.id)).toEqual([
    REVIEW_SCENE_ID,
  ]);
  expect(viewModel.reviewTargetsByTargetViewId[BEAT_ID].map((item) => item.id)).toEqual([
    REVIEW_BEAT_ID,
  ]);
  expect(viewModel.orphans.reviewTargets.map((item) => item.id)).toEqual([
    REVIEW_ORPHAN_ID,
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

test('returns explicit same-level, expand, child, collapse and parent keyboard actions', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());
  const items = storyWorkspaceEpisodeNavigationItems(
    viewModel,
    new Set([
      storyWorkspaceEpisodeSelectionKey({ kind: 'narrative-beat', id: BEAT_ID }),
      storyWorkspaceEpisodeSelectionKey({ kind: 'scene', id: SCENE_ID }),
    ]),
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
    STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
  ]);
  expect(storyWorkspaceEpisodeNavigationNeighbors(
    items,
    { kind: 'narrative-beat', id: BEAT_ID },
  )).toEqual({
    previousSibling: null,
    nextSibling: { kind: 'narrative-beat', id: EMPTY_BEAT_ID },
    parent: { kind: 'episode', id: EPISODE_ID },
    firstChild: { kind: 'scene', id: SCENE_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    items,
    { kind: 'narrative-beat', id: BEAT_ID },
    'ArrowDown',
  )).toEqual({
    action: 'move-sibling',
    target: { kind: 'narrative-beat', id: EMPTY_BEAT_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    items,
    { kind: 'narrative-beat', id: EMPTY_BEAT_ID },
    'ArrowUp',
  )).toEqual({
    action: 'move-sibling',
    target: { kind: 'narrative-beat', id: BEAT_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    items,
    { kind: 'scene', id: SCENE_ID },
    'ArrowRight',
  )).toEqual({
    action: 'move-first-child',
    target: { kind: 'shot', id: SHOT_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    items,
    { kind: 'scene', id: SCENE_ID },
    'ArrowLeft',
  )).toEqual({
    action: 'collapse',
    target: { kind: 'scene', id: SCENE_ID },
  });

  const collapsedItems = storyWorkspaceEpisodeNavigationItems(viewModel, new Set());
  expect(storyWorkspaceEpisodeNavigationAction(
    collapsedItems,
    { kind: 'narrative-beat', id: BEAT_ID },
    'ArrowRight',
  )).toEqual({
    action: 'expand',
    target: { kind: 'narrative-beat', id: BEAT_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    collapsedItems,
    { kind: 'narrative-beat', id: BEAT_ID },
    'ArrowLeft',
  )).toEqual({
    action: 'move-parent',
    target: { kind: 'episode', id: EPISODE_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    collapsedItems,
    { kind: 'narrative-beat', id: EMPTY_BEAT_ID },
    'ArrowRight',
  )).toEqual({ action: 'noop', target: null });
});

test('makes auxiliary groups and detached nodes keyboard reachable without canonical parents', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface());
  const items = storyWorkspaceEpisodeNavigationItems(viewModel, new Set([
    storyWorkspaceEpisodeSelectionKey({
      kind: 'auxiliary-group',
      id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    }),
    storyWorkspaceEpisodeSelectionKey({
      kind: 'auxiliary-group',
      id: STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
    }),
  ]));
  const unlinkedScene = items.find(
    (item) => item.kind === 'scene' && item.id === UNLINKED_SCENE_ID,
  );
  const orphanPrompt = items.find(
    (item) => item.kind === 'prompt' && item.id === ORPHAN_PROMPT_ID,
  );
  const unlinkedGroup = items.find(
    (item) => item.kind === 'auxiliary-group'
      && item.id === STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
  );
  const orphanGroup = items.find(
    (item) => item.kind === 'auxiliary-group'
      && item.id === STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
  );

  expect(unlinkedGroup?.children.map((selection) => selection.kind)).toEqual([
    'scene',
    'shot',
    'prompt',
    'render-queue',
    'review-target',
  ]);
  expect(orphanGroup?.children.map((selection) => selection.kind)).toEqual([
    'scene',
    'shot',
    'prompt',
    'review-target',
  ]);
  expect(unlinkedScene).toMatchObject({
    canonicalParent: null,
    navigationParent: {
      kind: 'auxiliary-group',
      id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    },
    auxiliaryGroup: 'unlinked',
  });
  expect(orphanPrompt).toMatchObject({
    canonicalParent: null,
    navigationParent: {
      kind: 'auxiliary-group',
      id: STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
    },
    auxiliaryGroup: 'orphan',
    sourceArtifact: 'prompts/orphan.yaml',
    sourceRevision: revision('e'),
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    items,
    {
      kind: 'auxiliary-group',
      id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    },
    'ArrowRight',
  )).toEqual({
    action: 'move-first-child',
    target: { kind: 'scene', id: UNLINKED_SCENE_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    items,
    { kind: 'scene', id: UNLINKED_SCENE_ID },
    'ArrowDown',
  )).toEqual({
    action: 'move-sibling',
    target: { kind: 'shot', id: UNLINKED_SHOT_ID },
  });
  expect(storyWorkspaceEpisodeNavigationAction(
    items,
    { kind: 'scene', id: UNLINKED_SCENE_ID },
    'ArrowLeft',
  )).toEqual({
    action: 'move-parent',
    target: {
      kind: 'auxiliary-group',
      id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    },
  });
});

test('reconciles {kind,id} selection across reorder and deterministic ancestor deletion', () => {
  const previousNarrative = narrative();
  const previous = storyWorkspaceBuildEpisodeExecutionViewModel(surface(
    previousNarrative,
    null,
  ));
  const reordered = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...previousNarrative,
    narrativeBeats: [...previousNarrative.narrativeBeats].reverse(),
    scenes: [...previousNarrative.scenes].reverse(),
    shots: [...previousNarrative.shots].reverse(),
  }, null));
  const shotSelection = { kind: 'shot' as const, id: SHOT_ID };

  expect(storyWorkspaceReconcileEpisodeSelection(
    shotSelection,
    previous,
    reordered,
  )).toEqual(shotSelection);

  const withoutShot = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...previousNarrative,
    shots: previousNarrative.shots.filter((shot) => shot.id !== SHOT_ID),
  }, null));
  expect(storyWorkspaceReconcileEpisodeSelection(
    shotSelection,
    previous,
    withoutShot,
  )).toEqual({ kind: 'scene', id: SCENE_ID });

  const withoutScene = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...previousNarrative,
    scenes: previousNarrative.scenes.filter((scene) => scene.id !== SCENE_ID),
    shots: previousNarrative.shots.filter((shot) => shot.scriptSceneId !== SCENE_ID),
  }, null));
  expect(storyWorkspaceReconcileEpisodeSelection(
    shotSelection,
    previous,
    withoutScene,
  )).toEqual({ kind: 'narrative-beat', id: BEAT_ID });
  expect(storyWorkspaceReconcileEpisodeSelection(
    { kind: 'scene', id: SCENE_ID },
    previous,
    withoutScene,
  )).toEqual({ kind: 'narrative-beat', id: BEAT_ID });

  const withoutBeat = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...previousNarrative,
    narrativeBeats: previousNarrative.narrativeBeats.filter(
      (beat) => beat.id !== BEAT_ID,
    ),
    scenes: previousNarrative.scenes.filter(
      (scene) => scene.narrativeBeatId !== BEAT_ID,
    ),
    shots: previousNarrative.shots.filter(
      (shot) => shot.narrativeBeatId !== BEAT_ID,
    ),
  }, null));
  expect(storyWorkspaceReconcileEpisodeSelection(
    shotSelection,
    previous,
    withoutBeat,
  )).toEqual({ kind: 'episode', id: EPISODE_ID });
  expect(storyWorkspaceReconcileEpisodeSelection(
    { kind: 'narrative-beat', id: BEAT_ID },
    previous,
    withoutBeat,
  )).toEqual({ kind: 'episode', id: EPISODE_ID });
});

test('falls back auxiliary selections through only explicit previous relation ancestors', () => {
  const previousNarrative = narrative();
  const previous = storyWorkspaceBuildEpisodeExecutionViewModel(surface(
    previousNarrative,
    auxiliary(),
  ));
  const intactCore = storyWorkspaceBuildEpisodeExecutionViewModel(surface(
    previousNarrative,
    null,
  ));
  const withoutShot = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...previousNarrative,
    shots: previousNarrative.shots.filter((shot) => shot.id !== SHOT_ID),
  }, null));
  const withoutScene = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...previousNarrative,
    scenes: previousNarrative.scenes.filter((scene) => scene.id !== SCENE_ID),
    shots: previousNarrative.shots.filter((shot) => shot.scriptSceneId !== SCENE_ID),
  }, null));
  const withoutBeat = storyWorkspaceBuildEpisodeExecutionViewModel(surface({
    ...previousNarrative,
    narrativeBeats: previousNarrative.narrativeBeats.filter(
      (beat) => beat.id !== BEAT_ID,
    ),
    scenes: previousNarrative.scenes.filter(
      (scene) => scene.narrativeBeatId !== BEAT_ID,
    ),
    shots: previousNarrative.shots.filter(
      (shot) => shot.narrativeBeatId !== BEAT_ID,
    ),
  }, null));
  const shotScopedSelections = [
    { label: 'prompt', selection: { kind: 'prompt' as const, id: PROMPT_ID } },
    { label: 'render', selection: { kind: 'render-queue' as const, id: QUEUE_ID } },
    {
      label: 'shot review',
      selection: { kind: 'review-target' as const, id: REVIEW_SHOT_ID },
    },
  ];
  const shotAncestorStages = [
    { label: 'shot exists', next: intactCore, expected: { kind: 'shot' as const, id: SHOT_ID } },
    { label: 'shot deleted', next: withoutShot, expected: { kind: 'scene' as const, id: SCENE_ID } },
    { label: 'scene deleted', next: withoutScene, expected: { kind: 'narrative-beat' as const, id: BEAT_ID } },
    { label: 'beat deleted', next: withoutBeat, expected: { kind: 'episode' as const, id: EPISODE_ID } },
  ];

  for (const source of shotScopedSelections) {
    for (const stage of shotAncestorStages) {
      expect(
        storyWorkspaceReconcileEpisodeSelection(
          source.selection,
          previous,
          stage.next,
        ),
        `${source.label}: ${stage.label}`,
      ).toEqual(stage.expected);
    }
  }

  const sceneReviewSelection = {
    kind: 'review-target' as const,
    id: REVIEW_SCENE_ID,
  };
  expect(storyWorkspaceReconcileEpisodeSelection(
    sceneReviewSelection,
    previous,
    intactCore,
  )).toEqual({ kind: 'scene', id: SCENE_ID });
  expect(storyWorkspaceReconcileEpisodeSelection(
    sceneReviewSelection,
    previous,
    withoutScene,
  )).toEqual({ kind: 'narrative-beat', id: BEAT_ID });
  expect(storyWorkspaceReconcileEpisodeSelection(
    sceneReviewSelection,
    previous,
    withoutBeat,
  )).toEqual({ kind: 'episode', id: EPISODE_ID });

  const beatReviewSelection = {
    kind: 'review-target' as const,
    id: REVIEW_BEAT_ID,
  };
  expect(storyWorkspaceReconcileEpisodeSelection(
    beatReviewSelection,
    previous,
    intactCore,
  )).toEqual({ kind: 'narrative-beat', id: BEAT_ID });
  expect(storyWorkspaceReconcileEpisodeSelection(
    beatReviewSelection,
    previous,
    withoutBeat,
  )).toEqual({ kind: 'episode', id: EPISODE_ID });

  expect(storyWorkspaceReconcileEpisodeSelection(
    { kind: 'review-target', id: REVIEW_ORPHAN_ID },
    previous,
    intactCore,
  )).toEqual({ kind: 'episode', id: EPISODE_ID });
  expect(storyWorkspaceReconcileEpisodeSelection(
    { kind: 'prompt', id: UNLINKED_PROMPT_ID },
    previous,
    intactCore,
  )).toEqual({ kind: 'episode', id: EPISODE_ID });
  expect(storyWorkspaceReconcileEpisodeSelection(
    { kind: 'render-queue', id: UNLINKED_QUEUE_ID },
    previous,
    intactCore,
  )).toEqual({ kind: 'episode', id: EPISODE_ID });
});

test('returns no selection or navigation nodes when the Episode projection is unavailable', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface(null, null));

  expect(viewModel.episode).toBeNull();
  expect(viewModel.storyArc).toBeNull();
  expect(storyWorkspaceEpisodeDefaultSelection(viewModel)).toBeNull();
  expect(storyWorkspaceEpisodeNavigationItems(viewModel, new Set())).toEqual([]);
});
