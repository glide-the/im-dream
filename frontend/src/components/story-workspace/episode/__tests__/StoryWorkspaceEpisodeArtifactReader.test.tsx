// [Input] Controlled Episode Markdown documents, storyboard shots and artifact availability.
// [Output] Safe SSR evidence for the storyboard-focus artifact reader.
// [Pos] Story Workspace Episode artifact reader Node seam.

import { expect, test } from '@playwright/test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
// @ts-expect-error Playwright Node seam reads the Vite project root; browser types omit Node.
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

import type {
  StoryWorkspaceEpisodeArtifactDocument,
  StoryWorkspaceEpisodeArtifactManifestEntry,
  StoryWorkspaceEpisodeStoryboardShot,
} from '../../../../hooks/story-workspace/contracts';

const revision = `sha256:${'1'.repeat(64)}`;
const artifacts: readonly StoryWorkspaceEpisodeArtifactManifestEntry[] = [
  ['episode-outline.md', 'plan_episode'],
  ['script.md', 'write_script'],
  ['storyboard.yaml', 'regenerate_storyboard'],
  ['review-report.md', 'review_full_chain'],
].map(([relativeKey, producerAction]) => ({
  relativeKey,
  availability: 'available',
  contentRevision: revision,
  mtime: '2026-08-06T00:00:00Z',
  size: 128,
  producerAction,
  consumers: [],
})) as readonly StoryWorkspaceEpisodeArtifactManifestEntry[];
const documents: readonly StoryWorkspaceEpisodeArtifactDocument[] = [
  {
    relativeKey: 'episode-outline.md',
    markdown: '# 下午的光\n\n## 故事目标\n\n- 守住书店',
    sourceRevision: revision,
  },
  {
    relativeKey: 'script.md',
    markdown: '# 剧本\n\n## S01 午后书店\n\n掌柜推开窗。',
    sourceRevision: revision,
  },
  {
    relativeKey: 'review-report.md',
    markdown: '# 审阅报告\n\n| 维度 | 结论 |\n| --- | --- |\n| 节奏 | 通过 |',
    sourceRevision: revision,
  },
];
const shot: StoryWorkspaceEpisodeStoryboardShot = {
  id: '2'.repeat(32),
  shotId: 'S01-E01-001',
  assetSceneRef: 'scene-shop',
  declaredScriptSceneRef: 'S01',
  declaredNarrativeBeatRef: 'SC-01',
  scriptSceneId: '3'.repeat(32),
  narrativeBeatId: '4'.repeat(32),
  associationStatus: 'linked',
  shotType: 'medium',
  characters: [{
    ref: 'shopkeeper', displayName: '掌柜', depthPlane: 'front', action: '推窗', emotion: '平静',
  }],
  camera: { angle: 'eye-level', height: 'chest', movement: 'slow-push', lens: '50mm' },
  visual: '午后的光落进书店。',
  dialogue: [{ speaker: '掌柜', line: '今天会有人来。', type: 'spoken' }],
  timing: { durationSec: 4, transitionIn: 'fade', transitionOut: 'cut' },
  sourceArtifact: 'storyboard.yaml',
  sourceRevision: revision,
  generatedFrom: 'script@v1',
};

const noOp = () => undefined;

async function renderReader(
  props: Record<string, unknown>,
): Promise<string> {
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../..', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { middlewareMode: true },
  });
  try {
    const module = await server.ssrLoadModule(
      '/src/components/story-workspace/episode/StoryWorkspaceEpisodeArtifactReader.tsx',
    ) as {
      readonly StoryWorkspaceEpisodeArtifactReader: (value: Record<string, unknown>) => unknown;
      readonly storyWorkspaceEpisodeArtifactTabTarget: (
        active: string,
        key: string,
      ) => string | null;
    };
    return renderToStaticMarkup(createElement(
      module.StoryWorkspaceEpisodeArtifactReader as never,
      props,
    ));
  } finally {
    await server.close();
  }
}

test('uses wrapping arrow, Home and End keyboard navigation for file tabs', async () => {
  const server = await createServer({
    root: fileURLToPath(new URL('../../../../..', import.meta.url)),
    configFile: false,
    logLevel: 'silent',
    server: { middlewareMode: true },
  });
  try {
    const module = await server.ssrLoadModule(
      '/src/components/story-workspace/episode/StoryWorkspaceEpisodeArtifactReader.tsx',
    ) as {
      readonly storyWorkspaceEpisodeArtifactTabTarget: (active: string, key: string) => string | null;
    };
    expect(module.storyWorkspaceEpisodeArtifactTabTarget('episode-outline.md', 'ArrowLeft'))
      .toBe('review-report.md');
    expect(module.storyWorkspaceEpisodeArtifactTabTarget('review-report.md', 'ArrowRight'))
      .toBe('episode-outline.md');
    expect(module.storyWorkspaceEpisodeArtifactTabTarget('script.md', 'Home'))
      .toBe('episode-outline.md');
    expect(module.storyWorkspaceEpisodeArtifactTabTarget('script.md', 'End'))
      .toBe('review-report.md');
    expect(module.storyWorkspaceEpisodeArtifactTabTarget('script.md', 'Enter')).toBeNull();
  } finally {
    await server.close();
  }
});

test('renders Markdown tabs through semantic markup and never as raw source text', async () => {
  const html = await renderReader({
    activeArtifact: 'review-report.md',
    artifacts,
    documents,
    shots: [shot],
    selectedShotId: shot.id,
    onArtifactSelection: noOp,
    onShotSelection: noOp,
  });

  expect(html).toContain('aria-label="第一集文件导航"');
  expect(html).toContain('分集大纲');
  expect(html).toContain('剧本');
  expect(html).toContain('分镜');
  expect(html).toContain('审阅');
  expect(html).toContain('<h1>审阅报告</h1>');
  expect(html).toContain('<table>');
  expect(html).not.toContain('# 审阅报告');
});

test('projects storyboard YAML properties for the selected stable shot identity', async () => {
  const html = await renderReader({
    activeArtifact: 'storyboard.yaml',
    artifacts,
    documents,
    shots: [shot],
    selectedShotId: shot.id,
    onArtifactSelection: noOp,
    onShotSelection: noOp,
  });

  for (const expected of [
    'aria-label="分镜镜头导航"',
    'S01-E01-001',
    '午后的光落进书店。',
    'medium',
    'eye-level',
    'slow-push',
    '50mm',
    '4 秒',
    '掌柜',
    '今天会有人来。',
    'script_scene_ref',
    'S01',
  ]) expect(html).toContain(expected);
  expect(html).not.toContain('shots:');
  expect(html).not.toContain('<pre>');
});
