// [Input] Named real actor/Chat Deck, normal local Dream services, and the exact candidate Runtime process boundary.
// [Output] Visible Chat proof that one test-owned Runtime crash becomes a safe error and the same Thread recovers.
// [Pos] Opt-in destructive release harness; it can signal only the sole new Runtime leaf beneath the named backend PID.
// [Sync] 2026-08-25: add fail-closed real Runtime SIGKILL and same-Thread recovery acceptance.

// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { execFileSync } from 'node:child_process';
// @ts-expect-error Playwright E2E uses Node built-ins outside the browser app tsconfig.
import { realpathSync, statSync } from 'node:fs';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const ENABLED = process.env.INK_REAL_CLAUDE_RUNTIME_FAILURE_QA === '1';
const WEB_BASE = process.env.INK_REAL_CLAUDE_RUNTIME_FAILURE_WEB_BASE
  ?? 'http://127.0.0.1:5173';
const API_BASE = process.env.INK_REAL_CLAUDE_RUNTIME_FAILURE_API_BASE
  ?? 'http://127.0.0.1:8765';
const ACTOR_EMAIL = process.env.INK_REAL_CLAUDE_RUNTIME_FAILURE_EMAIL ?? '';
const CHAT_DECK_ID = process.env.INK_REAL_CLAUDE_RUNTIME_FAILURE_DECK_ID ?? '';
const BACKEND_PID = Number(process.env.INK_REAL_CLAUDE_RUNTIME_FAILURE_BACKEND_PID ?? '0');
const RUNTIME_RELEASE_ROOT = process.env.INK_REAL_CLAUDE_RUNTIME_FAILURE_RELEASE_ROOT ?? '';
const BACKEND_DIR = new URL('../../backend/', import.meta.url).pathname;
const BACKEND_PYTHON = `${BACKEND_DIR}.venv/bin/python`;

test.use({
  channel: 'chromium',
  timezoneId: 'Asia/Shanghai',
  viewport: { width: 1280, height: 900 },
});
test.skip(!ENABLED, 'Run only with the explicit real Runtime-failure acceptance inputs.');

type ProcessRow = {
  readonly pid: number;
  readonly ppid: number;
  readonly command: string;
};

type ThreadStatus = {
  readonly running: boolean;
  readonly lifecycle: 'idle' | 'running' | 'destroyed' | 'not_found';
  readonly turn_count: number;
};

type ThreadMessages = {
  readonly messages: Array<{
    readonly role: string;
    readonly parts: Array<{ readonly type?: string; readonly text?: string }>;
  }>;
};

function requireInputs(): string {
  if (!ACTOR_EMAIL || !CHAT_DECK_ID || !RUNTIME_RELEASE_ROOT) {
    throw new Error('Actor, Chat Deck, and candidate Runtime release root are required.');
  }
  if (!Number.isSafeInteger(BACKEND_PID) || BACKEND_PID <= 1) {
    throw new Error('The exact backend PID is required.');
  }
  const releaseRoot = realpathSync(RUNTIME_RELEASE_ROOT);
  if (!statSync(releaseRoot).isDirectory()) {
    throw new Error('The candidate Runtime release root must be a directory.');
  }
  return releaseRoot;
}

function createActorToken(email: string): string {
  const source = [
    'from pathlib import Path',
    'from dotenv import load_dotenv',
    'load_dotenv(Path.cwd() / ".env", override=False)',
    'import auth,database,sys',
    'db=database.get_db()',
    'user=db.execute("select id,email from users where email=%s and status=\'active\'",(sys.argv[1],)).fetchone()',
    'db.close()',
    'assert user is not None',
    'print(auth.create_access_token(user["id"],user["email"]))',
  ].join(';');
  return execFileSync(BACKEND_PYTHON, ['-c', source, email], {
    cwd: BACKEND_DIR,
    encoding: 'utf8',
  }).trim();
}

function processSnapshot(): Map<number, ProcessRow> {
  const output = execFileSync('/bin/ps', ['-axo', 'pid=,ppid=,command='], {
    encoding: 'utf8',
  });
  const rows = new Map<number, ProcessRow>();
  for (const line of output.split('\n')) {
    const match = /^\s*(\d+)\s+(\d+)\s+(.*)$/.exec(line);
    if (!match) continue;
    const row = {
      pid: Number(match[1]),
      ppid: Number(match[2]),
      command: match[3],
    };
    rows.set(row.pid, row);
  }
  return rows;
}

function isDescendant(
  rows: ReadonlyMap<number, ProcessRow>,
  candidatePid: number,
  ancestorPid: number,
): boolean {
  const seen = new Set<number>();
  let cursor = rows.get(candidatePid);
  while (cursor && cursor.ppid > 0 && !seen.has(cursor.pid)) {
    if (cursor.ppid === ancestorPid) return true;
    seen.add(cursor.pid);
    cursor = rows.get(cursor.ppid);
  }
  return false;
}

function runtimeLeaves(rows: ReadonlyMap<number, ProcessRow>, releaseRoot: string): ProcessRow[] {
  const candidates = [...rows.values()].filter((row) => (
    row.pid !== BACKEND_PID
    && row.command.includes(releaseRoot)
    && isDescendant(rows, row.pid, BACKEND_PID)
  ));
  return candidates.filter((candidate) => !candidates.some((other) => (
    other.pid !== candidate.pid && isDescendant(rows, other.pid, candidate.pid)
  )));
}

async function getJson<T>(
  request: APIRequestContext,
  token: string,
  path: string,
): Promise<T> {
  const response = await request.get(`${API_BASE}${path}`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), `${path}: ${await response.text()}`).toBe(200);
  return response.json() as Promise<T>;
}

function assistantText(payload: ThreadMessages): string {
  return payload.messages
    .filter((message) => message.role === 'assistant')
    .flatMap((message) => message.parts)
    .filter((part) => part.type === 'text' && typeof part.text === 'string')
    .map((part) => part.text?.trim() ?? '')
    .filter(Boolean)
    .join('\n');
}

async function waitForIdle(
  page: Page,
  token: string,
  threadId: string,
  minimumTurns: number,
): Promise<ThreadStatus> {
  let settled: ThreadStatus | null = null;
  await expect.poll(async () => {
    settled = await getJson<ThreadStatus>(
      page.request,
      token,
      `/api/claude-agent/threads/${encodeURIComponent(threadId)}/status`,
    );
    return settled.running === false && settled.turn_count >= minimumTurns;
  }, {
    timeout: 120_000,
    intervals: [250, 500, 1_000, 2_000],
  }).toBe(true);
  return settled!;
}

test('one test-owned Runtime crash is visible, safe, and recoverable in the same Thread', async ({
  page,
}) => {
  test.setTimeout(360_000);
  const releaseRoot = requireInputs();
  const before = processSnapshot();
  const backend = before.get(BACKEND_PID);
  expect(backend?.command).toMatch(/(?:^|\s)(?:\.venv\/bin\/python|python\S*)\s+server\.py(?:\s|$)/);
  expect(runtimeLeaves(before, releaseRoot).map((row) => row.pid)).toEqual([]);

  const token = createActorToken(ACTOR_EMAIL);
  await page.addInitScript((value) => {
    localStorage.setItem('auth_token', value);
    localStorage.setItem('migration_completed', 'true');
    localStorage.setItem('ink-language', 'zh');
  }, token);
  await page.goto(`${WEB_BASE}/story-workspace/chat?deck=${encodeURIComponent(CHAT_DECK_ID)}`);
  const newChat = page.getByTitle(/^(New chat|新建对话)$/);
  if (await newChat.isVisible().catch(() => false)) await newChat.click();
  const input = page.getByRole('textbox', { name: /^(Chat input|聊天输入)$/ });
  await expect(input).toBeVisible();
  await input.fill('请写一篇结构完整的长篇运行时恢复测试说明，至少包含三十个编号段落；不要调用工具或访问网络。');

  const createResponsePromise = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && new URL(response.url()).pathname === '/api/claude-agent/threads'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status(), await createResponse.text()).toBe(200);
  const threadId = (await createResponse.json() as { thread_id: string }).thread_id;

  let runtime: ProcessRow | null = null;
  await expect.poll(() => {
    const rows = processSnapshot();
    const leaves = runtimeLeaves(rows, releaseRoot);
    if (leaves.length !== 1) return null;
    runtime = leaves[0];
    return runtime.pid;
  }, {
    message: 'Exactly one new candidate Runtime leaf must belong to this sole active test turn.',
    timeout: 20_000,
    intervals: [50, 100, 250],
  }).not.toBeNull();
  expect(before.has(runtime!.pid)).toBe(false);
  process.kill(runtime!.pid, 'SIGKILL');

  const errorBubble = page.getByText(/^Error:/).last();
  await expect(errorBubble).toBeVisible({ timeout: 60_000 });
  const visibleError = await errorBubble.innerText();
  expect(visibleError).toMatch(/(?:runtime|command failed|exit|signal)/i);
  expect(visibleError).not.toContain(releaseRoot);
  expect(visibleError).not.toMatch(/Authorization|Bearer|CLAUDE_CODE_.*TOKEN|\.credentials\.json/i);
  const failedStatus = await waitForIdle(page, token, threadId, 1);
  expect(failedStatus.lifecycle).toBe('idle');

  await expect(input).toBeEnabled();
  await input.fill('刚才连接中断了。请只回复：Runtime 恢复成功。不要调用工具。');
  const recoveryRequestPromise = page.waitForRequest((request) => (
    request.method() === 'POST'
    && new URL(request.url()).pathname === '/api/claude-agent'
  ));
  await page.getByRole('button', { name: /^(Send message|发送消息)$/ }).click();
  const recoveryRequest = await recoveryRequestPromise;
  expect(recoveryRequest.postDataJSON()).toMatchObject({ id: threadId, resume: true });
  const recoveredStatus = await waitForIdle(page, token, threadId, 2);
  expect(recoveredStatus.lifecycle).toBe('idle');
  const history = await getJson<ThreadMessages>(
    page.request,
    token,
    `/api/claude-agent/threads/${encodeURIComponent(threadId)}/messages`,
  );
  expect(assistantText(history)).toContain('Runtime 恢复成功');
  expect(runtimeLeaves(processSnapshot(), releaseRoot).map((row) => row.pid)).toEqual([]);
});
