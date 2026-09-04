// [Input] Authenticated Claude Agent common Skill command catalog endpoint.
// [Output] Typed backend-owned common Skill commands for Chat slash discovery.
// [Pos] Common Skill catalog transport in frontend/src/api; it does not execute Skills.
// [Sync] 2026-09-04: added the authenticated common Skill command catalog client.

import { getAuthToken } from '../contexts/AuthContext';
import { apiUrl } from '../lib/apiBase';

export interface CommonSkillCommandDto {
  readonly command: string;
  readonly name: string;
}

export async function listCommonSkillCommands(): Promise<readonly CommonSkillCommandDto[]> {
  const headers = new Headers({ Accept: 'application/json' });
  const token = getAuthToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(apiUrl('/api/claude-agent/skill-commands'), {
    credentials: 'include',
    headers,
  });
  if (!response.ok) {
    throw new Error(`Common Skill catalog request failed with status ${response.status}`);
  }
  const payload = await response.json() as { readonly commands?: unknown };
  return Array.isArray(payload.commands)
    ? payload.commands as readonly CommonSkillCommandDto[]
    : [];
}
