// [Input] Root App Router requests delegated through the package public entry.
// [Output] Server-only request handlers, safe current plugin manifest, and process teardown.
// [Pos] Sole public Runtime entry; Browser/RSC/root-Web reverse imports are forbidden.
// [Sync] 2026-09-06: export the same safe Node plugin manifest for Next policy routes.

import 'server-only';

import { handleMcpAppsRequest } from './runtime.ts';
import { EnvironmentPluginManifestProvider } from './plugin-manifest.ts';

export type { McpAppsPluginManifest } from './plugin-manifest.ts';
export type { McpAppsStaticView } from './contracts.ts';

export { closeMcpAppsRuntime, readCurrentMcpAppsStaticView } from './runtime.ts';

export function readMcpAppsPluginManifest() {
  return new EnvironmentPluginManifestProvider().current();
}

export function handleMcpAppsGet(request: Request, serverRef: string): Promise<Response> {
  return handleMcpAppsRequest(request, serverRef);
}

export function handleMcpAppsPost(request: Request, serverRef: string): Promise<Response> {
  return handleMcpAppsRequest(request, serverRef);
}

export function handleMcpAppsDelete(request: Request, serverRef: string): Promise<Response> {
  return handleMcpAppsRequest(request, serverRef);
}
