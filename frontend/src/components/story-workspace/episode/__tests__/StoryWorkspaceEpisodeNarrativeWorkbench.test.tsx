// [Input] Episode execution view-model, selection and expansion facts.
// [Output] SSR semantic markup and pure keyboard interaction coverage for the narrative workbench.
// [Pos] Story Workspace Episode narrative workbench Node seam (Task 3 U7).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import { createElement, type ComponentProps } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
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
        characterBeats: [],
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
  expect(beatHtml).toContain('林默在站台停下脚步。');
  expect(beatHtml).toContain('暴露犹豫');
  expect(sceneHtml).toContain('EXT. 旧车站站台 - 夜');
  expect(sceneHtml).toContain('苏遥从雨幕中走来。');
  expect(sceneHtml).toContain('苏遥');
  expect(sceneHtml).toContain('你还是来了。');
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
    '来源：storyboard.yaml',
    'Revision：storyboard-r3',
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
