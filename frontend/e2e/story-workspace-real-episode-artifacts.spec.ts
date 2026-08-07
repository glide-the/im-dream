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
const RUN_ID = process.env.INK_REAL_EPISODE_RUN_ID
  ?? 'run_b81d3731b56b4703868b66af76e7b656';
const ACTOR_EMAIL = process.env.INK_REAL_EPISODE_ACTOR_EMAIL
  ?? 'dmeck123@suoxya.com';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');
const EVIDENCE_DIR = resolve(
  REPO_ROOT,
  'output/playwright/story-workspace-real-episode-artifacts',
);

test.use({ channel: 'chromium', timezoneId: 'Asia/Shanghai' });
test.skip(!ENABLED, 'Set INK_REAL_EPISODE_QA=1 to run against the persisted local actor and run.');

function createActorToken(email: string): string {
  const source = [
    "from dotenv import load_dotenv",
    "load_dotenv('.env')",
    'import auth, database, sys',
    'db = database.get_db()',
    "user = db.execute('select id, email from users where email = ?', (sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'], user['email']))",
  ].join('; ');
  return execFileSync(BACKEND_PYTHON, ['-c', source, email], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

test('real actor can read Markdown documents and structured storyboard from the persisted EP01', async ({
  browser,
}) => {
  test.setTimeout(120_000);
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  const diagnostics: string[] = [];
  const apiFailures: string[] = [];
  const episodeActionPosts: string[] = [];
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error') diagnostics.push(`console: ${message.text()}`);
  });
  page.on('response', (response) => {
    if (response.status() >= 400 && response.url().includes('/api/story-workspace/')) {
      apiFailures.push(`${response.status()} ${response.url()}`);
    }
  });
  page.on('request', (request) => {
    if (
      request.method() === 'POST'
      && request.url().includes('/episode-actions/')
    ) episodeActionPosts.push(request.url());
  });

  const token = createActorToken(ACTOR_EMAIL);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    const surfaceResponse = page.waitForResponse((response) => (
      response.url().includes(`/api/story-workspace/workflow-runs/${RUN_ID}/episode-artifacts`)
      && response.status() === 200
    ));
    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
    const episodeResponse = await surfaceResponse;
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
      actionProjection?: {
        recommendedActionId: string | null;
        actionOptions: Array<{
          actionId: string;
          action: string;
          label: string;
          targetEpisode: { displayLabel: string; relation: string };
          availability: string;
          canDispatch: boolean;
          disabledReason: string | null;
          canonicalInputs: unknown[];
        }>;
      } | null;
    };
    expect(surface.bindingAvailability).toBe('bound');
    expect(surface.documents?.map((document) => document.relativeKey)).toEqual([
      'episode-outline.md',
      'script.md',
      'review-report.md',
    ]);
    expect(surface.narrative?.shots).toHaveLength(22);
    expect(surface.actionProjection?.actionOptions).toHaveLength(6);
    writeFileSync(
      resolve(EVIDENCE_DIR, 'episode-artifact-manifest.json'),
      JSON.stringify({
        runId: RUN_ID,
        actorEmail: ACTOR_EMAIL,
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
      }, null, 2),
      'utf-8',
    );
    writeFileSync(
      resolve(EVIDENCE_DIR, 'workflow-action-projection.json'),
      JSON.stringify({
        runId: RUN_ID,
        actorEmail: ACTOR_EMAIL,
        opaqueEpisodeId: surface.opaqueEpisodeId,
        manifestRevision: surface.manifestRevision,
        aggregateEtag: surface.etag,
        recommendedActionId: surface.actionProjection?.recommendedActionId ?? null,
        actionOptions: surface.actionProjection?.actionOptions.map((option) => ({
          actionId: option.actionId,
          action: option.action,
          label: option.label,
          targetEpisode: option.targetEpisode,
          availability: option.availability,
          canDispatch: option.canDispatch,
          disabledReason: option.disabledReason,
          canonicalInputCount: option.canonicalInputs.length,
        })) ?? [],
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
    await expect(agentDialog.getByRole('button', {
      name: /生成 EP01 Prompt 包.*推荐操作.*当前可执行/,
    })).toBeEnabled();
    await expect(agentDialog.getByRole('button', {
      name: /审阅 EP01 完整产物.*未来可用/,
    })).toBeDisabled();
    await expect(agentDialog.getByRole('button', { name: /审阅 EP01 剧本/ })).toHaveCount(0);
    let disclosure = agentDialog.getByRole('button', { name: '更多工作流操作（4）' });
    await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    await disclosure.click();
    await expect(agentDialog.getByRole('button', {
      name: /校验并提交 EP01.*未来可用/,
    })).toBeDisabled();
    await expect(agentDialog.getByRole('button', {
      name: /开始 EP02 分集规划.*暂不可用/,
    })).toBeDisabled();
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'workflow-actions-desktop-1440x1000.png'),
      fullPage: true,
    });
    await page.keyboard.press('Escape');
    await expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    await page.keyboard.press('Escape');
    await expect(agentDialog).toHaveCount(0);
    await expect(openAgent).toBeFocused();
    const progress = overview.getByRole('list', { name: '第一集产物进度' });
    await expect(progress).toBeVisible();
    await expect(progress.locator('li')).toHaveCount(6);
    await expect(progress.getByRole('button')).toHaveCount(4);
    await expect(progress.getByRole('button', { name: '阅读分集大纲' })).toBeVisible();
    await expect(progress.getByRole('button', { name: '阅读剧本' })).toBeVisible();
    await expect(progress.getByRole('button', { name: '阅读分镜' })).toBeVisible();
    await expect(progress.getByRole('button', { name: '阅读审阅报告' })).toBeVisible();
    await expect(progress.getByRole('button', { name: '阅读Prompts' })).toHaveCount(0);
    await expect(progress.getByRole('button', { name: '阅读Renders' })).toHaveCount(0);
    await expect(progress.locator('li').nth(0)).toContainText('分集大纲已生成');
    expect(await progress.evaluate((element) => element.previousElementSibling?.tagName)).toBe('H2');
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'episode-overview-progress-desktop-1440x1000.png'),
      fullPage: true,
    });

    const readScript = progress.getByRole('button', { name: '阅读剧本' });
    await readScript.focus();
    await readScript.press('Enter');
    const reader = page.getByRole('region', { name: '第一集文件阅读器' });
    await expect(reader).toBeVisible();
    await expect(reader).toBeInViewport();
    await expect(page.locator('details').filter({ hasText: 'Dream 初稿阶段投影' }))
      .toHaveAttribute('open', '');
    await expect(reader.getByRole('tab', { name: /剧本/ })).toHaveAttribute('aria-selected', 'true');
    await expect(reader.getByRole('tab', { name: /剧本/ })).toBeFocused();
    await expect(reader.getByRole('tab', { name: /剧本/ })).toBeInViewport();
    await expect(reader.getByRole('article', { name: '剧本文件内容' })).toContainText('浮世行路');

    await progress.getByRole('button', { name: '阅读分镜' }).click();
    await expect(reader).toBeInViewport();
    await expect(reader.getByRole('tab', { name: /分镜/ })).toHaveAttribute('aria-selected', 'true');
    await expect(reader.getByRole('tab', { name: /分镜/ })).toBeFocused();
    await expect(reader.getByRole('tab', { name: /分镜/ })).toBeInViewport();
    await expect(reader.getByRole('navigation', { name: '分镜镜头导航' }).getByRole('button')).toHaveCount(22);
    await expect(reader.getByRole('article', { name: '分镜 YAML 属性' })).toContainText('镜头参数');

    await reader.getByRole('tab', { name: /分集大纲/ }).click();
    await expect(reader.getByRole('article', { name: '分集大纲文件内容' })).toContainText('下午的光');
    const outlineTab = reader.getByRole('tab', { name: /分集大纲/ });
    await outlineTab.focus();
    await outlineTab.press('ArrowRight');
    await expect(reader.getByRole('tab', { name: /剧本/ })).toHaveAttribute('aria-selected', 'true');
    await expect(reader.getByRole('article', { name: '剧本文件内容' })).toContainText('浮世行路');

    await progress.getByRole('button', { name: '阅读审阅报告' }).click();
    await expect(reader).toBeInViewport();
    await expect(reader.getByRole('tab', { name: /审阅/ })).toBeFocused();
    await expect(reader.getByRole('tab', { name: /审阅/ })).toBeInViewport();
    await expect(reader.getByRole('article', { name: '审阅文件内容' })).toContainText('审查报告');
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'episode-artifacts-desktop-1440x1000.png'),
      fullPage: true,
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await expect(reader).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(1);
    await page.evaluate(() => {
      const element = document.querySelector<HTMLElement>('nav[aria-label="第一集文件导航"]');
      if (element === null) throw new Error('Episode artifact navigation is missing.');
      element.scrollIntoView({ block: 'start' });
    });
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'episode-artifacts-narrow-390x844.png'),
    });
    await openAgent.click();
    agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
    disclosure = agentDialog.getByRole('button', { name: '更多工作流操作（4）' });
    await disclosure.click();
    await expect(agentDialog).toBeVisible();
    expect(await agentDialog.evaluate((element) => element.scrollWidth <= element.clientWidth + 1))
      .toBe(true);
    const overflowActionBoxes = await agentDialog.getByRole('group', {
      name: '更多 Episode 工作流操作',
    }).getByRole('button').evaluateAll((buttons) => buttons.map((button) => {
      const box = button.getBoundingClientRect();
      return {
        top: box.top,
        bottom: box.bottom,
        height: box.height,
        contentFits: button.scrollHeight <= button.clientHeight + 1,
      };
    }));
    expect(overflowActionBoxes.every((box, index) => (
      box.height >= 44
      && box.contentFits
      && (index === 0 || box.top >= (overflowActionBoxes[index - 1]?.bottom ?? 0) - 0.5)
    ))).toBe(true);
    await page.screenshot({
      path: resolve(EVIDENCE_DIR, 'workflow-actions-narrow-390x844.png'),
    });
    await page.keyboard.press('Escape');
    await page.keyboard.press('Escape');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toContain('/Users/');
    expect(bodyText).not.toContain('第一集产物来源无效');
    expect(apiFailures).toEqual([]);
    expect(diagnostics).toEqual([]);
    expect(episodeActionPosts).toEqual([]);
  } finally {
    await context.close();
  }
});
