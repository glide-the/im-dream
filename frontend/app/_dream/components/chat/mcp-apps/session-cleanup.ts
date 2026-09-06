// [Input] One Browser MCP Client, its stateful Streamable HTTP transport, endpoint, scoped headers, and server timeout.
// [Output] Bounded fresh-signal DELETE, unconditional local close, and stale-lifecycle error suppression.
// [Pos] Browser session cleanup primitive; it never creates authority or logs endpoint/header/session material.
// [Sync] 2026-09-06: recover server sessions even when Client.connect already aborted the SDK transport signal.

type ClosableClient = Readonly<{
  close(): Promise<void>;
}>;

type StatefulHttpTransport = Readonly<{
  sessionId?: string;
  protocolVersion?: string;
  terminateSession(): Promise<void>;
}>;

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

async function bounded(operation: Promise<void>, timeoutMs: number): Promise<void> {
  let timer: ReturnType<typeof setTimeout> | null = null;
  try {
    await Promise.race([
      operation,
      new Promise<void>((_resolve, reject) => {
        timer = setTimeout(() => reject(new Error('MCP session cleanup timed out.')), timeoutMs);
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

async function terminateWithFreshSignal(input: Readonly<{
  endpoint: URL;
  headers: Readonly<Record<string, string>>;
  sessionId: string;
  protocolVersion?: string;
  timeoutMs: number;
  fetcher: Fetcher;
}>): Promise<void> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), input.timeoutMs);
  const headers = new Headers(input.headers);
  headers.set('mcp-session-id', input.sessionId);
  if (input.protocolVersion) headers.set('mcp-protocol-version', input.protocolVersion);
  try {
    const response = await input.fetcher(input.endpoint, {
      method: 'DELETE',
      headers,
      cache: 'no-store',
      signal: controller.signal,
    });
    await response.body?.cancel();
  } finally {
    clearTimeout(timer);
  }
}

export async function closeMcpAppsClientSession(input: Readonly<{
  client: ClosableClient;
  transport: StatefulHttpTransport;
  endpoint: URL;
  headers: Readonly<Record<string, string>>;
  timeoutMs: number;
  fetcher?: Fetcher;
}>): Promise<void> {
  const sessionId = input.transport.sessionId;
  try {
    if (!sessionId) return;
    try {
      await bounded(input.transport.terminateSession(), input.timeoutMs);
      return;
    } catch {
      await terminateWithFreshSignal({
        endpoint: input.endpoint,
        headers: input.headers,
        sessionId,
        protocolVersion: input.transport.protocolVersion,
        timeoutMs: input.timeoutMs,
        fetcher: input.fetcher ?? globalThis.fetch,
      }).catch(() => undefined);
    }
  } finally {
    await input.client.close().catch(() => undefined);
  }
}

export async function cleanupFailedMcpAppsConnection(input: Readonly<{
  cleanup: () => Promise<void>;
  isActive: () => boolean;
  report: () => void;
}>): Promise<void> {
  if (!input.isActive()) return;
  await input.cleanup();
  if (input.isActive()) input.report();
}
