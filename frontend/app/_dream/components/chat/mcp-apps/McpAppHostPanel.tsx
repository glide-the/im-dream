'use client';

// [Input] Trusted saved MCP Apps call, current Thread identity, optional existing Chat ingress, and Host status.
// [Output] Lifecycle-controlled same-origin Browser MCP Client plus Host adapter, or silent ordinary fallback.
// [Pos] ToolMessagePart child; never replays the originating tools/call and never owns upstream authority.
// [Sync] 2026-09-06: terminate each stateful session after any in-flight connect and keep identical policy polls stable.
// [Sync] 2026-09-06: load only the current connection-scoped App policy and user interaction choices.
// [Sync] 2026-09-06: retain a semantically unchanged saved call across history-poll object replacement so the App iframe and form state stay mounted.

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import {
  UI_EXTENSION_CAPABILITIES,
} from '@mcp-ui/client';

import { getAuthToken } from '../../../contexts/AuthContext';
import ImMcpAppHostAdapter, {
  McpAppBrowserError,
  type SendMcpAppUserMessage,
} from './ImMcpAppHostAdapter';
import {
  MCP_APPS_HOST_MANIFEST,
  mcpAppsPolicyIdentity,
  parseMcpAppsHostPolicy,
  type McpAppsHostPolicy,
} from './host-policy';
import { sameSavedMcpAppToolCall, type SavedMcpAppToolCall } from './result';
import {
  cleanupFailedMcpAppsConnection,
  closeMcpAppsClientSession,
} from './session-cleanup';

type PanelState =
  | { readonly status: 'checking' }
  | { readonly status: 'ready'; readonly policy: McpAppsHostPolicy }
  | { readonly status: 'unavailable' };

type ConnectedClient = Readonly<{
  client: Client;
  transport: StreamableHTTPClientTransport;
  close: () => Promise<void>;
  policyIdentity: string;
}>;

type ClientTransport = Pick<ConnectedClient, 'client' | 'transport' | 'close'>;

const PANEL_STYLE = Object.freeze({
  marginTop: '0.75rem',
  overflow: 'hidden',
  border: '1px solid var(--color-border-neutral)',
  borderRadius: '12px',
  background: 'var(--color-bg-surface-solid)',
  boxShadow: '0 8px 24px rgba(63, 52, 41, 0.06)',
} as const);

const PANEL_ACTION_STYLE = Object.freeze({
  border: '1px solid var(--color-border-paper)',
  borderRadius: '999px',
  background: 'var(--color-bg-paper)',
  color: 'var(--color-text-secondary)',
  cursor: 'pointer',
  font: 'inherit',
  fontSize: '0.75rem',
  lineHeight: 1.2,
  padding: '0.35rem 0.7rem',
} as const);

async function loadPolicy(
  signal: AbortSignal,
  serverRef: string,
  workspaceScope: string | null,
): Promise<McpAppsHostPolicy | null> {
  const token = getAuthToken();
  if (!token) return null;
  const query = new URLSearchParams({ serverRef });
  if (workspaceScope) query.set('workspaceScope', workspaceScope);
  const response = await fetch(`/api/mcp-apps/phase1-status?${query.toString()}`, {
    cache: 'no-store',
    headers: { authorization: `Bearer ${token}` },
    signal,
  });
  if (!response.ok) return null;
  return parseMcpAppsHostPolicy(await response.json(), window.location.origin);
}

export default function McpAppHostPanel({
  call,
  threadId,
  onSendMessage,
}: Readonly<{
  call: SavedMcpAppToolCall;
  threadId: string;
  onSendMessage?: SendMcpAppUserMessage;
}>) {
  const { t } = useTranslation();
  const [panel, setPanel] = useState<PanelState>({ status: 'checking' });
  const [connection, setConnection] = useState<ConnectedClient | null>(null);
  const [closed, setClosed] = useState(false);
  const [browserError, setBrowserError] = useState<McpAppBrowserError | null>(null);
  const [retryRevision, setRetryRevision] = useState(0);
  const [policyPollMs, setPolicyPollMs] = useState<number>(
    MCP_APPS_HOST_MANIFEST.defaults.policyPollMs,
  );
  const [browserSession] = useState(() => globalThis.crypto.randomUUID());
  const stableCallRef = useRef(call);
  if (!sameSavedMcpAppToolCall(stableCallRef.current, call)) {
    stableCallRef.current = call;
  }
  const stableCall = stableCallRef.current;
  const policy = panel.status === 'ready' ? panel.policy : null;
  const policyIdentity = useMemo(
    () => policy ? mcpAppsPolicyIdentity(policy) : null,
    [policy],
  );
  const client = connection?.policyIdentity === policyIdentity
    ? connection.client
    : null;
  const onError = useCallback((error: McpAppBrowserError) => setBrowserError(error), []);

  useEffect(() => {
    setClosed(false);
    setBrowserError(null);
  }, [stableCall.serverRef, stableCall.toolCallId, threadId]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let inspecting = false;
    let previousIdentity = policyIdentity;
    const inspect = async () => {
      if (inspecting) return;
      inspecting = true;
      try {
        const next = await loadPolicy(
          controller.signal,
          stableCall.serverRef,
          stableCall.workspaceScope,
        );
        if (!active) return;
        if (!next) {
          previousIdentity = null;
          setPanel((current) => current.status === 'unavailable'
            ? current
            : { status: 'unavailable' });
          return;
        }
        if (next.policyPollMs !== policyPollMs) setPolicyPollMs(next.policyPollMs);
        const nextIdentity = mcpAppsPolicyIdentity(next);
        if (previousIdentity !== nextIdentity) {
          previousIdentity = nextIdentity;
          setBrowserError(null);
          setPanel({ status: 'ready', policy: next });
        }
        setBrowserError((current) => current?.stage === 'transport' ? null : current);
      } catch {
        if (active && !controller.signal.aborted) {
          previousIdentity = null;
          setPanel((current) => current.status === 'unavailable'
            ? current
            : { status: 'unavailable' });
        }
      } finally {
        inspecting = false;
      }
    };
    void inspect();
    const timer = window.setInterval(() => void inspect(), policyPollMs);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
    };
  }, [policyIdentity, policyPollMs, retryRevision, stableCall.serverRef, stableCall.workspaceScope, threadId]);

  useEffect(() => {
    if (!policy || !policyIdentity || closed || browserError) {
      setConnection(null);
      return;
    }
    let active = true;
    let currentConnection: ClientTransport | null = null;
    let connectionReady: Promise<void> | null = null;
    let teardown: Promise<void> | null = null;
    const teardownCurrentConnection = (): Promise<void> => {
      if (teardown) return teardown;
      teardown = (async () => {
        await connectionReady?.catch(() => undefined);
        const closing = currentConnection;
        currentConnection = null;
        if (closing) await closing.close();
      })();
      return teardown;
    };
    const connect = async () => {
      try {
        const token = getAuthToken();
        if (!token) return;
        const endpoint = new URL(
          `/api/mcp-apps/${encodeURIComponent(stableCall.serverRef)}`,
          window.location.origin,
        );
        const requestHeaders = {
          authorization: `Bearer ${token}`,
          'x-ink-mcp-apps-browser-session': browserSession,
          ...(stableCall.workspaceScope
            ? { 'x-ink-workspace-scope': stableCall.workspaceScope }
            : {}),
        };
        const transport = new StreamableHTTPClientTransport(
          endpoint,
          {
            requestInit: {
              headers: requestHeaders,
            },
          },
        );
        const capabilities = {
          extensions: UI_EXTENSION_CAPABILITIES,
        };
        const connectedClient = new Client(
          { name: 'ink-memory-browser-host', version: policy.manifestVersion },
          { capabilities },
        );
        const createdConnection = {
          client: connectedClient,
          transport,
          close: () => closeMcpAppsClientSession({
            client: connectedClient,
            transport,
            endpoint,
            headers: requestHeaders,
            timeoutMs: policy.readyTimeoutMs,
          }),
        };
        currentConnection = createdConnection;
        connectionReady = connectedClient.connect(transport);
        await connectionReady;
        if (!active) {
          await teardownCurrentConnection();
          return;
        }
        setConnection({ ...createdConnection, policyIdentity });
      } catch (error) {
        await cleanupFailedMcpAppsConnection({
          cleanup: teardownCurrentConnection,
          isActive: () => active,
          report: () => setBrowserError(
            new McpAppBrowserError('transport', 'transport_failed', error),
          ),
        });
      }
    };
    void connect();
    return () => {
      active = false;
      const closing = currentConnection;
      setConnection((current) => current?.client === closing?.client ? null : current);
      void teardownCurrentConnection();
    };
  }, [browserError, browserSession, closed, policy, policyIdentity, stableCall.serverRef, stableCall.workspaceScope, threadId]);

  useEffect(() => {
    if (!client || !policy || closed || browserError) return undefined;
    let active = true;
    let running = false;
    const revalidate = async () => {
      if (running) return;
      running = true;
      try {
        await client.ping({ timeout: policy.readyTimeoutMs });
      } catch (error) {
        if (active) {
          setBrowserError(new McpAppBrowserError(
            'transport',
            'session_revalidation_failed',
            error,
          ));
        }
      } finally {
        running = false;
      }
    };
    const timer = window.setInterval(() => void revalidate(), policy.policyPollMs);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [browserError, client, closed, policy]);

  if (panel.status === 'checking') return null;
  if (panel.status === 'unavailable' || browserError) {
    return (
      <div
        data-testid="mcp-app-fallback"
        data-diagnostic-stage={browserError?.stage ?? 'policy'}
        data-diagnostic-code={browserError?.code ?? 'policy_unavailable'}
        role="status"
        style={{
          ...PANEL_STYLE,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
          padding: '0.7rem 0.8rem',
          color: 'var(--color-text-secondary)',
          fontSize: '0.8rem',
        }}
      >
        <span>{t('chat.mcpApps.unavailable')}</span>
        <button
          type="button"
          data-testid="mcp-app-retry"
          style={PANEL_ACTION_STYLE}
          onClick={() => {
            setBrowserError(null);
            setRetryRevision((value) => value + 1);
          }}
        >
          {t('chat.mcpApps.retry')}
        </button>
      </div>
    );
  }
  if (closed) {
    return (
      <button
        type="button"
        data-testid="mcp-app-reopen"
        style={{ ...PANEL_ACTION_STYLE, marginTop: '0.75rem' }}
        onClick={() => setClosed(false)}
      >
        {t('chat.mcpApps.open')}
      </button>
    );
  }
  if (!client || !policy) return null;
  return (
    <section
      data-testid="mcp-app-panel"
      data-policy-revision={policy.revision}
      aria-label={t('chat.mcpApps.regionLabel')}
      style={PANEL_STYLE}
    >
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '0.75rem',
        minHeight: '2.75rem',
        padding: '0.45rem 0.65rem 0.45rem 0.8rem',
        borderBottom: '1px solid var(--color-border-neutral)',
        color: 'var(--color-text-secondary)',
        fontSize: '0.78rem',
      }}>
        <span>{t('chat.mcpApps.regionLabel')}</span>
        <button
          type="button"
          data-testid="mcp-app-close"
          style={PANEL_ACTION_STYLE}
          onClick={() => setClosed(true)}
        >
          {t('chat.mcpApps.close')}
        </button>
      </header>
      <ImMcpAppHostAdapter
        client={client}
        toolName={stableCall.toolName}
        toolInput={stableCall.input}
        toolResult={stableCall.result}
        expectedResourceUri={stableCall.resourceUri}
        policy={policy}
        onSendMessage={onSendMessage}
        onError={onError}
      />
    </section>
  );
}
