// [Input] Authoritative managed MCP server configuration and the desired enabled value.
// [Output] Complete original PATCH changes when all required configuration is available.
// [Pos] Shared resource-card and Chat-tool eligibility; no guessed configuration or permission policy.
// [Sync] 2026-11-13: reuse the original revision-aware API for service enable/disable.
import type {ClaudeMcpServer} from '../../api/claudeMcpApi';

export function mcpServerToggleChanges(server:ClaudeMcpServer,enabled:boolean) {
  if (!server.id || !server.revision || !['user','workspace'].includes(server.config_scope)) return null;
  if (server.transport === 'stdio') {
    if (!server.stdio_profile_key) return null;
  } else if (server.transport !== 'streamable_http' && server.transport !== 'sse') return null;
  else if (!server.url) return null;
  return {displayName:server.display_name,transport:server.transport as 'streamable_http'|'sse'|'stdio',url:server.url,stdioProfileKey:server.stdio_profile_key,enabled};
}
