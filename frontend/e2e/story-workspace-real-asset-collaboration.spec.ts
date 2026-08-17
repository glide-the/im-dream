// [Input] Named real Dream Run, real actor/model, visible shared Chat composer, and canonical asset workspace.
// [Output] Human-language journey proving character/scene/prop/storyboard add, update, reference-safe delete, cleanup, Hook/API/UI.
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
const SUFFIX = process.env.INK_REAL_ASSET_QA_SUFFIX ?? '0814甲';
const CHARACTER_NAME = `场记小岚（${SUFFIX}）`;
const UPDATED_CHARACTER_NAME = `短发场记小岚（${SUFFIX}）`;
const SCENE_NAME = `备用雨棚（${SUFFIX}）`;
const UPDATED_SCENE_NAME = `雨夜备用雨棚（${SUFFIX}）`;
const PROP_NAME = `蓝边场记板（${SUFFIX}）`;
const UPDATED_PROP_NAME = `黄胶带蓝边场记板（${SUFFIX}）`;
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');
const FACT_READER = resolve(process.cwd(), 'e2e/helpers/read_asset_collaboration_facts.py');

/**
 * Business concepts and impact matrix:
 *
 * | User-visible concept | Authority | Expected impact |
 * | “小岚/刚才那个人” | canonical character file | add -> same-identity update -> reference-safe delete |
 * | “雨棚/刚才那个场景” | canonical scene file | add -> same-identity update -> reference-safe delete |
 * | “场记板/刚才那个道具” | canonical prop file | add -> same-identity update -> reference-safe delete |
 * | “第一集最后那个镜头” | EP01 storyboard.yaml item | add -> same-identity update -> unlink -> delete |
 * | Run-private stages | successful after_main_turn Hook | only file facts drive revisions/projection |
 * | Project/other assets | existing canonical files | must remain unchanged |
 * | Shared conversation | Chat thread + Claude session | same IDs and real model across all turns |
 * | Public consumer | actor-scoped dream-files + Execution Assets/Outline | shows each settled post-turn fact |
 *
 * The visible requests deliberately contain no internal ID, file path, file name,
 * `.dream`, Hook, canonical, tool, or shell terminology. Internal identities are
 * discovered only after the first turn and are used solely for acceptance evidence.
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
  readonly output: unknown;
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

interface CreatedFacts {
  readonly characterId: string;
  readonly character: AssetEntry;
  readonly sceneId: string;
  readonly scene: AssetEntry;
  readonly propId: string;
  readonly prop: AssetEntry;
  readonly shotId: string;
  readonly shot: Record<string, unknown>;
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
    "tools=[{'name':p.get('toolName'),'input':p.get('input') or {},'state':p.get('state'),'output':p.get('output')} for p in parts if isinstance(p,dict) and p.get('type')=='tool-invocation']",
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

function newKeys<T>(before: Readonly<Record<string, T>>, after: Readonly<Record<string, T>>): string[] {
  return Object.keys(after).filter((key) => before[key] === undefined);
}

function newShotIds(before: AssetFacts, after: AssetFacts): string[] {
  const previous = new Set(before.storyboard.shots.map((shot) => String(shot.shot_id ?? '')));
  return after.storyboard.shots
    .map((shot) => String(shot.shot_id ?? ''))
    .filter((id) => id.length > 0 && !previous.has(id));
}

function shotById(facts: AssetFacts, shotId: string): Record<string, unknown> | undefined {
  return facts.storyboard.shots.find((shot) => shot.shot_id === shotId);
}

function readPaths(facts: ThreadFacts): string[] {
  return facts.tools
    .filter((tool) => tool.name === 'Read')
    .map((tool) => String(tool.input.file_path ?? ''));
}

async function approveExpectedConfirmation(
  page: Page,
  reviewedDeletePaths: readonly string[],
): Promise<boolean> {
  const dialog = page.locator('[role="alertdialog"]:visible');
  if (await dialog.count() === 0) return false;
  if (await dialog.count() !== 1) throw new Error('Multiple confirmation dialogs are visible.');
  const label = await dialog.first().getAttribute('aria-label') ?? '';
  const content = await dialog.first().innerText();
  const fileTool = /(?:Edit|Write|MultiEdit) (?:工具|tool)/.test(label)
    && !content.includes('.dream');
  const reviewedDelete = /Bash/.test(label)
    && content.includes('rm --')
    && reviewedDeletePaths.some((path) => content.includes(path))
    && !content.includes('.dream')
    && !content.includes('*')
    && !/\brm\s+-[^-]*r/.test(content);
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

async function sendTurn(
  page: Page,
  request: string,
  before: ThreadFacts,
  reviewedDeletePaths: readonly string[] = [],
): Promise<ThreadFacts> {
  await ensureAgentOpen(page);
  const composer = page.getByRole('textbox', { name: '聊天输入' });
  await composer.fill(request);
  await page.getByRole('button', { name: '发送消息' }).click();
  await expect(page.getByText(request, { exact: true }).last()).toBeVisible();
  let after = before;
  await expect.poll(async () => {
    await approveExpectedConfirmation(page, reviewedDeletePaths);
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

function expectSuccessfulDeleteReceipt(turn: ThreadFacts, relativePath: string): void {
  const tools = turn.tools.filter((tool) => {
    const command = String(tool.input.command ?? '');
    return tool.name === 'Bash' && command.includes('rm --') && command.includes(relativePath);
  });
  expect(tools.length, `missing visible delete receipt for ${relativePath}`).toBeGreaterThan(0);
  expect(tools.some((tool) => tool.state === 'output-available')).toBe(true);
  const output = JSON.stringify(tools.map((tool) => tool.output));
  expect(output).not.toContain('operation not permitted');
  expect(output).not.toContain('cwd-');
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
  await expect(page.locator('h1').first()).toBeVisible();
  const draft = page.getByRole('region', { name: 'Dream 初稿工作台' });
  await expect(draft).toBeVisible();
  await draft.getByRole('tab', { name: /Assets/ }).click();
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

test('real Agent completes a human-language asset journey and restores temporary facts', async ({ browser }) => {
  test.setTimeout(1_500_000);
  expect(DREAM_ASSET_IMPACT_SCOPE).toEqual({
    temporaryAssetsAndShot: 'add-update-reference-safe-delete',
    projectAndExistingAssets: 'must-remain-unchanged',
    sharedThreadAndSession: 'must-remain-unchanged',
    storyProjection: 'not-directly-changed',
  });
  const baseline = readAssetFacts();
  expect(Object.values(baseline.characters).some((asset) => asset.name === CHARACTER_NAME)).toBe(false);
  expect(Object.values(baseline.scenes).some((asset) => asset.name === SCENE_NAME)).toBe(false);
  expect(Object.values(baseline.props).some((asset) => asset.name === PROP_NAME)).toBe(false);
  const baselineCharacterHashes = Object.fromEntries(
    Object.entries(baseline.characters).map(([id, asset]) => [id, asset.sha256]),
  );
  const baselineSceneHashes = Object.fromEntries(
    Object.entries(baseline.scenes).map(([id, asset]) => [id, asset.sha256]),
  );
  const baselinePropHashes = Object.fromEntries(
    Object.entries(baseline.props).map(([id, asset]) => [id, asset.sha256]),
  );
  const baselineShotIds = baseline.storyboard.shots.map((shot) => String(shot.shot_id ?? ''));
  const baselineTotalDuration = baseline.storyboard.total_duration_sec;
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
  let created: CreatedFacts | null = null;
  try {
    await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);

    const addRequest = `给这个故事加一个叫“${CHARACTER_NAME}”的场记姑娘，她负责记录高原拍摄的连续性；再加一个叫“${SCENE_NAME}”的临时场景，里面存放相机和雨具；她随身有一块“${PROP_NAME}”。第一集结尾再补一个三秒的中景：她在那个雨棚里举起那块场记板。`;
    latest = await sendTurn(page, addRequest, latest);
    let facts = readAssetFacts();
    expectContractsRead(latest, facts);
    const characterIds = newKeys(baseline.characters, facts.characters);
    const sceneIds = newKeys(baseline.scenes, facts.scenes);
    const propIds = newKeys(baseline.props, facts.props);
    const shotIds = newShotIds(baseline, facts);
    expect(characterIds).toHaveLength(1);
    expect(sceneIds).toHaveLength(1);
    expect(propIds).toHaveLength(1);
    expect(shotIds).toHaveLength(1);
    const characterId = characterIds[0];
    const sceneId = sceneIds[0];
    const propId = propIds[0];
    const shotId = shotIds[0];
    const shot = shotById(facts, shotId);
    expect(facts.characters[characterId]?.name).toBe(CHARACTER_NAME);
    expect(facts.scenes[sceneId]?.name).toBe(SCENE_NAME);
    expect(facts.props[propId]?.name).toBe(PROP_NAME);
    expect(shot).toMatchObject({
      scene_ref: sceneId,
      characters: expect.arrayContaining([characterId]),
      props: expect.arrayContaining([propId]),
      timing: { duration_sec: 3 },
    });
    expect(String(shot?.visual ?? '')).toContain('场记');
    expect(facts.storyboard.total_shots).toBe(facts.storyboard.shots.length);
    expect(facts.storyboard.total_duration_sec).toBe(baselineTotalDuration + 3);
    expect(facts.workbenchExists).toBe(true);
    expect(facts.assetContractExists).toBe(true);
    created = {
      characterId,
      character: facts.characters[characterId],
      sceneId,
      scene: facts.scenes[sceneId],
      propId,
      prop: facts.props[propId],
      shotId,
      shot: shot ?? {},
    };
    const addApi = await readDreamFilesApi(page, token) as {
      stages: Record<string, { items: Array<{ entityId: string; displayName: string }> }>;
    };
    expect(addApi.stages.characters.items).toEqual(expect.arrayContaining([
      expect.objectContaining({ entityId: characterId, displayName: CHARACTER_NAME }),
    ]));
    expect(addApi.stages.scenes.items).toEqual(expect.arrayContaining([
      expect.objectContaining({ entityId: sceneId, displayName: SCENE_NAME }),
    ]));
    await expectVisibleAssets(page, [CHARACTER_NAME, SCENE_NAME], []);

    const revisionsAfterAdd = Object.fromEntries(
      Object.entries(facts.stages).map(([stage, payload]) => [stage, payload.revision]),
    );
    const updateRequest = `把刚才的小岚改成短发、穿黑色冲锋衣，页面上的名字也改成“${UPDATED_CHARACTER_NAME}”；刚才的雨棚改成雨夜环境，名字改成“${UPDATED_SCENE_NAME}”，能听见雨水敲击篷布；她的场记板边缘贴上黄色胶带，名字改成“${UPDATED_PROP_NAME}”；刚加在第一集结尾的镜头改成五秒，画面要能看见这些变化。`;
    const beforeUpdate = latest;
    latest = await sendTurn(page, updateRequest, latest);
    facts = readAssetFacts();
    expectContractsRead(latest, facts);
    expect(latest.claudeSessionId).toBe(beforeUpdate.claudeSessionId);
    expect(facts.characters[characterId]).toMatchObject({
      name: UPDATED_CHARACTER_NAME,
      path: created.character.path,
    });
    expect(facts.characters[characterId].text).toContain('短发');
    expect(facts.scenes[sceneId]).toMatchObject({
      name: UPDATED_SCENE_NAME,
      path: created.scene.path,
    });
    expect(facts.scenes[sceneId].text).toContain('雨水敲击篷布');
    expect(facts.props[propId]).toMatchObject({
      name: UPDATED_PROP_NAME,
      path: created.prop.path,
    });
    expect(facts.props[propId].text).toContain('黄色胶带');
    expect(shotById(facts, shotId)).toMatchObject({
      shot_id: shotId,
      scene_ref: sceneId,
      characters: expect.arrayContaining([characterId]),
      props: expect.arrayContaining([propId]),
      timing: { duration_sec: 5 },
    });
    expect(String(shotById(facts, shotId)?.visual ?? '')).toContain('短发');
    expect(facts.storyboard.total_duration_sec).toBe(baselineTotalDuration + 5);
    for (const stage of ['characters', 'scenes', 'storyboards'] as const) {
      expect(facts.stages[stage].revision).toBe(revisionsAfterAdd[stage] + 1);
    }
    await expectVisibleAssets(page, [UPDATED_CHARACTER_NAME, UPDATED_SCENE_NAME], [
      CHARACTER_NAME,
      SCENE_NAME,
    ]);

    const deletePaths = [created.character.path, created.scene.path, created.prop.path];
    const unlinkRequest = '删掉刚才的小岚、备用雨棚和那块场记板，但先保留第一集结尾刚加的镜头。把镜头里对这三项的关联一起清掉，其他故事内容都不要动。';
    latest = await sendTurn(page, unlinkRequest, latest, deletePaths);
    facts = readAssetFacts();
    expectContractsRead(latest, facts);
    expect(facts.characters[characterId]).toBeUndefined();
    expect(facts.scenes[sceneId]).toBeUndefined();
    expect(facts.props[propId]).toBeUndefined();
    const unlinkedShot = shotById(facts, shotId);
    expect(unlinkedShot).toBeDefined();
    expect(unlinkedShot?.scene_ref).toBeUndefined();
    expect(unlinkedShot?.characters ?? []).not.toContain(characterId);
    expect(unlinkedShot?.props ?? []).not.toContain(propId);
    for (const path of deletePaths) expectSuccessfulDeleteReceipt(latest, path);
    await expectVisibleAssets(page, [], [UPDATED_CHARACTER_NAME, UPDATED_SCENE_NAME]);

    const cleanupRequest = '第一集结尾刚才新增的那个测试镜头现在也删掉，其他镜头一个都不要动，总镜头数和总时长要保持正确。';
    latest = await sendTurn(page, cleanupRequest, latest);
    facts = readAssetFacts();
    expectContractsRead(latest, facts);
    expect(shotById(facts, shotId)).toBeUndefined();
    expect(facts.characters[characterId]).toBeUndefined();
    expect(facts.scenes[sceneId]).toBeUndefined();
    expect(facts.props[propId]).toBeUndefined();
    expect(facts.storyboard.total_shots).toBe(facts.storyboard.shots.length);
    expect(facts.storyboard.shots.map((item) => String(item.shot_id ?? ''))).toEqual(baselineShotIds);
    expect(facts.storyboard.total_duration_sec).toBe(baselineTotalDuration);
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
    expect(finalApi.stages.characters.items.some((item) => item.entityId === characterId)).toBe(false);
    expect(finalApi.stages.scenes.items.some((item) => item.entityId === sceneId)).toBe(false);
    await expectVisibleAssets(page, [], [
      CHARACTER_NAME,
      UPDATED_CHARACTER_NAME,
      SCENE_NAME,
      UPDATED_SCENE_NAME,
    ]);
    expect(diagnostics).toEqual([]);
  } finally {
    const remaining = readAssetFacts();
    const createdCharacter = created && remaining.characters[created.characterId];
    const createdScene = created && remaining.scenes[created.sceneId];
    const createdProp = created && remaining.props[created.propId];
    const createdShot = created && shotById(remaining, created.shotId);
    if (created && (createdCharacter || createdScene || createdProp || createdShot)) {
      try {
        await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
        const beforeCleanup = readThreadFacts(THREAD_ID);
        const cleanupPaths = [createdCharacter?.path, createdScene?.path, createdProp?.path]
          .filter((value): value is string => Boolean(value));
        await sendTurn(
          page,
          `把这次刚加的“${CHARACTER_NAME}”“${UPDATED_CHARACTER_NAME}”“${SCENE_NAME}”“${UPDATED_SCENE_NAME}”“${PROP_NAME}”“${UPDATED_PROP_NAME}”以及第一集结尾与它们一起新增的镜头清理掉，其他内容不要修改。`,
          beforeCleanup,
          cleanupPaths,
        );
      } catch (error) {
        diagnostics.push(`best-effort Agent cleanup failed: ${String(error)}`);
      }
    }
    await context.close();
  }
});
