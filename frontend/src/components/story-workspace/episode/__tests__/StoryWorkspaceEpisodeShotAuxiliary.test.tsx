// [Input] One selected Shot plus explicitly indexed Prompt and Render Queue facts.
// [Output] SSR coverage for independent auxiliary relationships, provenance and honest diagnostics.
// [Pos] Story Workspace Shot auxiliary view Node seam (Task 3 U8).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import { createElement, type ComponentProps } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type {
  StoryWorkspaceEpisodeArtifactSection,
  StoryWorkspaceEpisodePrompt,
  StoryWorkspaceEpisodeRenderQueueEntry,
} from '../../../../hooks/story-workspace/contracts';
import type { StoryWorkspaceEpisodeShotNode } from '../../../../pages/story-workspace/episodeExecutionViewModel';
import { StoryWorkspaceEpisodeShotAuxiliary } from '../StoryWorkspaceEpisodeShotAuxiliary';

const SOURCE = readFileSync(
  new URL('../StoryWorkspaceEpisodeShotAuxiliary.tsx', import.meta.url),
  'utf8',
);
const opaqueId = (value: number) => value.toString(16).padStart(32, '0');
const revision = (value: string) => `sha256:${value.repeat(64)}`;

const SHOT_VIEW_ID = opaqueId(1);

const selectedShot: StoryWorkspaceEpisodeShotNode = {
  kind: 'shot',
  id: SHOT_VIEW_ID,
  shotId: 'S01-E01-SH01',
  assetSceneRef: null,
  declaredScriptSceneRef: 'S01',
  declaredNarrativeBeatRef: 'SC-01',
  scriptSceneId: opaqueId(2),
  narrativeBeatId: opaqueId(3),
  associationStatus: 'linked',
  shotType: 'wide',
  characters: [],
  camera: {
    angle: 'eye-level',
    height: 'shoulder',
    movement: 'slow-push',
    lens: '50mm',
  },
  visual: '雨夜站台。',
  dialogue: [],
  timing: { durationSec: 3, transitionIn: 'cut', transitionOut: 'hold' },
  sourceArtifact: 'storyboard.yaml',
  sourceRevision: revision('a'),
  generatedFrom: null,
  sourceAvailability: 'available',
};

function prompt(
  value: number,
  overrides: Partial<StoryWorkspaceEpisodePrompt> = {},
): StoryWorkspaceEpisodePrompt {
  return {
    id: opaqueId(value),
    shotId: 'S01-E01-SH01',
    kind: 'image',
    shotViewId: SHOT_VIEW_ID,
    associationStatus: 'linked',
    positive: '雨夜站台，人物停步',
    negative: '过曝，字幕',
    parameters: {
      model: 'ink-image-v2',
      mode: 'cinematic',
      durationSec: 4,
      motionStrength: 0.35,
      cameraMotion: 'slow-push',
      aspectRatio: '16:9',
    },
    generability: {
      characterAnchor: '林默',
      motionFeasibility: '可生成',
      durationBudget: '4 秒以内',
      notes: '保持雨丝连续',
    },
    sourceArtifact: 'prompts/private-path-should-not-render.yaml',
    sourceRevision: revision('b'),
    ...overrides,
  };
}

function queueEntry(
  value: number,
  overrides: Partial<StoryWorkspaceEpisodeRenderQueueEntry> = {},
): StoryWorkspaceEpisodeRenderQueueEntry {
  return {
    id: opaqueId(value),
    shotId: 'S01-E01-SH01',
    shotViewId: SHOT_VIEW_ID,
    associationStatus: 'linked',
    durationSec: 4,
    risk: '雨丝连续性',
    priority: 'high',
    renderer: 'cinema-renderer',
    status: 'pending',
    sourceArtifact: 'renders/render-guide.md',
    sourceRevision: revision('c'),
    ...overrides,
  };
}

const guideSections: readonly StoryWorkspaceEpisodeArtifactSection[] = [{
  id: opaqueId(20),
  level: 2,
  title: '雨夜连续性',
  text: '保持人物站位和雨向一致。',
  sourceArtifact: 'renders/render-guide.md',
  sourceRevision: revision('c'),
}];

function props(
  overrides: Partial<ComponentProps<typeof StoryWorkspaceEpisodeShotAuxiliary>> = {},
): ComponentProps<typeof StoryWorkspaceEpisodeShotAuxiliary> {
  return {
    selectedShot,
    prompts: [],
    renderQueueEntries: [],
    renderGuideSections: [],
    associationCoverage: {
      shotPrompt: { availability: 'unavailable', linked: 0, total: 0, ratio: null },
      shotRenderQueue: {
        availability: 'unavailable', linked: 0, total: 0, ratio: null,
      },
    },
    sourceAvailability: {
      prompts: 'not_generated',
      renderGuide: 'not_generated',
    },
    ...overrides,
  };
}

function render(
  overrides: Partial<ComponentProps<typeof StoryWorkspaceEpisodeShotAuxiliary>> = {},
): string {
  return renderToStaticMarkup(createElement(
    StoryWorkspaceEpisodeShotAuxiliary,
    props(overrides),
  ));
}

test('renders two independent semantic disclosures and zero-denominator pending copy', () => {
  const html = render();

  expect(html).toContain('<summary>Prompt</summary>');
  expect(html).toContain('<summary>制作指导 / Render Queue</summary>');
  expect(html).toContain('关系：Shot → Prompt');
  expect(html).toContain('关系：Shot → Render Queue');
  expect(html).toContain('Prompt 尚未生成');
  expect(html).toContain('制作指导尚未生成');
  expect(html.match(/关联覆盖：尚未生成/g)).toHaveLength(2);
  expect(html).not.toContain('0%');
  expect(html).not.toContain('Prompt → Render');
});

test('renders every explicitly indexed Prompt with kind, opaque id and allowlisted fields', () => {
  const html = render({
    prompts: [
      prompt(10),
      prompt(11, {
        shotId: 'DIFFERENT-DISPLAY-SHOT-ID',
        kind: 'video',
        positive: '人物回望',
        negative: null,
        sourceRevision: revision('d'),
      }),
    ],
    associationCoverage: {
      shotPrompt: { availability: 'available', linked: 1, total: 2, ratio: 0.5 },
      shotRenderQueue: {
        availability: 'unavailable', linked: 0, total: 0, ratio: null,
      },
    },
    sourceAvailability: { prompts: 'available', renderGuide: 'not_generated' },
  });

  for (const expected of [
    'Prompt image',
    'Prompt video',
    opaqueId(10),
    opaqueId(11),
    '雨夜站台，人物停步',
    '过曝，字幕',
    '人物回望',
    'ink-image-v2',
    'cinematic',
    '4 秒',
    '0.35',
    'slow-push',
    '16:9',
    '林默',
    '可生成',
    '4 秒以内',
    '保持雨丝连续',
    `Revision：${revision('b')}`,
    `Revision：${revision('d')}`,
    '关联覆盖：1 / 2（50%）',
  ]) expect(html).toContain(expected);
  expect(html).not.toContain('DIFFERENT-DISPLAY-SHOT-ID');
  expect(html).not.toContain('private-path-should-not-render');
});

test('renders guide and one Queue entry without claiming media or Prompt linkage', () => {
  const html = render({
    renderQueueEntries: [queueEntry(30)],
    renderGuideSections: guideSections,
    associationCoverage: {
      shotPrompt: { availability: 'unavailable', linked: 0, total: 0, ratio: null },
      shotRenderQueue: { availability: 'available', linked: 1, total: 1, ratio: 1 },
    },
    sourceAvailability: { prompts: 'not_generated', renderGuide: 'available' },
  });

  for (const expected of [
    '已生成制作指导；真实画面不在本期受审合同内',
    '雨夜连续性',
    '保持人物站位和雨向一致。',
    '已关联 1 条 Render Queue',
    opaqueId(30),
    '4 秒',
    '雨丝连续性',
    'high',
    'cinema-renderer',
    'pending',
    `Revision：${revision('c')}`,
    '关联覆盖：1 / 1（100%）',
  ]) expect(html).toContain(expected);
  expect(html).not.toContain('Prompt → Render');
});

test('keeps Queue independently visible when this Shot has no Prompt', () => {
  const html = render({
    prompts: [],
    renderQueueEntries: [queueEntry(31)],
    associationCoverage: {
      shotPrompt: { availability: 'available', linked: 2, total: 4, ratio: 0.5 },
      shotRenderQueue: { availability: 'available', linked: 1, total: 4, ratio: 0.25 },
    },
    sourceAvailability: { prompts: 'available', renderGuide: 'available' },
  });

  expect(html).toContain('此 Shot 尚未关联 Prompt');
  expect(html).toContain('已关联 1 条 Render Queue');
  expect(html).toContain(opaqueId(31));
});

test('diagnoses duplicate Queue rows without selecting one', () => {
  const html = render({
    renderQueueEntries: [queueEntry(32), queueEntry(33, { status: 'running' })],
    associationCoverage: {
      shotPrompt: { availability: 'unavailable', linked: 0, total: 0, ratio: null },
      shotRenderQueue: { availability: 'available', linked: 1, total: 1, ratio: 1 },
    },
    sourceAvailability: { prompts: 'not_generated', renderGuide: 'invalid' },
  });

  expect(html).toContain('制作指导来源无效');
  expect(html).toContain('重复关联：该 Shot 关联 2 条 Render Queue；未自动选择');
  expect(html).toContain(opaqueId(32));
  expect(html).toContain(opaqueId(33));
});

test('keeps unlinked and orphan diagnostics distinct', () => {
  const html = render({
    prompts: [prompt(40, { associationStatus: 'unlinked' })],
    renderQueueEntries: [queueEntry(41, { associationStatus: 'orphan' })],
    associationCoverage: {
      shotPrompt: { availability: 'available', linked: 0, total: 1, ratio: 0 },
      shotRenderQueue: { availability: 'available', linked: 0, total: 1, ratio: 0 },
    },
    sourceAvailability: { prompts: 'available', renderGuide: 'available' },
  });

  expect(html).toContain('尚未关联：没有声明可验证的 Shot 关系');
  expect(html).toContain('孤立引用：声明的 Shot 目标不存在或不一致');
});

test('separates invalid source copy from an available but unlinked Queue', () => {
  const html = render({
    associationCoverage: {
      shotPrompt: { availability: 'available', linked: 0, total: 1, ratio: 0 },
      shotRenderQueue: { availability: 'available', linked: 0, total: 1, ratio: 0 },
    },
    sourceAvailability: { prompts: 'invalid', renderGuide: 'available' },
  });

  expect(html).toContain('Prompt 来源无效；当前条目仅用于关系诊断');
  expect(html).toContain('此 Shot 尚未关联 Render Queue');
  expect(html).not.toContain('制作指导尚未生成');
});

test('escapes artifact text and keeps media, path, tool and persistence surfaces absent', () => {
  const unsafe = '<script>window.secret="credential"</script>';
  const html = render({
    prompts: [prompt(50, { positive: unsafe, negative: '<img src=x>' })],
    renderQueueEntries: [queueEntry(51, { risk: '<video>secret</video>' })],
    renderGuideSections: [{ ...guideSections[0], title: unsafe, text: '<a href=x>open</a>' }],
    associationCoverage: {
      shotPrompt: { availability: 'available', linked: 1, total: 1, ratio: 1 },
      shotRenderQueue: { availability: 'available', linked: 1, total: 1, ratio: 1 },
    },
    sourceAvailability: { prompts: 'available', renderGuide: 'available' },
  });

  expect(html).toContain('&lt;script&gt;');
  expect(html).toContain('&lt;img src=x&gt;');
  expect(html).toContain('&lt;video&gt;');
  expect(html).toContain('&lt;a href=x&gt;');
  expect(html).not.toContain('<script>');
  for (const forbidden of [
    'ChatView',
    'localStorage',
    'sessionStorage',
    'useState',
    'useReducer',
    'dangerouslySetInnerHTML',
    'toolArgs',
    'toolArguments',
    'sourceArtifact',
    '<img',
    '<video',
    '<a ',
    'href=',
    'src=',
    'http://',
    'https://',
    'prompt.shotId',
    'entry.shotId',
  ]) expect(SOURCE).not.toContain(forbidden);
});
