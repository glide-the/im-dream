// [Input] Runtime lifecycle outcomes plus already-validated opaque scope identifiers.
// [Output] Bounded structured diagnostics containing hashes/codes only, never payload material.
// [Pos] Phase 3 observability boundary shared by manager and HTTP adapter.
// [Sync] 2026-09-06: add closed-schema, URL/header/body/HTML-free diagnostic events.

import { createHash } from 'node:crypto';

import type { McpAppsConnectionView } from './contracts.ts';

export type McpAppsDiagnosticStage =
  | 'browser_transport'
  | 'connection_view'
  | 'authorization'
  | 'resource'
  | 'upstream'
  | 'plugin_lifecycle';

export type McpAppsDiagnosticEvent = Readonly<{
  stage: McpAppsDiagnosticStage;
  actorScopeHash: string | null;
  workspaceScopeHash: string | null;
  serverRef: string;
  sessionRef: string | null;
  outcome: 'allowed' | 'denied' | 'failed' | 'closed';
  errorCode: string | null;
  manifestRevision: number | null;
}>;

function scopeHash(value: string | null): string | null {
  return value === null ? null : createHash('sha256').update(value).digest('hex');
}

export class McpAppsDiagnosticRecorder {
  readonly #events: McpAppsDiagnosticEvent[] = [];

  constructor(readonly maximumEvents = 128) {
    if (!Number.isSafeInteger(maximumEvents) || maximumEvents < 1) {
      throw new TypeError('maximumEvents must be a positive safe integer');
    }
  }

  record(input: Readonly<{
    stage: McpAppsDiagnosticStage;
    view?: McpAppsConnectionView;
    serverRef: string;
    sessionId?: string | null;
    outcome: McpAppsDiagnosticEvent['outcome'];
    errorCode?: string | null;
    manifestRevision: number | null;
  }>): void {
    const event = Object.freeze({
      stage: input.stage,
      actorScopeHash: scopeHash(input.view?.actorScope ?? null),
      workspaceScopeHash: scopeHash(input.view?.workspaceScope ?? null),
      serverRef: input.serverRef,
      sessionRef: scopeHash(input.sessionId ?? null),
      outcome: input.outcome,
      errorCode: input.errorCode ?? null,
      manifestRevision: input.manifestRevision,
    });
    this.#events.push(event);
    if (this.#events.length > this.maximumEvents) this.#events.shift();
  }

  snapshot(): readonly McpAppsDiagnosticEvent[] {
    return Object.freeze([...this.#events]);
  }
}
