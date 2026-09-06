// [Input] A test-owned Browser MCP endpoint, completed CallToolResult, and immutable policy/sandbox snapshot.
// [Output] Mount ImMcpAppHostAdapter without replaying the original tool and expose redacted diagnostics.
// [Pos] phase0-app-renderer-harness browser module; excluded from production entrypoints.
// [Sync] 2026-09-04: switch the bounded P0-04 lane to the DEC-002 Host adapter.
// [Sync] 2026-09-06: mark the intentional module-load browser entry for the lint gate.

/* eslint-disable react-refresh/only-export-components -- provider-free browser entry renders at module load */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import {
  ImMcpAppHostAdapter,
  type Phase0PermissionPolicy,
  type Phase0PolicyEvidence,
} from './ImMcpAppHostAdapter';


const UI_EXTENSION_CAPABILITIES = {
  'io.modelcontextprotocol/ui': { mimeTypes: ['text/html;profile=mcp-app'] },
};


type Phase0Config = {
  endpointUrl: string;
  sandboxUrl: string;
  sandboxTokens: string;
  permissionPolicy?: Phase0PermissionPolicy;
  toolName: string;
  toolInput: Record<string, unknown>;
  toolResult: CallToolResult;
};

type Phase0HarnessState = {
  connected: boolean;
  closed: boolean;
  errors: string[];
  logs: string[];
  policyEvidence: Phase0PolicyEvidence | null;
};

declare global {
  interface Window {
    __PHASE0_CONFIG__: Phase0Config;
    phase0Harness: Phase0HarnessState;
  }
}


const harnessState: Phase0HarnessState = {
  connected: false,
  closed: false,
  errors: [],
  logs: [],
  policyEvidence: null,
};
window.phase0Harness = harnessState;


function Phase0AppRendererHarness() {
  const config = window.__PHASE0_CONFIG__;
  const clientRef = useRef<Client | null>(null);
  const [client, setClient] = useState<Client | null>(null);
  const [mounted, setMounted] = useState(true);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    let active = true;
    const nextClient = new Client(
      { name: 'phase0-browser-client', version: '1.0.0' },
      { capabilities: { extensions: UI_EXTENSION_CAPABILITIES } },
    );
    clientRef.current = nextClient;
    nextClient.connect(new StreamableHTTPClientTransport(new URL(config.endpointUrl)))
      .then(() => {
        if (!active) return;
        harnessState.connected = true;
        setClient(nextClient);
      })
      .catch((error: unknown) => {
        harnessState.errors.push(error instanceof Error ? error.message : String(error));
      });
    return () => {
      active = false;
      void nextClient.close();
    };
  }, [config.endpointUrl]);

  const recordLog = useCallback((data: unknown) => {
    harnessState.logs.push(String(data));
  }, []);
  const recordPolicyEvidence = useCallback((evidence: Phase0PolicyEvidence) => {
    harnessState.policyEvidence = evidence;
  }, []);
  const recordError = useCallback((error: Error) => {
    harnessState.errors.push(error.message);
  }, []);
  const completeClose = useCallback(() => {
    setMounted(false);
    harnessState.closed = true;
    void clientRef.current?.close();
  }, []);

  const closeApp = () => {
    setClosing(true);
  };

  return (
    <main style={{ maxWidth: 760, margin: '40px auto', fontFamily: 'system-ui' }}>
      <h1>Phase 0 MCP Apps isolated harness</h1>
      <p data-testid="connection-state">{client ? 'connected' : 'connecting'}</p>
      <section data-testid="fallback-result">
        {config.toolResult.content?.[0]?.type === 'text'
          ? config.toolResult.content[0].text
          : 'Fallback result available'}
      </section>
      {mounted && client ? (
        <ImMcpAppHostAdapter
          client={client}
          toolName={config.toolName}
          toolInput={config.toolInput}
          toolResult={config.toolResult}
          sandboxUrl={config.sandboxUrl}
          sandboxTokens={config.sandboxTokens}
          permissionPolicy={config.permissionPolicy}
          closeRequested={closing}
          onClosed={completeClose}
          onLoggingMessage={recordLog}
          onPolicyEvidence={recordPolicyEvidence}
          onError={recordError}
        />
      ) : null}
      <button type="button" onClick={closeApp} disabled={!mounted || !client || closing}>
        Close isolated app
      </button>
      <output data-testid="harness-logs">{harnessState.logs.join('|')}</output>
    </main>
  );
}


createRoot(document.getElementById('root')!).render(<Phase0AppRendererHarness />);
