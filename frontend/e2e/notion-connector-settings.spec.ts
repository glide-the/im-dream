// [Input] Running Vite frontend plus production-shaped intercepted Notion connector, capability, Skill, and safe-file DTOs.
// [Output] Verify placeholders, strict seven-section overview, deferred discovery, four child views, safe links, responsive layout, and dialog-free disconnect.
// [Pos] Provider-free Notion Settings browser journey; it never calls Notion, a real backend, or business data.
// [Sync] 2026-08-29: cover the implemented detail redesign while retaining disabled Feishu/local CLI placeholders.
// [Sync] 2026-08-29: keep decorative section indices, redundant normal-state notices, and the four-item status summary absent from the overview.
// [Sync] 2026-08-29: require the compact overview to expose the real Read-hook and workspace-materializer operations.
// [Sync] 2026-08-29: lock the skeleton-proportioned overview without section subtitles, Skill summaries, resource counts, or recent-sync copy.
// [Sync] 2026-08-30: require ntn installation metadata and verify connected notion-cli is available through Agent Bash.
// [Sync] 2026-08-30: require the overview heading to identify the connector as Notion CLI.
// [Sync] 2026-08-30: classify Vite 8 HMR transport-send failures as harness diagnostics during isolated-port QA.

import { expect, test } from '@playwright/test';

const WEB_BASE = process.env.E2E_WEB_BASE ?? 'http://127.0.0.1:5173';

test.use({ channel: 'chrome', locale: 'zh-CN', viewport: { width: 1180, height: 820 } });

test('Notion Settings exposes the seven-section overview and focused child views', async ({ page }) => {
  const applicationDiagnostics: string[] = [];
  const harnessDiagnostics: string[] = [];
  const isViteHarnessDiagnostic = (text: string) => (
    text.includes('WebSocket connection to')
    || text.includes('[vite] failed to connect')
    || text.includes('Failed to send error to Vite server')
  );
  let deleteRequests = 0;
  let discoveryRequests = 0;
  let disconnected = false;
  page.on('console', (message) => {
    if (message.type() !== 'error') return;
    const text = message.text();
    if (isViteHarnessDiagnostic(text)) {
      harnessDiagnostics.push(text);
    } else {
      applicationDiagnostics.push(text);
    }
  });
  page.on('pageerror', (error) => applicationDiagnostics.push(error.message));
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (!url.includes('fonts.googleapis.com') && !url.includes('fonts.gstatic.com')) {
      applicationDiagnostics.push(`${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });

  const connector = {
    id: 'connector-1',
    name: 'Notion Resource Connector',
    platform: 'notion',
    auth_status: 'authenticated',
    created_at: '2026-08-29T00:00:00Z',
    updated_at: '2026-08-29T00:05:00Z',
    last_synced_at: '2026-08-29T00:04:00Z',
    config: {
      auth_error: 'The new authorization attempt expired.',
      auth_session: { auth_session_status: 'expired' },
    },
    sources: [{
      id: 'source-1',
      external_id: 'database-1',
      resource_type: 'notion_database',
      title: 'Team Knowledge',
      sync_status: 'synced',
      updated_at: '2026-08-29T00:04:00Z',
      last_synced_at: '2026-08-29T00:04:00Z',
      page_count: 2,
    }],
    sync_policy: {
      schema_version: 1,
      default: { enabled: true, interval_minutes: 15, revision: 1 },
      desired: { enabled: true, interval_minutes: 15, revision: 1 },
      effective: { enabled: true, interval_minutes: 15, revision: 1 },
      status: 'applied',
      last_attempt_at: '2026-08-29T00:05:00Z',
      last_success_at: '2026-08-29T00:04:00Z',
      next_sync_at: '2026-08-29T00:19:00Z',
      last_error_code: null,
      allowed_interval_minutes: [15, 60, 360, 1440],
    },
  };

  await page.route(`${WEB_BASE}/notion-connector-settings-harness`, async (route) => {
    await route.fulfill({
      contentType: 'text/html',
      body: '<!doctype html><html lang="zh-CN"><head><script type="module">import { injectIntoGlobalHook } from "/@react-refresh"; injectIntoGlobalHook(window); window.$RefreshReg$ = () => {}; window.$RefreshSig$ = () => (type) => type;</script><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/src/index.css"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/notionConnectorSettingsHarness.tsx"></script></body></html>',
    });
  });
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith('/api/')) {
      await route.continue();
      return;
    }
    if (request.method() === 'GET' && path === '/api/connectors') {
      await route.fulfill({ json: { connectors: disconnected ? [] : [connector] } });
      return;
    }
    if (request.method() === 'GET' && path === '/api/connectors/notion/capabilities') {
      const availability = disconnected ? 'requires_connection' : 'available';
      await route.fulfill({ json: { catalog: {
        schema_version: 4,
        package_revision: 'revision-1',
        cli_installation: { status: 'installed', required_version: '0.15.1', install_command: 'npm install -g ntn@0.15.1' },
        mcp_inventory: { status: 'not_integrated', revision: null, read_status: 'not_integrated', write_status: 'not_integrated' },
        skills: [
          { id: 'notion-session', title: 'Notion 工作空间助手', description: '只读搜索和读取当前用户已挂载的 Notion 内容', source: 'builtin', availability },
          { id: 'notion-cli', title: 'Notion CLI 工作空间数据助手', description: '通过 ntn CLI 访问 Notion', source: 'builtin', availability },
        ],
        operations: [
          { id: 'notion-page-read-hook', title: '按需读取页面正文', description: '只在回答需要时校验已选范围，并读取一个页面的最新 Markdown。', kind: 'read', source: 'runtime_hook', entrypoint: 'apply_notion_page_read_redirect', availability },
          { id: 'notion-workspace-snapshot-materialize', title: '挂载工作区轻量索引', description: '为当前对话挂载已选页面和数据库的标识与紧凑元数据；不包含页面正文，也不会写回 Notion。', kind: 'write', source: 'workspace_materializer', entrypoint: 'materialize_workspace_snapshot', availability },
        ],
      } } });
      return;
    }
    if (request.method() === 'GET' && path === '/api/connectors/notion/skills/notion-session') {
      await route.fulfill({ json: {
        package_revision: 'revision-1',
        skill: { id: 'notion-session', title: 'Notion 工作空间助手', description: '只读搜索和读取当前用户已挂载的 Notion 内容', source: 'builtin', availability: disconnected ? 'requires_connection' : 'available', tools: ['Read'], body: '# Notion 工作空间助手\n\n## 边界\n\n- 只读搜索、页面读取和数据库查询。\n- 不读取凭证。' },
        files: [
          { id: 'notion-search', relative_path: 'references/notion-search.md', media_type: 'text/markdown', size_bytes: 1536 },
          { id: 'notion-page-read', relative_path: 'references/notion-page-read.md', media_type: 'text/markdown', size_bytes: 2048 },
          { id: 'notion-db-query', relative_path: 'references/notion-db-query.md', media_type: 'text/markdown', size_bytes: 1024 },
        ],
      } });
      return;
    }
    if (request.method() === 'GET' && path === '/api/connectors/notion/skills/notion-cli') {
      await route.fulfill({ json: {
        package_revision: 'cli-revision-1',
        skill: { id: 'notion-cli', title: 'Notion CLI 工作空间数据助手', description: '通过 ntn CLI 访问 Notion', source: 'builtin', availability: disconnected ? 'requires_connection' : 'available', tools: ['Bash'], body: '# Notion CLI 工作空间数据助手\n\n## 核心命令速查\n\n```bash\nntn api v1/search --data \'{"query":"关键词"}\'\n```' },
        files: [
          { id: 'notion-search', relative_path: 'references/notion-search.md', media_type: 'text/markdown', size_bytes: 1536 },
          { id: 'notion-page-read', relative_path: 'references/notion-page-read.md', media_type: 'text/markdown', size_bytes: 2048 },
          { id: 'notion-db-query', relative_path: 'references/notion-db-query.md', media_type: 'text/markdown', size_bytes: 1024 },
        ],
      } });
      return;
    }
    if (request.method() === 'GET' && path === '/api/connectors/notion/skills/notion-session/files/notion-search') {
      expect(new URL(request.url()).searchParams.get('package_revision')).toBe('revision-1');
      await route.fulfill({ json: { package_revision: 'revision-1', file: { id: 'notion-search', relative_path: 'references/notion-search.md', media_type: 'text/markdown', size_bytes: 1536, content: '# Notion 搜索参考\n\n只在当前已挂载索引中定位页面。' } } });
      return;
    }
    if (request.method() === 'GET' && path.endsWith('/databases')) {
      discoveryRequests += 1;
      await route.fulfill({ json: { databases: [{ database_id: 'database-1', title: 'Team Knowledge', page_count: 2, selected: true }] } });
      return;
    }
    if (request.method() === 'GET' && path.endsWith('/pages')) {
      discoveryRequests += 1;
      await route.fulfill({ json: { pages: [{ page_id: 'page-1', title: 'Product Brief', selected: false }] } });
      return;
    }
    if (request.method() === 'DELETE' && path === '/api/connectors/connector-1') {
      deleteRequests += 1;
      disconnected = true;
      await route.fulfill({ json: { deleted: true } });
      return;
    }
    if (request.method() === 'GET' && path === '/api/claude-mcp/capability') {
      await route.fulfill({ json: { enabled: true, reason_code: null, management_mode: 'managed_db', schema_capability: 'dream.managed-mcp-resources.v1', schema_version: 1, transports: ['streamable_http', 'sse', 'stdio'] } });
      return;
    }
    if (request.method() === 'GET' && path === '/api/claude-mcp/servers') {
      await route.fulfill({ json: { servers: [] } });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: `unexpected ${request.method()} ${path}` } });
  });

  let dialogCount = 0;
  page.on('dialog', async (dialog) => {
    dialogCount += 1;
    await dialog.dismiss();
  });

  await page.goto(`${WEB_BASE}/notion-connector-settings-harness`);
  await expect.poll(async () => JSON.stringify({ body: await page.locator('body').innerText(), diagnostics: applicationDiagnostics })).toContain('资源链接');
  const feishuPlaceholder = page.getByRole('button', { name: /飞书/ });
  await expect(feishuPlaceholder).toBeDisabled();
  await expect(feishuPlaceholder).toContainText('占位');
  const localCliPlaceholder = page.getByRole('button', { name: /CLI 执行器/ });
  await expect(localCliPlaceholder).toBeDisabled();
  await expect(localCliPlaceholder).toContainText('暂不可用');
  await page.getByRole('button', { name: /Notion/ }).click();

  await expect(page.getByRole('heading', { name: 'Notion CLI', exact: true })).toBeVisible();
  await expect(page.getByText('部分可用', { exact: true })).toBeVisible();
  await expect(page.locator('.notion-detail__section-index')).toHaveCount(0);
  await expect(page.locator('.notion-detail__notice')).toHaveCount(0);
  await expect(page.locator('.notion-detail__facts')).toHaveCount(0);
  expect(await page.locator('.notion-detail__section h2').allTextContents()).toEqual([
    '权限', 'Skills', '读取操作', '写入操作', '资源范围', '已挂载来源', '信息',
  ]);
  expect(await page.locator('.notion-detail__section-body').first().evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(' ').length)).toBe(2);
  await expect(page.locator('.notion-detail__section-header p')).toHaveCount(0);
  await expect(page.getByText('只读搜索和读取当前用户已挂载的 Notion 内容', { exact: true })).toHaveCount(0);
  await expect(page.getByText('按需读取页面正文', { exact: true })).toBeVisible();
  await expect(page.getByText('挂载工作区轻量索引', { exact: true })).toBeVisible();
  await expect(page.getByText('已选择 1 个资源', { exact: true })).toHaveCount(0);
  await expect(page.getByText(/最近成功/)).toHaveCount(0);
  await expect(page.getByText('2026年8月29日')).toBeVisible();
  await expect(page.getByRole('link', { name: '网站（在新窗口打开）' })).toHaveAttribute('href', 'https://developers.notion.com/cli/get-started/overview');
  await expect(page.getByRole('link', { name: '隐私政策（在新窗口打开）' })).toHaveAttribute('href', 'https://privacycenter.notion.so/policies');
  await expect(page.getByRole('link', { name: '服务条款（在新窗口打开）' })).toHaveAttribute('target', '_blank');
  expect(discoveryRequests).toBe(0);
  expect(await page.locator('.notion-detail').evaluate((root) => [...root.querySelectorAll<HTMLElement>('*')].filter((element) => {
    const style = getComputedStyle(element);
    return ['auto', 'scroll'].includes(style.overflowY) && element.scrollHeight > element.clientHeight + 1;
  }).length)).toBe(0);
  if (process.env.INK_CAPTURE_NOTION_QA === '1') {
    await page.screenshot({ path: '../output/playwright/notion-detail-wide.png', fullPage: true });
  }

  const skillTrigger = page.getByRole('button', { name: /Notion 工作空间助手/ });
  const cliSkillTrigger = page.getByRole('button', { name: /Notion CLI 工作空间数据助手/ });
  await expect(cliSkillTrigger).toBeVisible();
  await expect(cliSkillTrigger).toContainText('可用');
  await skillTrigger.click();
  await expect(page.getByRole('heading', { name: 'Skill 说明' })).toBeVisible();
  await expect(page.getByText('不读取凭证。')).toBeVisible();
  await expect(page.getByRole('button', { name: /references\/notion-search\.md/ })).toBeVisible();
  const fileTrigger = page.getByRole('button', { name: /references\/notion-search\.md/ });
  await fileTrigger.click();
  await expect(page.getByRole('heading', { name: 'references/notion-search.md' })).toBeVisible();
  await expect(page.getByText('只在当前已挂载索引中定位页面。')).toBeVisible();
  await page.getByRole('button', { name: '包含的文件' }).click();
  await expect(fileTrigger).toBeFocused();
  await page.getByRole('button', { name: 'Notion', exact: true }).click();
  await expect(skillTrigger).toBeFocused();
  await cliSkillTrigger.click();
  await expect(page.getByRole('heading', { name: 'Skill 说明' })).toBeVisible();
  await expect(page.getByText('ntn api v1/search', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Notion', exact: true }).click();
  await expect(cliSkillTrigger).toBeFocused();
  expect(discoveryRequests).toBe(0);

  const resourceTrigger = page.getByRole('button', { name: /管理资源范围/ });
  await resourceTrigger.click();
  await expect(page.getByRole('heading', { name: '资源范围', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Team Knowledge/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /Product Brief/ })).toBeVisible();
  expect(discoveryRequests).toBe(2);
  await page.getByRole('button', { name: 'Notion', exact: true }).click();
  await expect(resourceTrigger).toBeFocused();

  await page.getByRole('button', { name: /管理已挂载来源/ }).click();
  await expect(page.getByRole('heading', { name: '已挂载来源', exact: true })).toBeVisible();
  await expect(page.getByText('Team Knowledge')).toBeVisible();
  await page.getByRole('button', { name: 'Notion', exact: true }).click();

  await page.setViewportSize({ width: 390, height: 780 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  expect(await page.locator('.notion-detail__section h2').allTextContents()).toEqual([
    '权限', 'Skills', '读取操作', '写入操作', '资源范围', '已挂载来源', '信息',
  ]);
  expect(await page.locator('.notion-detail__section-body').first().evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(' ').length)).toBe(1);
  expect(await page.getByRole('button', { name: '管理资源范围' }).evaluate((element) => getComputedStyle(element).flexDirection)).toBe('row');
  if (process.env.INK_CAPTURE_NOTION_QA === '1') {
    await page.screenshot({ path: '../output/playwright/notion-detail-narrow.png', fullPage: true });
  }

  await page.locator('summary[aria-label="更多 Notion 操作"]').click();
  await page.getByRole('button', { name: '关闭连接' }).click();
  await expect.poll(() => deleteRequests).toBe(1);
  expect(dialogCount).toBe(0);
  await expect(page.getByRole('button', { name: '连接 Notion' })).toBeVisible();
  await expect(page.getByText('未连接', { exact: true })).toBeVisible();
  expect(applicationDiagnostics).toEqual([]);
  expect(harnessDiagnostics.every(isViteHarnessDiagnostic)).toBe(true);
});
