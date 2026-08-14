// [Input] Named real Dream Run, real actor/model, visible shared Chat composer, and canonical asset workspace.
// [Output] Full human journey proving character/scene/prop/storyboard add, update, reference-safe delete, cleanup, Hook/API/UI.
// [Pos] Opt-in headless real-data Dream Agent asset-collaboration acceptance test.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_ASSET_QA === '1';
const WEB_BASE = process.env.INK_REAL_ASSET_QA_WEB_BASE ?? 'http://127.0.0.1:5173';
const RUN_ID = process.env.INK_REAL_ASSET_QA_RUN_ID
  ?? 'run_ddb53a9a261d497c98ad9a6c1ec3a1c2';
const THREAD_ID = process.env.INK_REAL_ASSET_QA_THREAD_ID
  ?? '5cb50934-c592-501d-9a37-8b058a1f413b';
const ACTOR_EMAIL = process.env.INK_REAL_ASSET_QA_ACTOR_EMAIL
  ?? 'dmeck123@suoxya.com';
const SUFFIX = process.env.INK_REAL_ASSET_QA_SUFFIX ?? 'codex-asset-0814';
const CHARACTER_ID = `qa-character-${SUFFIX}`;
const SCENE_ID = `qa-scene-${SUFFIX}`;
const SHOT_ID = `qa-shot-${SUFFIX}`;
const PROP_ID = `QA-PROP-${SUFFIX}`;
const CHARACTER_NAME = `临时场记-${SUFFIX}`;
const UPDATED_CHARACTER_NAME = `临时场记（短发）-${SUFFIX}`;
const SCENE_NAME = `临时器材帐篷-${SUFFIX}`;
const UPDATED_SCENE_NAME = `临时器材帐篷（雨夜）-${SUFFIX}`;
const PROP_NAME = `临时场记板-${SUFFIX}`;
const UPDATED_PROP_NAME = `临时雨夜场记板-${SUFFIX}`;
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');
const FACT_READER = resolve(process.cwd(), 'e2e/helpers/read_asset_collaboration_facts.py');

/**
 * Business concepts and impact matrix:
 *
 * | Fact | Authority | Expected impact |
 * | Character/scene/prop | canonical assets files | temporary add -> stable-ID update -> reference-safe delete |
 * | EP01 storyboard | canonical storyboard.yaml | temporary shot add -> update -> refs removed -> shot deleted |
 * | Run-private stages | successful after_main_turn Hook | only changed stage revisions advance; final items return to baseline |
 * | Project/other assets | existing canonical files | must remain unchanged |
 * | Shared conversation | Chat thread + Claude session | same IDs for all four visible turns |
 * | Public consumer | actor-scoped dream-files + Execution Assets/Outline | shows each post-turn fact after refresh |
 * | PostgreSQL Story | Project/Episode materialization | not directly changed by temporary stage-only assets |
 */
const DREAM_ASSET_IMPACT_SCOPE = Object.freeze({
  temporaryAssetsAndShot: 'add-update-reference-safe-delete',
  projectAndExistingAssets: 'must-remain-unchanged',
  sharedThreadAndSession: 'must-remain-unchanged',
  storyProjection: 'not-directly-changed',
});

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1200, height: 720 },
});
test.skip(!ENABLED, 'Set INK_REAL_ASSET_QA=1 to run the real asset collaboration journey.');

interface ToolFact {
  readonly name: string;
  readonly input: Record<string, unknown>;
  readonly state: string | null;
}

interface ThreadFacts {
  readonly assistantId: string | null;
  readonly claudeSessionId: string | null;
  readonly model: string | null;
  readonly text: string;
  readonly tools: readonly ToolFact[];
}

interface AssetEntry {
  readonly name: string;
  readonly path: string;
  readonly sha256: string;
  readonly text: string;
}

interface StagePayload {
  readonly revision: number;
  readonly items: ReadonlyArray<{
    readonly entity_id: string;
    readonly display_name: string;
  }>;
}

interface AssetFacts {
  readonly workspaceRoot: string;
  readonly projectSlug: string;
  readonly characters: Readonly<Record<string, AssetEntry>>;
  readonly scenes: Readonly<Record<string, AssetEntry>>;
  readonly props: Readonly<Record<string, AssetEntry>>;
  readonly storyboardPath: string;
  readonly storyboard: {
    readonly total_shots: number;
    readonly total_duration_sec: number;
    readonly shots: ReadonlyArray<Record<string, unknown>>;
  };
  readonly stages: Readonly<Record<'characters' | 'scenes' | 'storyboards', StagePayload>>;
  readonly workbenchPath: string;
  readonly assetContractPath: string;
  readonly workbenchExists: boolean;
  readonly assetContractExists: boolean;
}

function runBackendScript(source: string, args: readonly string[]): string {
  return execFileSync(BACKEND_PYTHON, ['-c', source, ...args], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim();
}

function createActorToken(email: string): string {
  return runBackendScript([
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import auth,database,sys',
    'db=database.get_db()',
    "user=db.execute(\"select id,email from users where email=%s and status='active'\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "assert user is not None, 'actor not found'",
    "print(auth.create_access_token(user['id'],user['email']))",
  ].join(';'), [email]);
}

function readThreadFacts(threadId: string): ThreadFacts {
  return JSON.parse(runBackendScript([
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import database,json,sys',
    'db=database.get_db()',
    "row=db.execute(\"select id,metadata,parts from chat_message where thread_id=%s and role='assistant' order by created_at desc limit 1\",(sys.argv[1],)).fetchone()",
    "thread=db.execute(\"select claude_session_id from chat_thread where id=%s\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "metadata=json.loads(row['metadata']) if row and isinstance(row['metadata'],str) else (row['metadata'] if row else {})",
    "parts=json.loads(row['parts']) if row and isinstance(row['parts'],str) else (row['parts'] if row else [])",
    "tools=[{'name':p.get('toolName'),'input':p.get('input') or {},'state':p.get('state')} for p in parts if isinstance(p,dict) and p.get('type')=='tool-invocation']",
    "text='\\n'.join(str(p.get('text') or '') for p in parts if isinstance(p,dict) and p.get('type')=='text')",
    "print(json.dumps({'assistantId':row['id'] if row else None,'claudeSessionId':thread['claude_session_id'] if thread else None,'model':metadata.get('chatModel',{}).get('model') if isinstance(metadata,dict) else None,'text':text,'tools':tools},ensure_ascii=False))",
  ].join(';'), [threadId])) as ThreadFacts;
}

function readAssetFacts(): AssetFacts {
  return JSON.parse(execFileSync(BACKEND_PYTHON, [FACT_READER, THREAD_ID, RUN_ID], {
    cwd: BACKEND_DIR,
    encoding: 'utf-8',
  }).trim()) as AssetFacts;
}

function shotById(facts: AssetFacts): Record<string, unknown> | undefined {
  return facts.storyboard.shots.find((shot) => shot.shot_id === SHOT_ID);
}

function readPaths(facts: ThreadFacts): string[] {
  return facts.tools
    .filter((tool) => tool.name === 'Read')
    .map((tool) => String(tool.input.file_path ?? ''));
}

async function approveExpectedConfirmation(page: Page): Promise<boolean> {
  const dialog = page.locator('[role="alertdialog"]:visible');
  if (await dialog.count() === 0) return false;
  if (await dialog.count() !== 1) throw new Error('Multiple confirmation dialogs are visible.');
  const label = await dialog.first().getAttribute('aria-label') ?? '';
  const content = await dialog.first().innerText();
  const fileTool = /(?:Edit|Write|MultiEdit) (?:工具|tool)/.test(label);
  const reviewedDelete = /Bash/.test(label)
    && content.includes('rm --')
    && (content.includes(CHARACTER_ID) || content.includes(SCENE_ID) || content.includes(PROP_ID))
    && !content.includes('.dream');
  if (!fileTool && !reviewedDelete) {
    throw new Error(`Unexpected confirmation dialog: ${label}\n${content}`);
  }
  const approve = dialog.first().getByRole('button', { name: /^(同意|Approve)/ });
  await expect(approve).toBeInViewport();
  await approve.click();
  await expect(dialog.first()).toBeHidden({ timeout: 15_000 });
  return true;
}

async function ensureAgentOpen(page: Page): Promise<void> {
  const composer = page.getByRole('textbox', { name: '聊天输入' });
  if (await composer.count() === 0 || !(await composer.isVisible())) {
    await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
  }
  await expect(composer).toBeVisible();
  await expect(composer).toBeEnabled();
}

async function sendTurn(page: Page, request: string, before: ThreadFacts): Promise<ThreadFacts> {
  await ensureAgentOpen(page);
  const composer = page.getByRole('textbox', { name: '聊天输入' });
  await composer.fill(request);
  await page.getByRole('button', { name: '发送消息' }).click();
  await expect(page.getByText(request, { exact: true }).last()).toBeVisible();
  let after = before;
  await expect.poll(async () => {
    await approveExpectedConfirmation(page);
    after = readThreadFacts(THREAD_ID);
    return after.assistantId === before.assistantId ? null : after.assistantId;
  }, {
    message: 'real Dream turn should persist only after Agent and Hook settle',
    timeout: 360_000,
    intervals: [500, 1_000, 2_000],
  }).not.toBeNull();
  await expect(page.getByRole('button', { name: /停止生成|Stop generating/ })).toHaveCount(0);
  await expect(composer).toBeEnabled();
  return after;
}

function expectContractsRead(turn: ThreadFacts, facts: AssetFacts): void {
  expect(readPaths(turn)).toContain(facts.workbenchPath);
  expect(readPaths(turn)).toContain(facts.assetContractPath);
  expect(turn.text.trim().startsWith('{')).toBe(false);
  expect(turn.model).toBe('deepseek-v4-pro');
}

async function readDreamFilesApi(page: Page, token: string): Promise<Record<string, unknown>> {
  const response = await page.request.get(
    `${WEB_BASE}/api/story-workspace/workflow-runs/${RUN_ID}/dream-files`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  expect(response.status(), await response.text()).toBe(200);
  return await response.json() as Record<string, unknown>;
}

async function expectVisibleAssets(
  page: Page,
  expectedNames: readonly string[],
  absentNames: readonly string[],
): Promise<void> {
  await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
  await expect(page.getByRole('heading', { level: 1, name: '雾中黑海湖' })).toBeVisible();
  const details = page.getByText('Dream 初稿阶段投影', { exact: true });
  await details.click();
  await page.getByRole('tab', { name: /Assets/ }).click();
  for (const name of expectedNames) {
    await expect(page.getByText(name, { exact: true })).toBeVisible();
  }
  for (const name of absentNames) {
    await expect(page.getByText(name, { exact: true })).toHaveCount(0);
  }
  await page.getByRole('tab', { name: /Outline/ }).click();
  await expect(page.getByText('EP01 分镜', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => (
    document.documentElement.scrollWidth - document.documentElement.clientWidth
  ))).toBeLessThanOrEqual(1);
}

test('real Agent completes full asset CRUD and restores the temporary facts', async ({ browser }) => {
  test.setTimeout(1_500_000);
  expect(DREAM_ASSET_IMPACT_SCOPE).toEqual({
    temporaryAssetsAndShot: 'add-update-reference-safe-delete',
    projectAndExistingAssets: 'must-remain-unchanged',
    sharedThreadAndSession: 'must-remain-unchanged',
    storyProjection: 'not-directly-changed',
  });
  const baseline = readAssetFacts();
  expect(baseline.characters[CHARACTER_ID]).toBeUndefined();
  expect(baseline.scenes[SCENE_ID]).toBeUndefined();
  expect(baseline.props[PROP_ID]).toBeUndefined();
  expect(shotById(baseline)).toBeUndefined();
  const baselineCharacterHashes = Object.fromEntries(
    Object.entries(baseline.characters).map(([id, asset]) => [id, asset.sha256]),
  );
  const baselineSceneHashes = Object.fromEntries(
    Object.entries(baseline.scenes).map(([id, asset]) => [id, asset.sha256]),
  );
  const baselinePropHashes = Object.fromEntries(
    Object.entries(baseline.props).map(([id, asset]) => [id, asset.sha256]),
  );
  const baselineSession = readThreadFacts(THREAD_ID).claudeSessionId;
  expect(baselineSession).toBeTruthy();

  const token = createActorToken(ACTOR_EMAIL);
  const context = await browser.newContext({ viewport: { width: 1200, height: 720 } });
  const page = await context.newPage();
  const diagnostics: string[] = [];
  page.on('pageerror', (error) => diagnostics.push(`pageerror: ${error.message}`));
  page.on('console', (message) => {
    if (message.type() === 'error' && !message.text().startsWith('Failed to load resource:')) {
      diagnostics.push(`console: ${message.text()}`);
    }
  });
  page.on('requestfailed', (request) => {
    const url = request.url();
    if (request.failure()?.errorText !== 'net::ERR_ABORTED'
      && !/(?:react-grab\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)/.test(url)) {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${url}`);
    }
  });
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  let latest = readThreadFacts(THREAD_ID);
  try {
    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);

    const addRequest = `请在当前 Dream 工作台完成一次真实资产新增：新增人物“${CHARACTER_NAME}”，固定 char_id 为 ${CHARACTER_ID}，描述为负责记录高原拍摄连续性；新增场景“${SCENE_NAME}”，固定 scene_id 为 ${SCENE_ID}，描述为存放相机与雨具的帐篷；新增道具“${PROP_NAME}”，固定 prop_id 为 ${PROP_ID}，描述为黑白拍板；并在 EP01 storyboard.yaml 新增 shot_id 为 "${SHOT_ID}" 的 3 秒 medium 镜头，scene_ref=${SCENE_ID}、characters 包含 ${CHARACTER_ID}、props 包含 ${PROP_ID}，visual 写“场记在器材帐篷举起场记板”。请先读取本轮两份 Dream 合同，必须写入真实 canonical 文件并正确重算分镜总数和总时长，不要只返回 JSON。`;
    latest = await sendTurn(page, addRequest, latest);
    let facts = readAssetFacts();
    expectContractsRead(latest, facts);
    expect(facts.characters[CHARACTER_ID]?.name).toBe(CHARACTER_NAME);
    expect(facts.scenes[SCENE_ID]?.name).toBe(SCENE_NAME);
    expect(facts.props[PROP_ID]?.name).toBe(PROP_NAME);
    expect(shotById(facts)).toMatchObject({
      scene_ref: SCENE_ID,
      characters: [CHARACTER_ID],
      props: [PROP_ID],
      visual: '场记在器材帐篷举起场记板',
    });
    expect(facts.storyboard.total_shots).toBe(facts.storyboard.shots.length);
    expect(facts.workbenchExists).toBe(true);
    expect(facts.assetContractExists).toBe(true);
    const addApi = await readDreamFilesApi(page, token) as {
      stages: Record<string, { items: Array<{ entityId: string; displayName: string }> }>;
    };
    expect(addApi.stages.characters.items).toEqual(expect.arrayContaining([
      expect.objectContaining({ entityId: CHARACTER_ID, displayName: CHARACTER_NAME }),
    ]));
    expect(addApi.stages.scenes.items).toEqual(expect.arrayContaining([
      expect.objectContaining({ entityId: SCENE_ID, displayName: SCENE_NAME }),
    ]));
    await expectVisibleAssets(page, [CHARACTER_NAME, SCENE_NAME], []);

    const stableCharacterPath = facts.characters[CHARACTER_ID].path;
    const stableScenePath = facts.scenes[SCENE_ID].path;
    const stablePropPath = facts.props[PROP_ID].path;
    const revisionsAfterAdd = Object.fromEntries(
      Object.entries(facts.stages).map(([stage, payload]) => [stage, payload.revision]),
    );
    const updateRequest = `继续修改刚新增的四个资产：保持 char_id=${CHARACTER_ID}、scene_id=${SCENE_ID}、prop_id=${PROP_ID}、shot_id="${SHOT_ID}" 和原文件路径不变；把人物显示名改为“${UPDATED_CHARACTER_NAME}”并补充“短发、黑色冲锋衣”；把场景名改为“${UPDATED_SCENE_NAME}”并补充“雨水敲击篷布”；把道具名改为“${UPDATED_PROP_NAME}”并补充“边缘贴有黄色胶带”；把该镜头 visual 改为“短发场记在雨夜器材帐篷举起贴黄胶带的场记板”，时长改为 5 秒。请读取两份合同和现有文件后直接编辑，并重算分镜总时长。`;
    const beforeUpdate = latest;
    latest = await sendTurn(page, updateRequest, latest);
    facts = readAssetFacts();
    expectContractsRead(latest, facts);
    expect(latest.claudeSessionId).toBe(beforeUpdate.claudeSessionId);
    expect(facts.characters[CHARACTER_ID]).toMatchObject({
      name: UPDATED_CHARACTER_NAME,
      path: stableCharacterPath,
    });
    expect(facts.characters[CHARACTER_ID].text).toContain('短发');
    expect(facts.scenes[SCENE_ID]).toMatchObject({
      name: UPDATED_SCENE_NAME,
      path: stableScenePath,
    });
    expect(facts.scenes[SCENE_ID].text).toContain('雨水敲击篷布');
    expect(facts.props[PROP_ID]).toMatchObject({
      name: UPDATED_PROP_NAME,
      path: stablePropPath,
    });
    expect(facts.props[PROP_ID].text).toContain('黄色胶带');
    expect(shotById(facts)).toMatchObject({
      shot_id: SHOT_ID,
      scene_ref: SCENE_ID,
      characters: [CHARACTER_ID],
      props: [PROP_ID],
      visual: '短发场记在雨夜器材帐篷举起贴黄胶带的场记板',
      timing: { duration_sec: 5 },
    });
    for (const stage of ['characters', 'scenes', 'storyboards'] as const) {
      expect(facts.stages[stage].revision).toBe(revisionsAfterAdd[stage] + 1);
    }
    await expectVisibleAssets(page, [UPDATED_CHARACTER_NAME, UPDATED_SCENE_NAME], [
      CHARACTER_NAME,
      SCENE_NAME,
    ]);

    const unlinkRequest = `现在明确删除人物 ${CHARACTER_ID}、场景 ${SCENE_ID} 和道具 ${PROP_ID}，但暂时保留镜头 ${SHOT_ID}。请先读取两份合同并检查引用；在同一轮先从这个镜头移除 characters 中的 ${CHARACTER_ID}、scene_ref=${SCENE_ID} 和 props 中的 ${PROP_ID}，保留镜头其他字段，然后分别使用三条精确的单文件 rm -- 命令删除对应人物、场景和道具文件。不得合并多目标命令，不得删除其他资产、镜头或目录，不得留下悬空引用。`;
    latest = await sendTurn(page, unlinkRequest, latest);
    facts = readAssetFacts();
    expectContractsRead(latest, facts);
    expect(facts.characters[CHARACTER_ID]).toBeUndefined();
    expect(facts.scenes[SCENE_ID]).toBeUndefined();
    expect(facts.props[PROP_ID]).toBeUndefined();
    const unlinkedShot = shotById(facts);
    expect(unlinkedShot).toBeDefined();
    expect(unlinkedShot?.scene_ref).toBeUndefined();
    expect(unlinkedShot?.characters ?? []).not.toContain(CHARACTER_ID);
    expect(unlinkedShot?.props ?? []).not.toContain(PROP_ID);
    const bashTools = latest.tools.filter((tool) => tool.name === 'Bash');
    for (const expectedId of [CHARACTER_ID, SCENE_ID, PROP_ID]) {
      const targetDeleteTools = bashTools.filter((tool) => {
        const command = String(tool.input.command ?? '');
        return command.startsWith('rm --') && command.includes(expectedId);
      });
      expect(targetDeleteTools.length).toBeGreaterThan(0);
      expect(targetDeleteTools.some((tool) => tool.state === 'output-available')).toBe(true);
    }
    await expectVisibleAssets(page, [], [UPDATED_CHARACTER_NAME, UPDATED_SCENE_NAME]);

    const cleanupRequest = `最后清理本次测试：从 EP01 storyboard.yaml 删除 shot_id="${SHOT_ID}" 这一项，只删除该临时镜头，保留其他镜头及其全部字段；然后正确重算 total_shots 和 total_duration_sec。人物 ${CHARACTER_ID} 与场景 ${SCENE_ID} 已删除，不要重建。请读取两份合同后直接编辑真实文件。`;
    latest = await sendTurn(page, cleanupRequest, latest);
    facts = readAssetFacts();
    expectContractsRead(latest, facts);
    expect(shotById(facts)).toBeUndefined();
    expect(facts.characters[CHARACTER_ID]).toBeUndefined();
    expect(facts.scenes[SCENE_ID]).toBeUndefined();
    expect(facts.props[PROP_ID]).toBeUndefined();
    expect(facts.storyboard.total_shots).toBe(facts.storyboard.shots.length);
    expect(Object.fromEntries(
      Object.entries(facts.characters).map(([id, asset]) => [id, asset.sha256]),
    )).toEqual(baselineCharacterHashes);
    expect(Object.fromEntries(
      Object.entries(facts.scenes).map(([id, asset]) => [id, asset.sha256]),
    )).toEqual(baselineSceneHashes);
    expect(Object.fromEntries(
      Object.entries(facts.props).map(([id, asset]) => [id, asset.sha256]),
    )).toEqual(baselinePropHashes);
    expect(latest.claudeSessionId).toBe(baselineSession);
    const finalApi = await readDreamFilesApi(page, token) as {
      stages: Record<string, { items: Array<{ entityId: string }> }>;
    };
    expect(finalApi.stages.characters.items.some((item) => item.entityId === CHARACTER_ID)).toBe(false);
    expect(finalApi.stages.scenes.items.some((item) => item.entityId === SCENE_ID)).toBe(false);
    await expectVisibleAssets(page, [], [CHARACTER_NAME, UPDATED_CHARACTER_NAME, SCENE_NAME, UPDATED_SCENE_NAME]);
    expect(diagnostics).toEqual([]);
  } finally {
    const remaining = readAssetFacts();
    if (remaining.characters[CHARACTER_ID] || remaining.scenes[SCENE_ID]
      || remaining.props[PROP_ID] || shotById(remaining)) {
      try {
        await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
        const beforeCleanup = readThreadFacts(THREAD_ID);
        await sendTurn(page, `清理刚才 ID 前缀为 ${SUFFIX} 的临时测试资产：先移除 EP01 中 shot_id="${SHOT_ID}" 及其引用，再分别使用三条单目标 rm -- 命令精确删除 char_id=${CHARACTER_ID}、scene_id=${SCENE_ID}、prop_id=${PROP_ID} 的单个文件；不要修改任何其他资产。`, beforeCleanup);
      } catch (error) {
        diagnostics.push(`best-effort Agent cleanup failed: ${String(error)}`);
      }
    }
    await context.close();
  }
});
