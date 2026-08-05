// [Input] Parsed Review Report facts, artifact availability and optional target selection.
// [Output] SSR and callback coverage for a read-only, explicitly linked Review auxiliary panel.
// [Pos] Story Workspace Episode Review panel Node seam (Task 3 U9).

import { expect, test } from '@playwright/test';
// @ts-expect-error Playwright Node seam reads source; browser app omits Node types.
import { readFileSync } from 'node:fs';
import { createElement, type ComponentProps } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

import type {
  StoryWorkspaceEpisodeReviewReport,
  StoryWorkspaceEpisodeReviewTarget,
} from '../../../../hooks/story-workspace/contracts';
import {
  StoryWorkspaceEpisodeReviewPanel,
  storyWorkspaceLocateEpisodeReviewTarget,
  type StoryWorkspaceEpisodeReviewLocateSelection,
} from '../StoryWorkspaceEpisodeReviewPanel';

const SOURCE = readFileSync(
  new URL('../StoryWorkspaceEpisodeReviewPanel.tsx', import.meta.url),
  'utf8',
);
const opaqueId = (value: number) => value.toString(16).padStart(32, '0');
const revision = (value: string) => `sha256:${value.repeat(64)}`;

const BEAT_VIEW_ID = opaqueId(1);
const SCENE_VIEW_ID = opaqueId(2);
const SHOT_VIEW_ID = opaqueId(3);

function target(
  value: number,
  overrides: Partial<StoryWorkspaceEpisodeReviewTarget> = {},
): StoryWorkspaceEpisodeReviewTarget {
  return {
    id: opaqueId(value),
    kind: 'shot',
    sourceKey: 'S01-E01-SH01',
    targetViewId: SHOT_VIEW_ID,
    associationStatus: 'linked',
    sectionId: opaqueId(90),
    sourceArtifact: 'review-report.md',
    sourceRevision: revision('f'),
    ...overrides,
  };
}

function report(
  overrides: Partial<StoryWorkspaceEpisodeReviewReport> = {},
): StoryWorkspaceEpisodeReviewReport {
  return {
    scope: 'script',
    overallVerdict: 'CONDITIONAL_APPROVAL',
    reviewedArtifacts: ['script.md', 'storyboard.yaml', 'prompts/'],
    sourceRevisions: [
      { sourceArtifact: 'script.md', sourceRevision: revision('a') },
      { sourceArtifact: 'storyboard.yaml', sourceRevision: revision('b') },
    ],
    sections: [{
      id: opaqueId(80),
      level: 2,
      title: '节奏与连续性',
      text: '第二场转折需要更多停顿。',
      sourceArtifact: 'review-report.md',
      sourceRevision: revision('f'),
    }],
    targets: [],
    sourceArtifact: 'review-report.md',
    sourceRevision: revision('f'),
    ...overrides,
  };
}

const noOp = () => undefined;

function render(
  overrides: Partial<ComponentProps<typeof StoryWorkspaceEpisodeReviewPanel>> = {},
): string {
  return renderToStaticMarkup(createElement(
    StoryWorkspaceEpisodeReviewPanel,
    {
      review: report(),
      availability: 'available',
      currentTargetSelection: null,
      onLocateTarget: noOp,
      ...overrides,
    },
  ));
}

test('renders a low-level read-only script review with logical artifact provenance', () => {
  const html = render();

  for (const expected of [
    '<aside',
    '<summary>Review Report</summary>',
    '只读审阅报告',
    '审阅范围',
    '剧本（script）',
    '报告结论',
    'CONDITIONAL_APPROVAL',
    '受审产物',
    'Script',
    'Storyboard',
    'Prompts',
    `Script · ${revision('a')}`,
    `Storyboard · ${revision('b')}`,
    '节奏与连续性',
    '第二场转折需要更多停顿。',
    `来源：Review Report · Revision：${revision('f')}`,
  ]) expect(html).toContain(expected);
  expect(html).not.toContain('script.md');
  expect(html).not.toContain('storyboard.yaml');
  expect(html).not.toContain('prompts/');
  expect(html).not.toContain('批准');
  expect(html).not.toContain('重试');
  expect(html).not.toContain('保存');
});

test('renders full-chain and unknown scopes as report facts only', () => {
  expect(render({ review: report({ scope: 'full-chain', overallVerdict: 'APPROVED' }) }))
    .toContain('全链路（full-chain）');
  const unknown = render({ review: report({ scope: 'unknown', overallVerdict: null }) });
  expect(unknown).toContain('范围未声明（unknown）');
  expect(unknown).toContain('报告结论</dt><dd>尚未声明');
});

test('locates linked Beat, Scene and Shot targets only by explicit opaque identity', () => {
  const targets = [
    target(10, {
      kind: 'narrative-beat', sourceKey: 'SC-01', targetViewId: BEAT_VIEW_ID,
    }),
    target(11, {
      kind: 'script-scene', sourceKey: 'S01', targetViewId: SCENE_VIEW_ID,
    }),
    target(12),
  ];
  const html = render({
    review: report({ targets }),
    currentTargetSelection: { kind: 'shot', id: SHOT_VIEW_ID },
  });

  expect(html.match(/<button/g)).toHaveLength(3);
  expect(html).toContain('定位叙事点：SC-01');
  expect(html).toContain('定位场景：S01');
  expect(html).toContain('定位镜头：S01-E01-SH01');
  expect(html).toContain('aria-current="true"');
  expect(html).not.toContain(BEAT_VIEW_ID);
  expect(html).not.toContain(SCENE_VIEW_ID);
  expect(html).not.toContain(SHOT_VIEW_ID);

  const located: StoryWorkspaceEpisodeReviewLocateSelection[] = [];
  for (const item of targets) {
    expect(storyWorkspaceLocateEpisodeReviewTarget(item, (selection) => {
      located.push(selection);
    })).toBe(true);
  }
  expect(located).toEqual([
    { kind: 'narrative-beat', id: BEAT_VIEW_ID },
    { kind: 'scene', id: SCENE_VIEW_ID },
    { kind: 'shot', id: SHOT_VIEW_ID },
  ]);
});

test('keeps unlinked and orphan targets diagnostic-only and visibly distinct', () => {
  const unlinked = target(20, {
    sourceKey: 'SUP-E01-01',
    targetViewId: null,
    associationStatus: 'unlinked',
  });
  const orphan = target(21, {
    sourceKey: 'S99-E01-SH01',
    targetViewId: null,
    associationStatus: 'orphan',
  });
  const html = render({ review: report({ targets: [unlinked, orphan] }) });

  expect(html).toContain('尚未关联');
  expect(html).toContain('没有声明可验证的定位目标');
  expect(html).toContain('SUP-E01-01');
  expect(html).toContain('孤立引用');
  expect(html).toContain('声明的定位目标不存在或不一致');
  expect(html).toContain('S99-E01-SH01');
  expect(html).not.toContain('<button');

  const located: StoryWorkspaceEpisodeReviewLocateSelection[] = [];
  expect(storyWorkspaceLocateEpisodeReviewTarget(unlinked, (value) => {
    located.push(value);
  })).toBe(false);
  expect(storyWorkspaceLocateEpisodeReviewTarget(orphan, (value) => {
    located.push(value);
  })).toBe(false);
  expect(located).toEqual([]);
});

test('separates null, not-generated, invalid and unavailable report states', () => {
  const cases = [
    ['available', '审阅报告内容尚未形成'],
    ['not_generated', '审阅报告尚未生成'],
    ['invalid', '审阅报告来源无效，暂无法读取'],
    ['unavailable', '审阅报告来源当前不可用'],
  ] as const;
  for (const [availability, expected] of cases) {
    const html = render({ review: null, availability });
    expect(html).toContain(expected);
    expect(html).not.toContain('CONDITIONAL_APPROVAL');
  }
});

test('escapes section and target text without exposing implementation surfaces', () => {
  const unsafe = '<script>window.secret="credential"</script>';
  const html = render({
    review: report({
      sections: [{
        id: opaqueId(70),
        level: 2,
        title: unsafe,
        text: '<img src=x onerror=alert(1)>',
        sourceArtifact: 'review-report.md',
        sourceRevision: revision('f'),
      }],
      targets: [target(71, { sourceKey: '<b>unsafe</b>' })],
    }),
  });

  expect(html).toContain('&lt;script&gt;');
  expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;');
  expect(html).toContain('&lt;b&gt;unsafe&lt;/b&gt;');
  expect(html).not.toContain('<script>');
  for (const forbidden of [
    'ChatView',
    'localStorage',
    'sessionStorage',
    'dangerouslySetInnerHTML',
    'hiddenReasoning',
    'toolArgs',
    'toolArguments',
    'contentEditable',
    'useState',
    '<form',
    '<input',
    '<textarea',
    'href=',
    'src=',
    'http://',
    'https://',
  ]) expect(SOURCE).not.toContain(forbidden);
});
