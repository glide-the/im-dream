// [Input] Real local actor, persisted Dream run, and actor-scoped Episode artifact API.
// [Output] Browser evidence that canonical Markdown and storyboard properties are readable in Execution.
// [Pos] Opt-in Story Workspace real-data regression; never mutates the workflow or artifact files.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { mkdirSync, writeFileSync } from 'node:fs';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test } from '@playwright/test';

const ENABLED = process.env.INK_REAL_EPISODE_QA === '1';
const WEB_BASE = process.env.INK_REAL_EPISODE_WEB_BASE ?? 'http://127.0.0.1:5174';
const API_BASE = process.env.INK_REAL_EPISODE_API_BASE?.replace(/\/$/, '');
const RUN_ID = process.env.INK_REAL_EPISODE_RUN_ID
  ?? 'run_b81d3731b56b4703868b66af76e7b656';
const ACTOR_EMAIL = process.env.INK_REAL_EPISODE_ACTOR_EMAIL
  ?? 'dmeck123@suoxya.com';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');
const EVIDENCE_DIR = process.env.INK_REAL_EPISODE_EVIDENCE_DIR
  ? resolve(process.env.INK_REAL_EPISODE_EVIDENCE_DIR)
  : resolve(REPO_ROOT, 'output/playwright/story-workspace-real-episode-artifacts');

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Set INK_REAL_EPISODE_QA=1 to run against the persisted local actor and run.');

function createActorToken(email: string): string {
  const source = [
    "from dotenv import load_dotenv",
    "load_dotenv('.env')",
    'import auth, database, sys',
    'db = database.get_db()',
    "user = db.execute('select id, email from users where email = %s', (sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'], user['email']))",
  ].join('; ');
  return execFileSync(BACKEND_PYTHON, ['-c', source, email], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

test('real actor loads persisted Dream files and EP01 artifacts without API failures', async ({
  browser,
}) => {
  test.setTimeout(120_000);
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  const diagnostics: string[] = [];
  const apiFailures: string[] = [];
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (
      message.type() === 'error'
      && !message.text().startsWith('Failed to load resource:')
    ) diagnostics.push(`console: ${message.text()}`);
  });
  page.on('requestfailed', (request) => {
    if (request.failure()?.errorText === 'net::ERR_ABORTED') return;
    diagnostics.push(
      `requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`,
    );
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/story-workspace/')) {
      apiFailures.push(`${response.status()} ${response.url()}`);
    }
  });
  if (API_BASE !== undefined) {
    await page.route('**/api/**', async (route) => {
      const original = new URL(route.request().url());
      if (!original.pathname.startsWith('/api/')) {
        await route.continue();
        return;
      }
      if (original.pathname.endsWith('/events')) {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: ': isolated real-REST QA\n\n',
        });
        return;
      }
      const response = await route.fetch({
        url: `${API_BASE}${original.pathname}${original.search}`,
      });
      await route.fulfill({ response });
    });
  }

  const token = createActorToken(ACTOR_EMAIL);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    const dreamFilesResponse = page.waitForResponse((response) => (
      response.url().includes(`/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`)
      && response.status() === 200
    ));
    const surfaceResponse = page.waitForResponse((response) => (
      response.url().includes(`/api/story-workspace/workflow-runs/${RUN_ID}/episode-artifacts`)
      && response.status() === 200
    ));
    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
    const dreamResponse = await dreamFilesResponse;
    const episodeResponse = await surfaceResponse;
    const dreamFiles = await dreamResponse.json() as {
      runRevision: number;
      stages: {
        storyboards?: {
          sourceFiles: string[];
          items: Array<{ entityId: string }>;
        };
      };
    };
    expect(dreamFiles.runRevision).toBeGreaterThan(0);
    expect(dreamFiles.stages.storyboards?.sourceFiles).toEqual(expect.arrayContaining([
      expect.stringMatching(/episode-outline\.md$/),
      expect.stringMatching(/script\.md$/),
      expect.stringMatching(/storyboard\.yaml$/),
    ]));
    const hasStoryboardReaderHost = (dreamFiles.stages.storyboards?.items.length ?? 0) > 0;
    const surface = await episodeResponse.json() as {
      bindingAvailability: string;
      opaqueEpisodeId: string | null;
      manifestRevision: string;
      etag: string;
      documents?: Array<{ relativeKey: string; markdown: string; sourceRevision: string }>;
      artifacts: Array<{
        relativeKey: string;
        availability: string;
        contentRevision: string | null;
        size: number | null;
      }>;
      narrative?: { shots?: unknown[] };
      auxiliary?: {
        prompts?: { items: unknown[]; total: number };
        associations?: {
          shotPromptCoverage?: {
            availability: string;
            linked: number;
            total: number;
            ratio: number | null;
          };
        };
      } | null;
    };
    expect(surface.bindingAvailability).toBe('bound');
    expect(surface.documents?.map((document) => document.relativeKey)).toEqual([
      'episode-outline.md',
      'script.md',
      'review-report.md',
    ]);
    expect(surface.narrative?.shots).toHaveLength(22);
    expect(surface.auxiliary?.prompts?.total).toBe(66);
    expect(surface.auxiliary?.prompts?.items).toHaveLength(66);
    expect(surface.auxiliary?.associations?.shotPromptCoverage).toEqual({
      availability: 'available',
      linked: 22,
      total: 22,
      ratio: 1,
    });
    writeFileSync(
      resolve(EVIDENCE_DIR, 'episode-artifact-manifest.json'),
      JSON.stringify({
        runId: RUN_ID,
        actorEmail: ACTOR_EMAIL,
        dreamRunRevision: dreamFiles.runRevision,
        hasStoryboardReaderHost,
        bindingAvailability: surface.bindingAvailability,
        manifestRevision: surface.manifestRevision,
        aggregateEtag: surface.etag,
        responseEtag: episodeResponse.headers()['etag'] ?? null,
        artifacts: surface.artifacts,
        documents: surface.documents?.map((document) => ({
          relativeKey: document.relativeKey,
          sourceRevision: document.sourceRevision,
          characters: document.markdown.length,
        })) ?? [],
        projectedShotCount: surface.narrative?.shots?.length ?? 0,
        projectedPromptCount: surface.auxiliary?.prompts?.total ?? 0,
        promptPageItemCount: surface.auxiliary?.prompts?.items.length ?? 0,
        shotPromptCoverage: surface.auxiliary?.associations?.shotPromptCoverage ?? null,
      }, null, 2),
      'utf-8',
    );
    const browserParserError = await page.evaluate(async (runId) => {
      const contract = await import('/src/hooks/story-workspace/contracts.ts');
      const apiBase = await import('/src/lib/apiBase.ts');
      const query = await import('/src/hooks/story-workspace/useStoryWorkspaceEpisodeArtifacts.ts');
      const endpoint = apiBase.apiUrl(
        `/api/story-workspace/workflow-runs/${encodeURIComponent(runId)}/episode-artifacts`,
      );
      const response = await fetch(
        endpoint,
        { headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') ?? ''}` } },
      );
      try {
        contract.storyWorkspaceParseEpisodeArtifactSurface(await response.json());
        await query.storyWorkspaceFetchEpisodeArtifacts(endpoint, {
          expectedRunId: runId,
          token: localStorage.getItem('auth_token'),
        });
        return null;
      } catch (error) {
        return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
      }
    }, RUN_ID);
    expect(browserParserError).toBeNull();

    const overview = page.getByRole('article', { name: 'Episode Overview' });
    await expect(overview).toBeVisible();
    const openAgent = page.getByRole('button', { name: '打开 Dream Agent 消息预览' });
    await openAgent.click();
    let agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(agentDialog).toBeVisible();
    await expect(agentDialog.getByText('Episode 下一步')).toHaveCount(0);
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'dream-agent-desktop-1440x1000.png'),
      fullPage: true,
    });
    await page.keyboard.press('Escape');
    await expect(agentDialog).toHaveCount(0);
    await expect(openAgent).toBeFocused();
    const progress = overview.getByRole('list', { name: 'EP01 产物进度' });
    await expect(progress).toBeVisible();
    await expect(progress.locator('li')).toHaveCount(6);
    await expect(progress.getByRole('button')).toHaveCount(hasStoryboardReaderHost ? 4 : 0);
    await expect(progress.getByRole('button', { name: '阅读Prompts' })).toHaveCount(0);
    await expect(progress.getByRole('button', { name: '阅读渲染指引' })).toHaveCount(0);
    await expect(progress.locator('li').nth(0)).toContainText('分集大纲已生成');
    await expect(progress.locator('li').filter({ hasText: 'Prompts' })).toContainText('已生成');
    await expect(progress.locator('li').filter({ hasText: '渲染指引' }))
      .toContainText('尚未准备');
    await expect(progress.getByText('Renders', { exact: true })).toHaveCount(0);
    expect(await progress.evaluate((element) => element.previousElementSibling?.tagName)).toBe('H2');
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'episode-overview-progress-desktop-1440x1000.png'),
      fullPage: true,
    });

    const reader = page.getByRole('region', { name: 'EP01 文件阅读器' });
    if (hasStoryboardReaderHost) {
      for (const label of ['阅读分集大纲', '阅读剧本', '阅读分镜', '阅读审阅报告']) {
        await expect(progress.getByRole('button', { name: label })).toBeVisible();
      }
      const readScript = progress.getByRole('button', { name: '阅读剧本' });
      await readScript.focus();
      await readScript.press('Enter');
      await expect(reader).toBeVisible();
      await expect(reader).toBeInViewport();
      await expect(page.locator('details').filter({ hasText: 'Dream 初稿阶段投影' }))
        .toHaveAttribute('open', '');
      await expect(reader.getByRole('tab', { name: /剧本/ }))
        .toHaveAttribute('aria-selected', 'true');
      await expect(reader.getByRole('tab', { name: /剧本/ })).toBeFocused();
      await expect(reader.getByRole('tab', { name: /剧本/ })).toBeInViewport();
      await expect(reader.getByRole('article', { name: '剧本文件内容' }))
        .toContainText('浮世行路');

      await progress.getByRole('button', { name: '阅读分镜' }).click();
      await expect(reader).toBeInViewport();
      await expect(reader.getByRole('tab', { name: /分镜/ }))
        .toHaveAttribute('aria-selected', 'true');
      await expect(reader.getByRole('tab', { name: /分镜/ })).toBeFocused();
      await expect(reader.getByRole('tab', { name: /分镜/ })).toBeInViewport();
      await expect(reader.getByRole('navigation', { name: '分镜镜头导航' }).getByRole('button'))
        .toHaveCount(22);
      await expect(reader.getByRole('article', { name: '分镜 YAML 属性' }))
        .toContainText('镜头参数');

      await reader.getByRole('tab', { name: /分集大纲/ }).click();
      await expect(reader.getByRole('article', { name: '分集大纲文件内容' }))
        .toContainText('下午的光');
      const outlineTab = reader.getByRole('tab', { name: /分集大纲/ });
      await outlineTab.focus();
      await outlineTab.press('ArrowRight');
      await expect(reader.getByRole('tab', { name: /剧本/ }))
        .toHaveAttribute('aria-selected', 'true');
      await expect(reader.getByRole('article', { name: '剧本文件内容' }))
        .toContainText('浮世行路');

      await progress.getByRole('button', { name: '阅读审阅报告' }).click();
      await expect(reader).toBeInViewport();
      await expect(reader.getByRole('tab', { name: /审阅/ })).toBeFocused();
      await expect(reader.getByRole('tab', { name: /审阅/ })).toBeInViewport();
      await expect(reader.getByRole('article', { name: '审阅文件内容' }))
        .toContainText('审查报告');
      await page.getByRole('button', { name: '定位镜头：S04-E01-020a' }).click();
      await expect(page.getByRole('article', { name: 'Prompt kling' })).toBeVisible();
      await expect(page.getByRole('article', { name: 'Prompt runway' })).toBeVisible();
      await expect(page.getByRole('article', { name: 'Prompt jimeng' })).toBeVisible();
      await page.screenshot({
        path: resolve(EVIDENCE_DIR, 'episode-artifacts-desktop-1440x1000.png'),
        fullPage: true,
      });
    } else {
      await expect(reader).toHaveCount(0);
    }

    await page.setViewportSize({ width: 390, height: 844 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
    if (hasStoryboardReaderHost) {
      await expect(reader).toBeVisible();
      await page.evaluate(() => {
        const element = document.querySelector<HTMLElement>('nav[aria-label="EP01 文件导航"]');
        if (element === null) throw new Error('Episode artifact navigation is missing.');
        element.scrollIntoView({ block: 'start' });
      });
    }
    await page.screenshot({
      path: resolve(
        EVIDENCE_DIR,
        hasStoryboardReaderHost
          ? 'episode-artifacts-narrow-390x844.png'
          : 'episode-overview-narrow-390x844.png',
      ),
    });
    await openAgent.click();
    agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    await expect(agentDialog).toBeVisible();
    expect(await agentDialog.evaluate((element) => element.scrollWidth <= element.clientWidth + 1))
      .toBe(true);
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'dream-agent-narrow-390x844.png'),
    });
    await page.keyboard.press('Escape');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toContain('/Users/');
    expect(bodyText).not.toContain('第一集产物来源无效');
    expect(apiFailures).toEqual([]);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.close();
  }
});
