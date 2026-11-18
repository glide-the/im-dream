// [Input] Browser session and existing system configuration GET.
// [Output] HTTP status and decoded configuration for the current browser session.
// [Pos] Shares concurrent Web reads across Chat and its composer.
import { API_BASE } from '../lib/apiBase';
import { browserRequestHeaders } from '../lib/browserSession';
import { createSessionRequestShare } from '../lib/shareSessionRequest';

const shareConfigRead = createSessionRequestShare<{ status: number; payload: unknown }>();

async function fetchWebSystemConfig() {
  const response = await fetch(`${API_BASE}/api/system-config`, { headers: browserRequestHeaders() });
  const payload: unknown = response.ok ? await response.json() : null;
  return { status: response.status, payload };
}

export function readWebSystemConfig({ fresh = false } = {}) {
  return fresh ? fetchWebSystemConfig() : shareConfigRead(fetch, 'system-config', fetchWebSystemConfig);
}
