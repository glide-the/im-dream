// [Input] Episode execution view-model, selection and expansion facts.
// [Output] SSR semantic markup and pure keyboard interaction coverage for the narrative workbench.
// [Pos] Story Workspace Episode narrative workbench Node seam (Task 3 U7).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { fileURLToPath } from 'node:url';
import { createElement, type ComponentProps } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import type { StoryWorkspaceEpisodeArtifactSurface } from '../../../../hooks/story-workspace/contracts';
import {
  STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
  STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
  storyWorkspaceBuildEpisodeExecutionViewModel,
  storyWorkspaceEpisodeNavigationItems,
  storyWorkspaceEpisodeSelectionKey,
  type StoryWorkspaceEpisodeSelection,
} from '../../../../pages/story-workspace/episodeExecutionViewModel';
import {
  StoryWorkspaceEpisodeNarrativeWorkbench,
  storyWorkspaceHandleEpisodeNarrativeKey,
  storyWorkspaceSelectEpisodeNarrativeItem,
} from '../StoryWorkspaceEpisodeNarrativeWorkbench';

const SOURCE = readFileSync(
  new URL('../StoryWorkspaceEpisodeNarrativeWorkbench.tsx', import.meta.url),
  'utf8',
);
const opaqueId = (value: number) => value.toString(16).padStart(32, '0');
const EPISODE_ID = opaqueId(1);
const ARC_ID = opaqueId(2);
const BEAT_ID = opaqueId(3);
const SECOND_BEAT_ID = opaqueId(4);
const SCENE_ID = opaqueId(5);
const UNLINKED_SCENE_ID = opaqueId(6);
const ORPHAN_SCENE_ID = opaqueId(7);
const SHOT_ID = opaqueId(8);
const UNLINKED_SHOT_ID = opaqueId(9);
const ORPHAN_SHOT_ID = opaqueId(10);
const CHARACTER_BEAT_ID = opaqueId(11);
const UNLINKED_PROMPT_ID = opaqueId(12);
const ORPHAN_PROMPT_ID = opaqueId(13);
const UNLINKED_QUEUE_ID = opaqueId(14);
const ORPHAN_QUEUE_ID = opaqueId(15);
const UNLINKED_REVIEW_ID = opaqueId(16);
const ORPHAN_REVIEW_ID = opaqueId(17);
const UNLINKED_REVIEW_SECTION_ID = opaqueId(18);
const ORPHAN_REVIEW_SECTION_ID = opaqueId(19);

function coverage(linked: number, total: number) {
  return total === 0
    ? { availability: 'unavailable' as const, linked: 0, total: 0, ratio: null }
    : { availability: 'available' as const, linked, total, ratio: linked / total };
}

function surface(stage: 'outline' | 'script' | 'storyboard'): StoryWorkspaceEpisodeArtifactSurface {
  const hasScript = stage !== 'outline';
  const hasStoryboard = stage === 'storyboard';
  return {
    runId: `run_${'1'.repeat(32)}`,
    opaqueEpisodeId: EPISODE_ID,
    manifestRevision: `sha256:${'a'.repeat(64)}`,
    etag: `sha256:${'a'.repeat(64)}`,
    bindingAvailability: 'bound',
    bindingRecovery: {
      autoRepairAttempted: false,
      canDispatch: true,
      publicReason: null,
    },
    artifacts: [],
    narrative: {
      episodeId: EPISODE_ID,
      storyArcId: ARC_ID,
      overview: {
        title: '雨夜重逢',
        series: '归途',
        storyGoals: ['让林默决定留下'],
        coreConflict: '留下还是离开',
        hook: '旧友出现在雨幕中',
        sourceArtifact: 'episode-outline.md',
        sourceRevision: 'outline-r1',
        generatedFrom: null,
        characterBeats: [{
          id: CHARACTER_BEAT_ID,
          sourceKey: 'lin-mo-choice',
          characterId: 'lin-mo',
          action: '留下',
          startState: '执意离开',
          trigger: '旧友出现',
          choice: '停下脚步',
          endState: '决定面对过去',
          visibleEvidence: '林默放下车票。',
        }],
      },
      narrativeBeats: [
        {
          id: BEAT_ID,
          sourceKey: 'SC-01',
          title: '失去控制',
          assetSceneRef: null,
          narrativeFunction: '触发主角的选择',
          emotionTone: '紧张',
          summary: '林默在站台停下脚步。',
          sceneGoals: ['暴露犹豫', '引出旧友'],
          keyDialogueBeats: ['你还是来了。'],
          sourceArtifact: 'episode-outline.md',
          sourceRevision: 'outline-r1',
          generatedFrom: null,
        },
        {
          id: SECOND_BEAT_ID,
          sourceKey: 'SC-02',
          title: '做出选择',
          assetSceneRef: null,
          narrativeFunction: null,
          emotionTone: null,
          summary: null,
          sceneGoals: [],
          keyDialogueBeats: [],
          sourceArtifact: 'episode-outline.md',
          sourceRevision: 'outline-r1',
          generatedFrom: null,
        },
      ],
      scenes: hasScript ? [
        {
          id: SCENE_ID,
          sourceKey: 'S01',
          title: '雨夜站台',
          heading: 'EXT. 旧车站站台 - 夜',
          assetSceneRef: null,
          narrativeBeatId: BEAT_ID,
          declaredNarrativeBeatRef: 'SC-01',
          associationStatus: 'linked',
          actions: ['林默停住脚步。', '苏遥从雨幕中走来。'],
          dialogue: [{ speaker: '苏遥', qualifier: '低声', text: '你还是来了。' }],
          cameraCues: ['雨声压住广播。'],
          sourceArtifact: 'script.md',
          sourceRevision: 'script-r2',
          generatedFrom: null,
        },
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
          sourceRevision: 'script-r2',
          generatedFrom: null,
        },
        {
          id: ORPHAN_SCENE_ID,
          sourceKey: 'S03',
          title: '孤立场景',
          heading: 'EXT. 侧门 - 夜',
          assetSceneRef: null,
          narrativeBeatId: null,
          declaredNarrativeBeatRef: 'SC-99',
          associationStatus: 'orphan',
          actions: [],
          dialogue: [],
          cameraCues: [],
          sourceArtifact: 'script.md',
          sourceRevision: 'script-r2',
          generatedFrom: null,
        },
      ] : [],
      shots: hasStoryboard ? [
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
          characters: [{
            ref: 'lin-mo',
            displayName: '林默',
            depthPlane: 'front',
            action: '停步',
            emotion: '犹豫',
          }],
          camera: {
            angle: 'eye-level',
            height: 'shoulder',
            movement: 'slow-push',
            lens: '50mm',
          },
          visual: '雨夜站台建立镜头。',
          dialogue: [{ speaker: '苏遥', line: '你还是来了。', type: 'spoken' }],
          timing: { durationSec: 3, transitionIn: 'cut', transitionOut: 'hold' },
          sourceArtifact: 'storyboard.yaml',
          sourceRevision: 'storyboard-r3',
          generatedFrom: 'script@r2',
        },
        {
          id: UNLINKED_SHOT_ID,
          shotId: 'SUP-E01-01',
          assetSceneRef: null,
          declaredScriptSceneRef: null,
          declaredNarrativeBeatRef: null,
          scriptSceneId: null,
          narrativeBeatId: null,
          associationStatus: 'unlinked',
          shotType: null,
          characters: [],
          camera: { angle: null, height: null, movement: null, lens: null },
          visual: null,
          dialogue: [],
          timing: { durationSec: null, transitionIn: null, transitionOut: null },
          sourceArtifact: 'storyboard.yaml',
          sourceRevision: 'storyboard-r3',
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
          sourceRevision: 'storyboard-r3',
          generatedFrom: null,
        },
      ] : [],
      associations: {
        beatSceneCoverage: coverage(hasScript ? 1 : 0, hasScript ? 3 : 0),
        sceneShotCoverage: coverage(hasStoryboard ? 1 : 0, hasStoryboard ? 3 : 0),
        missingLinks: [],
        orphanArtifacts: [],
      },
    },
    auxiliary: null,
    workflow: {
      factsRevision: 0,
      nextAction: {
        action: stage === 'outline'
          ? 'write_script'
          : stage === 'script'
            ? 'review_script'
            : 'generate_prompts',
        diagnostic: 'ready',
        canDispatch: true,
      },
      prerequisites: [],
      legacyPartial: false,
    },
  };
}

function surfaceWithAuxiliary(): StoryWorkspaceEpisodeArtifactSurface {
  return {
    ...surface('storyboard'),
    auxiliary: {
      manifestRevision: 'aux-r1',
      prompts: {
        total: 2,
        nextCursor: null,
        items: [
          {
            id: UNLINKED_PROMPT_ID,
            shotId: 'SUP-E01-01',
            kind: 'image',
            shotViewId: null,
            associationStatus: 'unlinked',
            positive: '雨水特写',
            negative: null,
            parameters: {
              model: null,
              mode: null,
              durationSec: null,
              motionStrength: null,
              cameraMotion: null,
              aspectRatio: null,
            },
            generability: {
              characterAnchor: null,
              motionFeasibility: null,
              durationBudget: null,
              notes: null,
            },
            sourceArtifact: 'prompts/unlinked.yaml',
            sourceRevision: 'prompt-r1',
          },
          {
            id: ORPHAN_PROMPT_ID,
            shotId: 'S99-E01-SH01',
            kind: 'video',
            shotViewId: null,
            associationStatus: 'orphan',
            positive: '未知侧门',
            negative: null,
            parameters: {
              model: null,
              mode: null,
              durationSec: null,
              motionStrength: null,
              cameraMotion: null,
              aspectRatio: null,
            },
            generability: {
              characterAnchor: null,
              motionFeasibility: null,
              durationBudget: null,
              notes: null,
            },
            sourceArtifact: 'prompts/orphan.yaml',
            sourceRevision: 'prompt-r1',
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
              id: UNLINKED_QUEUE_ID,
              shotId: 'SUP-E01-01',
              shotViewId: null,
              associationStatus: 'unlinked',
              durationSec: null,
              risk: null,
              priority: null,
              renderer: null,
              status: 'pending',
              sourceArtifact: 'renders/render-guide.md',
              sourceRevision: 'render-r1',
            },
            {
              id: ORPHAN_QUEUE_ID,
              shotId: 'S99-E01-SH01',
              shotViewId: null,
              associationStatus: 'orphan',
              durationSec: null,
              risk: null,
              priority: null,
              renderer: null,
              status: 'pending',
              sourceArtifact: 'renders/render-guide.md',
              sourceRevision: 'render-r1',
            },
          ],
        },
        sourceArtifact: 'renders/render-guide.md',
        sourceRevision: 'render-r1',
      },
      review: {
        scope: 'full-chain',
        overallVerdict: null,
        reviewedArtifacts: [],
        sourceRevisions: [],
        sections: [
          {
            id: UNLINKED_REVIEW_SECTION_ID,
            level: 2,
            title: '未关联审阅',
            text: '没有定位目标。',
            sourceArtifact: 'review-report.md',
            sourceRevision: 'review-r1',
          },
          {
            id: ORPHAN_REVIEW_SECTION_ID,
            level: 2,
            title: '孤立审阅',
            text: '引用目标不存在。',
            sourceArtifact: 'review-report.md',
            sourceRevision: 'review-r1',
          },
        ],
        targets: [
          {
            id: UNLINKED_REVIEW_ID,
            kind: 'shot',
            sourceKey: 'SUP-E01-01',
            targetViewId: null,
            associationStatus: 'unlinked',
            sectionId: UNLINKED_REVIEW_SECTION_ID,
            sourceArtifact: 'review-report.md',
            sourceRevision: 'review-r1',
          },
          {
            id: ORPHAN_REVIEW_ID,
            kind: 'shot',
            sourceKey: 'S99-E01-SH01',
            targetViewId: null,
            associationStatus: 'orphan',
            sectionId: ORPHAN_REVIEW_SECTION_ID,
            sourceArtifact: 'review-report.md',
            sourceRevision: 'review-r1',
          },
        ],
        sourceArtifact: 'review-report.md',
        sourceRevision: 'review-r1',
      },
      associations: {
        shotPromptCoverage: coverage(0, 3),
        shotRenderQueueCoverage: coverage(0, 3),
        totalPrompts: 2,
        totalQueueEntries: 2,
        orphanPrompts: [ORPHAN_PROMPT_ID],
        orphanQueueEntries: [ORPHAN_QUEUE_ID],
        duplicateQueueShotIds: [],
      },
    },
  };
}

const noOp = () => undefined;

function renderWorkbench(
  props: ComponentProps<typeof StoryWorkspaceEpisodeNarrativeWorkbench>,
): string {
  return renderToStaticMarkup(createElement(
    StoryWorkspaceEpisodeNarrativeWorkbench,
    props,
  ));
}

test('renders an outline-only Episode with one semantic tree and honest pending stages', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface('outline'));
  const html = renderWorkbench({
    viewModel,
    selection: { kind: 'episode', id: EPISODE_ID },
    expandedKeys: new Set(),
    episodeOverview: surface('outline').narrative?.overview,
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });

  expect(html).toContain('role="tree"');
  expect(html).toContain('雨夜重逢');
  expect(html).toContain('让林默决定留下');
  expect(html).toContain('留下还是离开');
  expect(html).toContain('旧友出现在雨幕中');
  expect(html).toContain('归途');
  expect(html).toContain('人物弧光');
  expect(html).toContain('执意离开');
  expect(html).toContain('林默放下车票。');
  expect(html).toContain('场景尚未生成');
  expect(html).toContain('镜头尚未生成');
  expect(html.match(/tabindex="0"/g)).toHaveLength(1);
  expect(html).toContain('aria-current="true"');
});

test('renders Beat and Scene narrative content from their owning artifacts', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface('script'));
  const beatHtml = renderWorkbench({
    viewModel,
    selection: { kind: 'narrative-beat', id: BEAT_ID },
    expandedKeys: new Set([storyWorkspaceEpisodeSelectionKey({
        kind: 'narrative-beat', id: BEAT_ID,
      })]),
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });
  const sceneHtml = renderWorkbench({
    viewModel,
    selection: { kind: 'scene', id: SCENE_ID },
    expandedKeys: new Set([storyWorkspaceEpisodeSelectionKey({
        kind: 'narrative-beat', id: BEAT_ID,
      })]),
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });

  expect(beatHtml).toContain('触发主角的选择');
  expect(beatHtml).toContain('情绪基调');
  expect(beatHtml).toContain('紧张');
  expect(beatHtml).toContain('林默在站台停下脚步。');
  expect(beatHtml).toContain('暴露犹豫');
  expect(sceneHtml).toContain('雨夜站台');
  expect(sceneHtml).toContain('EXT. 旧车站站台 - 夜');
  expect(sceneHtml).toContain('苏遥从雨幕中走来。');
  expect(sceneHtml).toContain('苏遥');
  expect(sceneHtml).toContain('你还是来了。');
  expect(sceneHtml).toContain('镜头提示');
  expect(sceneHtml).toContain('雨声压住广播。');
  expect(sceneHtml).toContain('来源：script.md');
  expect(sceneHtml).toContain('Revision：script-r2');
});

test('renders Shot detail and logical provenance without implementation paths', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface('storyboard'));
  const expandedKeys = new Set([
    storyWorkspaceEpisodeSelectionKey({ kind: 'narrative-beat', id: BEAT_ID }),
    storyWorkspaceEpisodeSelectionKey({ kind: 'scene', id: SCENE_ID }),
  ]);
  const html = renderWorkbench({
    viewModel,
    selection: { kind: 'shot', id: SHOT_ID },
    expandedKeys,
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
    auxiliarySlot: createElement('p', null, '辅助占位'),
  });

  for (const expected of [
    'S01-E01-SH01',
    '雨夜站台建立镜头。',
    'eye-level',
    'slow-push',
    '50mm',
    '3 秒',
    '林默',
    '犹豫',
    '你还是来了。',
    'spoken',
    '雨夜重逢 / SC-01 / S01 / S01-E01-SH01',
    '返回场景：雨夜站台',
    '剧本上下文',
    'EXT. 旧车站站台 - 夜',
    '林默停住脚步。',
    '来源：script.md script-r2 · storyboard.yaml storyboard-r3',
    '关联：script_scene_ref → S01 · narrative_beat_ref → SC-01 · shot_id → S01-E01-SH01',
    '辅助占位',
  ]) expect(html).toContain(expected);
  expect(html).not.toContain('/Users/');
  expect(html).not.toContain('script@r2');
});

test('renders reachable unlinked and orphan groups with explicit accessible levels', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface('storyboard'));
  const expandedKeys = new Set([
    storyWorkspaceEpisodeSelectionKey({
      kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    }),
    storyWorkspaceEpisodeSelectionKey({
      kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
    }),
  ]);
  const html = renderWorkbench({
    viewModel,
    selection: {
        kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
      },
    expandedKeys,
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });

  expect(html).toContain('尚未关联');
  expect(html).toContain('孤立引用');
  expect(html).toContain('aria-expanded="true"');
  expect(html).toContain('aria-level="2"');
  expect(html).toContain('候车室');
  expect(html).toContain('SUP-E01-01');
  expect(html).toContain('孤立场景');
  expect(html).toContain('S99-E01-SH01');

  const unlinkedHtml = renderWorkbench({
    viewModel,
    selection: {
      kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    },
    expandedKeys,
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });
  const orphanHtml = renderWorkbench({
    viewModel,
    selection: {
      kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
    },
    expandedKeys,
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });
  expect(unlinkedHtml).toContain('没有声明可验证的上游引用');
  expect(unlinkedHtml).not.toContain('目标不存在或不一致');
  expect(orphanHtml).toContain('目标不存在或不一致');
  expect(orphanHtml).not.toContain('没有声明可验证的上游引用');
});

test('uses one resolved active selection for tree state and narrative content', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface('storyboard'));
  const html = renderWorkbench({
    viewModel,
    selection: { kind: 'shot', id: opaqueId(999) },
    expandedKeys: new Set(),
    episodeOverview: surface('storyboard').narrative?.overview,
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });

  expect(html).toContain('aria-label="Episode Overview"');
  expect(html).toContain('<h2>雨夜重逢</h2>');
  expect(html).not.toContain('aria-label="辅助选择"');
  expect(html.match(/aria-current="true"/g)).toHaveLength(1);
  expect(html.match(/tabindex="0"/g)).toHaveLength(1);
});

test('preserves orphan and unlinked semantics for Prompt, Render and Review children', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surfaceWithAuxiliary());
  const expandedKeys = new Set([
    storyWorkspaceEpisodeSelectionKey({
      kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    }),
    storyWorkspaceEpisodeSelectionKey({
      kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID,
    }),
  ]);
  const navigationHtml = renderWorkbench({
    viewModel,
    selection: {
      kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
    },
    expandedKeys,
    onSelection: noOp,
    onExpanded: noOp,
    onEscape: noOp,
  });

  for (const expected of [
    'Prompt · 尚未关联',
    'Prompt · 孤立引用',
    'Render Queue · 尚未关联',
    'Render Queue · 孤立引用',
    'Review · 尚未关联',
    'Review · 孤立引用',
  ]) expect(navigationHtml).toContain(expected);

  const detailCases: ReadonlyArray<readonly [StoryWorkspaceEpisodeSelection, string]> = [
    [{ kind: 'prompt', id: UNLINKED_PROMPT_ID }, 'Prompt · 尚未关联'],
    [{ kind: 'prompt', id: ORPHAN_PROMPT_ID }, 'Prompt · 孤立引用'],
    [{ kind: 'render-queue', id: UNLINKED_QUEUE_ID }, 'Render Queue · 尚未关联'],
    [{ kind: 'render-queue', id: ORPHAN_QUEUE_ID }, 'Render Queue · 孤立引用'],
    [{ kind: 'review-target', id: UNLINKED_REVIEW_ID }, 'Review · 尚未关联'],
    [{ kind: 'review-target', id: ORPHAN_REVIEW_ID }, 'Review · 孤立引用'],
  ];
  for (const [selection, heading] of detailCases) {
    const html = renderWorkbench({
      viewModel,
      selection,
      expandedKeys,
      onSelection: noOp,
      onExpanded: noOp,
      onEscape: noOp,
    });
    expect(html).toContain(`<h2>${heading}</h2>`);
  }
});

test('keyboard seam delegates U6 actions and uses explicit Escape callback', () => {
  const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface('storyboard'));
  const beatSelection = { kind: 'narrative-beat' as const, id: BEAT_ID };
  const sceneSelection = { kind: 'scene' as const, id: SCENE_ID };
  const selections: StoryWorkspaceEpisodeSelection[] = [];
  const expansions: Array<[StoryWorkspaceEpisodeSelection, boolean]> = [];
  const escapes: StoryWorkspaceEpisodeSelection[] = [];
  const callbacks = {
    onSelection: (selection: StoryWorkspaceEpisodeSelection) => selections.push(selection),
    onExpanded: (selection: StoryWorkspaceEpisodeSelection, expanded: boolean) => {
      expansions.push([selection, expanded]);
    },
    onEscape: (selection: StoryWorkspaceEpisodeSelection) => escapes.push(selection),
  };
  const collapsed = storyWorkspaceEpisodeNavigationItems(viewModel, new Set());
  const beatExpanded = storyWorkspaceEpisodeNavigationItems(viewModel, new Set([
    storyWorkspaceEpisodeSelectionKey(beatSelection),
  ]));
  const sceneExpanded = storyWorkspaceEpisodeNavigationItems(viewModel, new Set([
    storyWorkspaceEpisodeSelectionKey(beatSelection),
    storyWorkspaceEpisodeSelectionKey(sceneSelection),
  ]));

  expect(storyWorkspaceHandleEpisodeNarrativeKey({
    key: 'ArrowRight', items: collapsed, selection: beatSelection, ...callbacks,
  })).toBe(true);
  expect(expansions.at(-1)).toEqual([beatSelection, true]);
  storyWorkspaceHandleEpisodeNarrativeKey({
    key: 'ArrowRight', items: beatExpanded, selection: beatSelection, ...callbacks,
  });
  expect(selections.at(-1)).toEqual(sceneSelection);
  storyWorkspaceHandleEpisodeNarrativeKey({
    key: 'ArrowDown', items: beatExpanded, selection: beatSelection, ...callbacks,
  });
  expect(selections.at(-1)).toEqual({ kind: 'narrative-beat', id: SECOND_BEAT_ID });
  storyWorkspaceHandleEpisodeNarrativeKey({
    key: 'ArrowLeft', items: sceneExpanded, selection: sceneSelection, ...callbacks,
  });
  expect(expansions.at(-1)).toEqual([sceneSelection, false]);
  storyWorkspaceHandleEpisodeNarrativeKey({
    key: 'ArrowLeft', items: beatExpanded, selection: sceneSelection, ...callbacks,
  });
  expect(selections.at(-1)).toEqual(beatSelection);
  storyWorkspaceHandleEpisodeNarrativeKey({
    key: 'Enter', items: beatExpanded, selection: sceneSelection, ...callbacks,
  });
  expect(selections.at(-1)).toEqual(sceneSelection);
  storyWorkspaceHandleEpisodeNarrativeKey({
    key: 'Escape', items: sceneExpanded, selection: { kind: 'shot', id: SHOT_ID },
    ...callbacks,
  });
  expect(escapes).toEqual([{ kind: 'shot', id: SHOT_ID }]);
});

test('selection seam notifies auxiliary owners without treating narrative nodes as auxiliary', () => {
  const selected: StoryWorkspaceEpisodeSelection[] = [];
  const auxiliary: StoryWorkspaceEpisodeSelection[] = [];
  const select = (selection: StoryWorkspaceEpisodeSelection) => selected.push(selection);
  const selectAuxiliary = (selection: StoryWorkspaceEpisodeSelection) => {
    auxiliary.push(selection);
  };

  storyWorkspaceSelectEpisodeNarrativeItem(
    { kind: 'scene', id: SCENE_ID },
    select,
    selectAuxiliary,
  );
  storyWorkspaceSelectEpisodeNarrativeItem(
    { kind: 'auxiliary-group', id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID },
    select,
    selectAuxiliary,
  );

  expect(selected).toHaveLength(2);
  expect(auxiliary).toEqual([{
    kind: 'auxiliary-group',
    id: STORY_WORKSPACE_EPISODE_UNLINKED_GROUP_ID,
  }]);
});

test('source boundary contains no generic conversation, persistence or styling dependency', () => {
  for (const forbidden of [
    'ChatView',
    'ChatWidgetUI',
    'localStorage',
    'sessionStorage',
    'agent.snapshot',
    "import './StoryWorkspaceEpisodeNarrativeWorkbench.css'",
  ]) expect(SOURCE).not.toContain(forbidden);
  expect(SOURCE).toContain('event.preventDefault()');
  expect(SOURCE).toContain('auxiliarySlot');
  expect(SOURCE).toContain('onAuxiliarySelection');
});

test('keeps real DOM focus stable across navigation, controlled transitions and Escape', async ({ page }) => {
  const browserSurface = JSON.stringify(surface('storyboard'));
  const harnessModule = `
    import React, { useState } from 'react';
    import { createRoot } from 'react-dom/client';
    import { StoryWorkspaceEpisodeNarrativeWorkbench } from '/src/components/story-workspace/episode/StoryWorkspaceEpisodeNarrativeWorkbench.tsx';
    import { storyWorkspaceBuildEpisodeExecutionViewModel, storyWorkspaceEpisodeSelectionKey } from '/src/pages/story-workspace/episodeExecutionViewModel.ts';

    const surface = ${browserSurface};
    const viewModel = storyWorkspaceBuildEpisodeExecutionViewModel(surface);

    function Harness() {
      const [selection, setSelection] = useState({ kind: 'episode', id: '${EPISODE_ID}' });
      const [expandedKeys, setExpandedKeys] = useState(new Set());
      const [escapeCount, setEscapeCount] = useState(0);
      const [deferSelection, setDeferSelection] = useState(false);
      const onExpanded = (target, expanded) => {
        setExpandedKeys((current) => {
          const next = new Set(current);
          const key = storyWorkspaceEpisodeSelectionKey(target);
          if (expanded) next.add(key);
          else next.delete(key);
          return next;
        });
      };
      return React.createElement(
        React.Fragment,
        null,
        React.createElement('button', { id: 'outside-focus', type: 'button' }, '外部焦点'),
        React.createElement('button', {
          id: 'external-episode',
          type: 'button',
          onClick: () => setSelection({ kind: 'episode', id: '${EPISODE_ID}' }),
        }, '外部选择 Episode'),
        React.createElement('button', {
          id: 'external-beat',
          type: 'button',
          onClick: () => setSelection({ kind: 'narrative-beat', id: '${BEAT_ID}' }),
        }, '外部选择 Beat'),
        React.createElement('button', {
          id: 'external-orphan-group',
          type: 'button',
          onClick: () => setSelection({
            kind: 'auxiliary-group',
            id: '${STORY_WORKSPACE_EPISODE_ORPHAN_GROUP_ID}',
          }),
        }, '外部选择孤立引用'),
        React.createElement('button', {
          id: 'defer-selection',
          type: 'button',
          onClick: () => setDeferSelection(true),
        }, '暂缓受控选择'),
        React.createElement('button', {
          id: 'resume-selection',
          type: 'button',
          onClick: () => setDeferSelection(false),
        }, '恢复受控选择'),
        React.createElement(
          'output',
          { id: 'selection-mode' },
          deferSelection ? 'deferred' : 'immediate',
        ),
        React.createElement('output', { id: 'escape-count' }, String(escapeCount)),
        React.createElement(StoryWorkspaceEpisodeNarrativeWorkbench, {
          viewModel,
          selection,
          expandedKeys,
          episodeOverview: surface.narrative.overview,
          onSelection: deferSelection ? () => undefined : setSelection,
          onExpanded,
          onEscape: () => setEscapeCount((count) => count + 1),
        }),
      );
    }

    createRoot(document.querySelector('#root')).render(React.createElement(Harness));
  `;
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../../', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { host: '127.0.0.1', port: 0, strictPort: true },
    plugins: [{
      name: 'u7-episode-narrative-browser-harness',
      configureServer(vite) {
        vite.middlewares.use(async (request, response, next) => {
          const requestUrl = (request as unknown as { readonly url?: string }).url;
          if (requestUrl !== '/u7-episode-narrative-focus') return next();
          try {
            const html = await vite.transformIndexHtml(requestUrl, `
              <!doctype html><html><body><div id="root"></div>
              <script type="module" src="/u7-harness.js"></script></body></html>
            `);
            response.statusCode = 200;
            response.setHeader('Content-Type', 'text/html; charset=utf-8');
            response.end(html);
          } catch (error) {
            next(error as Error);
          }
        });
      },
      resolveId(id) {
        return id === '/u7-harness.js' ? '\0u7-harness.js' : null;
      },
      load(id) {
        return id === '\0u7-harness.js' ? harnessModule : null;
      },
    }],
  });
  const diagnostics: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(message.text());
  });
  page.on('pageerror', (error) => diagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    diagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
  });

  const activeTreeItem = page.locator('[role="treeitem"][tabindex="0"]');
  const expectFocused = async (label: string) => {
    await expect(activeTreeItem).toContainText(label);
    await expect.poll(() => page.evaluate(() => document.activeElement?.textContent ?? ''))
      .toContain(label);
    await expect(activeTreeItem).toHaveAttribute('aria-current', 'true');
  };

  try {
    await server.listen();
    const address = server.httpServer?.address();
    if (address === null || address === undefined || typeof address === 'string') {
      throw new Error('Ephemeral Vite server did not expose a TCP address.');
    }
    await page.goto(`http://127.0.0.1:${address.port}/u7-episode-narrative-focus`);
    await expect(activeTreeItem).toContainText('雨夜重逢');
    await activeTreeItem.focus();

    const outsideFocus = page.locator('#outside-focus');
    const externalSelect = async (id: string) => {
      await page.locator(id).evaluate((element: HTMLButtonElement) => element.click());
    };
    for (const key of ['Enter', 'Space', 'Home']) {
      await activeTreeItem.focus();
      await page.keyboard.press(key);
      await outsideFocus.focus();
      await externalSelect('#external-beat');
      await expect(activeTreeItem).toContainText('SC-01');
      await externalSelect('#external-episode');
      await expect(activeTreeItem).toContainText('雨夜重逢');
      await expect.soft.poll(() => page.evaluate(() => document.activeElement?.id ?? ''), {
        timeout: 500,
      }).toBe('outside-focus');
    }
    await externalSelect('#defer-selection');
    await expect(page.locator('#selection-mode')).toHaveText('deferred');
    await activeTreeItem.focus();
    await page.keyboard.press('ArrowRight');
    await expect(activeTreeItem).toContainText('雨夜重逢');
    await outsideFocus.focus();
    await externalSelect('#external-orphan-group');
    await expect(activeTreeItem).toContainText('孤立引用');
    await externalSelect('#external-beat');
    await expect(activeTreeItem).toContainText('SC-01');
    await expect.poll(() => page.evaluate(() => document.activeElement?.id ?? ''), {
      timeout: 500,
    }).toBe('outside-focus');
    await externalSelect('#external-episode');
    await externalSelect('#resume-selection');
    await expect(page.locator('#selection-mode')).toHaveText('immediate');
    await expect(activeTreeItem).toContainText('雨夜重逢');
    await activeTreeItem.focus();
    await page.keyboard.press('End');
    await expectFocused('孤立引用');
    await page.keyboard.press('End');
    await outsideFocus.focus();
    await externalSelect('#external-episode');
    await expect(activeTreeItem).toContainText('雨夜重逢');
    await externalSelect('#external-orphan-group');
    await expect(activeTreeItem).toContainText('孤立引用');
    await expect.soft.poll(() => page.evaluate(() => document.activeElement?.id ?? ''), {
      timeout: 500,
    }).toBe('outside-focus');
    await externalSelect('#external-episode');
    await expect(activeTreeItem).toContainText('雨夜重逢');
    await activeTreeItem.focus();

    await page.keyboard.press('ArrowRight');
    await expectFocused('SC-01');
    await page.keyboard.press('ArrowDown');
    await expectFocused('SC-02');
    await page.keyboard.press('ArrowUp');
    await expectFocused('SC-01');
    await page.keyboard.press('End');
    await expectFocused('孤立引用');
    await page.keyboard.press('Home');
    await expectFocused('雨夜重逢');
    await page.keyboard.press('ArrowRight');
    await expectFocused('SC-01');
    await page.keyboard.press('ArrowRight');
    await expectFocused('SC-01');
    await page.keyboard.press('ArrowRight');
    await expectFocused('S01');
    await page.keyboard.press('ArrowRight');
    await expectFocused('S01');
    await page.keyboard.press('ArrowRight');
    await expectFocused('S01-E01-SH01');
    await expect(page.getByRole('article', { name: 'Shot Detail' })).toBeVisible();

    const escapeCount = () => page.locator('#escape-count').textContent();
    const expectShotFocus = async () => {
      await expect.soft.poll(() => page.evaluate(() => document.activeElement?.textContent ?? ''), {
        timeout: 500,
      }).toContain('S01-E01-SH01');
    };
    const returnScene = page.getByRole('button', { name: '返回场景：雨夜站台' });
    await returnScene.focus();
    await page.keyboard.press('Escape');
    await expect.soft.poll(escapeCount, { timeout: 500 }).toBe('1');
    await expectShotFocus();

    await outsideFocus.focus();
    await page.getByRole('article', { name: 'Shot Detail' }).dispatchEvent('keydown', {
      key: 'Escape',
      code: 'Escape',
      bubbles: true,
    });
    await expect.soft.poll(escapeCount, { timeout: 500 }).toBe('2');
    await expectShotFocus();

    await outsideFocus.focus();
    await page.getByRole('region', { name: '叙事内容工作面' }).dispatchEvent('keydown', {
      key: 'Escape',
      code: 'Escape',
      bubbles: true,
    });
    await expect.soft.poll(escapeCount, { timeout: 500 }).toBe('3');
    await expectShotFocus();

    await activeTreeItem.focus();
    await page.keyboard.press('Escape');
    await expect.soft.poll(escapeCount, { timeout: 500 }).toBe('4');
    await expectShotFocus();

    await returnScene.click();
    await expectFocused('S01');
    await expect(page.getByRole('article', { name: 'Script Scene' })).toBeVisible();
    await page.keyboard.press('ArrowRight');
    await expectFocused('S01-E01-SH01');
    await page.keyboard.press('ArrowLeft');
    await expectFocused('S01');
    await page.keyboard.press('ArrowLeft');
    await expectFocused('S01');
    await page.keyboard.press('ArrowLeft');
    await expectFocused('SC-01');

    await page.setViewportSize({ width: 390, height: 844 });
    const storylineToggle = page.getByRole('button', { name: '打开故事线' });
    await expect(storylineToggle).toHaveAttribute('aria-expanded', 'false');
    await expect(page.getByRole('tree', { name: 'Episode 故事线' })).toBeHidden();
    await storylineToggle.click();
    await expect(storylineToggle).toHaveAttribute('aria-expanded', 'true');
    const storylineSheet = page.getByRole('dialog', { name: '故事线' });
    await expect(storylineSheet).toBeVisible();
    await expectFocused('SC-01');

    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: '关闭故事线' })).toBeFocused();
    await page.keyboard.press('Shift+Tab');
    await expectFocused('SC-01');
    await page.keyboard.press('Escape');
    await expect(storylineSheet).toBeHidden();
    await expect(storylineToggle).toBeFocused();
    await page.keyboard.press('Tab');
    await expect.poll(() => page.evaluate(() => document.activeElement?.getAttribute('role')))
      .not.toBe('treeitem');

    expect(diagnostics).toEqual([]);
  } finally {
    await server.close();
  }
});
