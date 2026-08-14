// [Input] Existing local Dream Run, real actor, real model, and visible shared Chat composer.
// [Output] Human-journey proof of each dialogue through shared session, canonical
//          files, after-turn Hook, PostgreSQL/API projection, and Execution UI.
// [Pos] Opt-in real-data full-business Dream projection acceptance test.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_WORKBENCH_QA === '1';
const WEB_BASE = process.env.INK_REAL_WORKBENCH_WEB_BASE ?? 'http://127.0.0.1:5173';
const RUN_ID = process.env.INK_REAL_WORKBENCH_RUN_ID
  ?? 'run_8956be79389b4bd3aa40b5107a5bb233';
const THREAD_ID = process.env.INK_REAL_WORKBENCH_THREAD_ID
  ?? '9aa276b3-8333-5507-9ab5-c5e67c9ef610';
const ACTOR_EMAIL = process.env.INK_REAL_WORKBENCH_ACTOR_EMAIL
  ?? 'dmeck123@suoxya.com';
const EXPECTED_TITLE = process.env.INK_REAL_WORKBENCH_EXPECTED_TITLE
  ?? '隔壁的病友';
const EXPECTED_EPISODE_TITLE = process.env.INK_REAL_WORKBENCH_EXPECTED_EPISODE_TITLE
  ?? '凌晨五点的敲墙声';
const REPO_ROOT = resolve(process.cwd(), '..');
const BACKEND_DIR = resolve(REPO_ROOT, 'backend');
const BACKEND_PYTHON = resolve(BACKEND_DIR, '.venv/bin/python');

/**
 * Dream business concept and impact contract for this real Run:
 *
 * | Fact | Authority | Expected impact |
 * | Project title | project.yaml.project_name | becomes/stays `EXPECTED_TITLE`; Hook publishes it and Story Index/UI consume it |
 * | EP01 title/content | EP01 canonical artifacts | must remain `EXPECTED_EPISODE_TITLE`; a Project rename is not an Episode rewrite |
 * | Run-private files | .dream/runtime/runs/<run>/artifact + manifest | match current canonical Project facts after every successful turn |
 * | Thread/Claude session | chat_thread | same ids across both visible dialogues |
 * | Other assets/Episodes | canonical manifest | outside this scenario and must not be rewritten |
 */
const DREAM_IMPACT_SCOPE = Object.freeze({
  projectTitle: 'changes-or-idempotently-confirms',
  episodeTitle: 'must-remain-unchanged',
  threadAndSession: 'must-remain-unchanged',
  unrelatedArtifacts: 'out-of-scope',
});

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1200, height: 720 },
  launchOptions: { args: ['--window-position=20,20', '--window-size=1280,800'] },
});
test.skip(!ENABLED, 'Set INK_REAL_WORKBENCH_QA=1 to modify the named real Dream Run.');

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

interface ThreadFacts {
  readonly assistantId: string | null;
  readonly claudeSessionId: string | null;
  readonly model: string | null;
  readonly readPaths: readonly string[];
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
    "read_paths=[part.get('input',{}).get('file_path') for part in parts if isinstance(part,dict) and part.get('type')=='tool-invocation' and part.get('toolName')=='Read' and isinstance(part.get('input'),dict) and isinstance(part.get('input',{}).get('file_path'),str)]",
    "print(json.dumps({'assistantId':row['id'] if row else None,'claudeSessionId':thread['claude_session_id'] if thread else None,'model':metadata.get('chatModel',{}).get('model') if isinstance(metadata,dict) else None,'readPaths':read_paths}))",
  ].join(';'), [threadId])) as ThreadFacts;
}

interface StoryDatabaseFacts {
  readonly artifactSyncStatus: string | null;
  readonly projectTitle: string | null;
  readonly sourceRunId: string | null;
}

function readStoryDatabaseFacts(runId: string): StoryDatabaseFacts {
  return JSON.parse(runBackendScript([
    'from dotenv import load_dotenv',
    "load_dotenv('.env')",
    'import database,json,sys',
    'db=database.get_db()',
    "row=db.execute(\"select title,source_run_id,artifact_sync_status from story_workspace_stories where source_run_id=%s\",(sys.argv[1],)).fetchone()",
    'db.close()',
    "print(json.dumps({'projectTitle':row['title'] if row else None,'sourceRunId':row['source_run_id'] if row else None,'artifactSyncStatus':row['artifact_sync_status'] if row else None},ensure_ascii=False))",
  ].join(';'), [runId])) as StoryDatabaseFacts;
}

interface WorkspaceFacts {
  readonly projectSlug: string;
  readonly canonicalTitle: string;
  readonly privateTitle: string;
  readonly canonicalSha256: string;
  readonly privateSha256: string;
  readonly manifestSha256: string | null;
  readonly workbenchPath: string;
  readonly workbenchHasRun: boolean;
  readonly workbenchHasProject: boolean;
}

function readWorkspaceFacts(threadId: string, runId: string): WorkspaceFacts {
  return JSON.parse(runBackendScript([
    'from pathlib import Path',
    'import hashlib,json,os,sys,yaml',
    "root=(Path(os.environ.get('AGENT_CWD') or 'data/agent-workspace')/sys.argv[1]).resolve()",
    "projects=[p for p in (root/'stories').iterdir() if p.is_dir() and (p/'project.yaml').is_file()]",
    "assert len(projects)==1, f'expected one canonical project, got {len(projects)}'",
    'project=projects[0]',
    "canonical=(project/'project.yaml').read_bytes()",
    "private=root/'.dream'/'runtime'/'runs'/sys.argv[2]/'artifact'/'stories'/project.name/'project.yaml'",
    'private_bytes=private.read_bytes()',
    "manifest=json.loads((private.parents[2]/'manifest.json').read_text(encoding='utf-8'))",
    "entry=next((item for item in manifest['files'] if item['path']==f'stories/{project.name}/project.yaml'),None)",
    "workbench=(root/'.dream'/'WORKBENCH.md').read_text(encoding='utf-8')",
    "canonical_yaml=yaml.safe_load(canonical.decode('utf-8'))",
    "private_yaml=yaml.safe_load(private_bytes.decode('utf-8'))",
    "print(json.dumps({'projectSlug':project.name,'canonicalTitle':canonical_yaml.get('project_name'),'privateTitle':private_yaml.get('project_name'),'canonicalSha256':hashlib.sha256(canonical).hexdigest(),'privateSha256':hashlib.sha256(private_bytes).hexdigest(),'manifestSha256':entry.get('sha256') if entry else None,'workbenchPath':str(root/'.dream'/'WORKBENCH.md'),'workbenchHasRun':sys.argv[2] in workbench,'workbenchHasProject':project.name in workbench},ensure_ascii=False))",
  ].join(';'), [threadId, runId])) as WorkspaceFacts;
}

async function approveExpectedFileConfirmation(page: Page): Promise<boolean> {
  const dialog = page.locator('[role="alertdialog"]:visible');
  if (await dialog.count() === 0) return false;
  if (await dialog.count() !== 1) throw new Error('Multiple confirmation dialogs are visible.');
  const accessibleName = await dialog.first().getAttribute('aria-label');
  if (!accessibleName || !/(?:Edit|Write) 工具|(?:Edit|Write) tool/.test(accessibleName)) {
    throw new Error(`Unexpected confirmation dialog: ${accessibleName ?? 'unnamed'}`);
  }
  const approve = dialog.first().getByRole('button', { name: /^(同意|Approve)/ });
  await expect(approve).toBeInViewport();
  await approve.click();
  await expect(dialog.first()).toBeHidden({ timeout: 15_000 });
  return true;
}

async function sendDialogueAndWait(
  page: Page,
  request: string,
  before: ThreadFacts,
): Promise<ThreadFacts> {
  const composer = page.getByRole('textbox', { name: '聊天输入' });
  await expect(composer).toBeEnabled();
  await expect(composer).toBeInViewport();
  await composer.fill(request);
  await page.getByRole('button', { name: '发送消息' }).click();
  await expect(page.getByText(request, { exact: true }).last()).toBeVisible();

  let after = before;
  await expect.poll(async () => {
    await approveExpectedFileConfirmation(page);
    after = readThreadFacts(THREAD_ID);
    return after.assistantId === before.assistantId ? null : after.assistantId;
  }, {
    message: 'the visible real Dream turn should persist its assistant after Hook settlement',
    timeout: 300_000,
    intervals: [500, 1_000, 2_000],
  }).not.toBeNull();
  await expect(page.getByRole('button', { name: /停止生成|Stop generating/ })).toHaveCount(0);
  await expect(composer).toBeEnabled();
  return after;
}

async function expectExecutionProjection(page: Page, token: string): Promise<void> {
  await page.goto(`${WEB_BASE}/story-workspace/runs/${RUN_ID}/execution`);
  await expect(page.getByRole('heading', { level: 1, name: EXPECTED_TITLE })).toBeVisible();
  const projection = page.getByRole('region', { name: 'Dream 初稿工作台' });
  await expect(projection).toBeVisible();
  await expect(page.locator('#story-workspace-episode-title')).toHaveCount(0);
  await expect(page.getByText('工作空间更新流', { exact: true })).toHaveCount(0);
  await expect(page.getByText('stage revisions', { exact: true })).toHaveCount(0);
  await expect(page.getByText('Agent 工作空间历史', { exact: true })).toHaveCount(0);

  await projection.getByRole('tab', { name: /^Assets/ }).click();
  const assetIndex = projection.locator('#story-workspace-execution-index');
  await expect(assetIndex).toBeVisible();
  expect(await assetIndex.getByRole('button').count()).toBeGreaterThan(0);
  await assetIndex.getByRole('button').first().click();
  await expect(projection.getByRole('button', { name: '← 返回故事线' })).toBeVisible();
  await projection.getByRole('button', { name: '← 返回故事线' }).click();
  await projection.getByRole('tab', { name: /^Outline/ }).click();
  const outlineIndex = projection.locator('#story-workspace-execution-index');
  await expect(outlineIndex).toBeVisible();
  expect(await outlineIndex.getByRole('button').count()).toBeGreaterThan(0);

  await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
  const agentDialog = page.getByRole('dialog', { name: 'Dream Agent' });
  await agentDialog.getByRole('button', { name: '同步', exact: true }).click();
  await agentDialog.getByRole('button', { name: '收起 Dream Agent' }).click();
  await expect(page.locator('#story-workspace-episode-title'))
    .toHaveText(EXPECTED_EPISODE_TITLE);
  const response = await page.request.get(
    `${WEB_BASE}/api/story-workspace/workflow-runs/${RUN_ID}/story-index`,
    { headers: { authorization: `Bearer ${token}` } },
  );
  expect(response.status(), await response.text()).toBe(200);
  expect(await response.json()).toMatchObject({
    runId: RUN_ID,
    projectTitle: EXPECTED_TITLE,
    status: 'indexed',
  });
  expect(readStoryDatabaseFacts(RUN_ID)).toEqual({
    artifactSyncStatus: 'indexed',
    projectTitle: EXPECTED_TITLE,
    sourceRunId: RUN_ID,
  });
}

test('each dialogue completes the real Project projection and preserves session context', async ({
  browser,
}) => {
  test.setTimeout(360_000);
  const before = readThreadFacts(THREAD_ID);
  expect(DREAM_IMPACT_SCOPE).toEqual({
    projectTitle: 'changes-or-idempotently-confirms',
    episodeTitle: 'must-remain-unchanged',
    threadAndSession: 'must-remain-unchanged',
    unrelatedArtifacts: 'out-of-scope',
  });
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
    if (request.failure()?.errorText !== 'net::ERR_ABORTED') {
      diagnostics.push(`requestfailed: ${request.failure()?.errorText ?? 'failed'} ${request.url()}`);
    }
  });

  const token = createActorToken(ACTOR_EMAIL);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);

  try {
    await page.goto(`${WEB_BASE}/story-workspace/dream?run=${RUN_ID}`);
    await expect(page.getByRole('heading', { name: '创作工作空间' })).toBeVisible();
    await page.getByRole('button', { name: '打开 Dream Agent 消息' }).click();
    const mutationRequest = `请先按照本轮工作区要求读取服务端给出的 Dream 工作台上下文文件；确认当前项目后，把项目标题设为「${EXPECTED_TITLE}」。如果文件已经是这个标题，不要改写 Episode 标题，确认当前工作台同步即可。`;
    const afterMutation = await sendDialogueAndWait(page, mutationRequest, before);
    expect(afterMutation.model).toBe('deepseek-v4-pro');
    expect(afterMutation.claudeSessionId).toBeTruthy();

    const files = readWorkspaceFacts(THREAD_ID, RUN_ID);
    expect(files.canonicalTitle).toBe(EXPECTED_TITLE);
    expect(files.privateTitle).toBe(EXPECTED_TITLE);
    expect(files.canonicalSha256).toBe(files.privateSha256);
    expect(files.manifestSha256).toBe(files.canonicalSha256);
    expect(files.workbenchHasRun).toBe(true);
    expect(files.workbenchHasProject).toBe(true);
    expect(afterMutation.readPaths).toContain(files.workbenchPath);
    await expectExecutionProjection(page, token);

    const unchangedBefore = readWorkspaceFacts(THREAD_ID, RUN_ID);
    await page.getByRole('button', { name: '打开 Dream Agent 消息预览' }).click();
    const continuityRequest = '继续。请再次读取本轮 Dream 工作台上下文，告诉我当前项目标题和 EP01 标题分别是什么；这次只确认上下文，不要修改任何文件。';
    const afterContinuity = await sendDialogueAndWait(
      page,
      continuityRequest,
      afterMutation,
    );
    expect(afterContinuity.model).toBe('deepseek-v4-pro');
    expect(afterContinuity.claudeSessionId).toBe(afterMutation.claudeSessionId);
    expect(afterContinuity.readPaths).toContain(files.workbenchPath);
    expect(readWorkspaceFacts(THREAD_ID, RUN_ID)).toEqual(unchangedBefore);
    await expectExecutionProjection(page, token);

    const overflow = await page.evaluate(() => (
      document.documentElement.scrollWidth - document.documentElement.clientWidth
    ));
    expect(overflow).toBeLessThanOrEqual(1);
    expect(diagnostics).toEqual([]);
  } finally {
    await context.close();
  }
});
