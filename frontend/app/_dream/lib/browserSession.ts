// [Input] Same-origin BFF public session DTO and Browser request header requirements.
// [Output] Immutable public user/session state, in-memory CSRF and Cookie-based request headers.
// [Pos] Sole Browser session/header owner; OAuth tokens remain on Admin/Dream servers.
// [Sync] 2026-09-14: replace OAuth storage and Bearer injection with validated session/CSRF.
import { z } from 'zod';

const decimalId = z.string().regex(/^[1-9]\d{0,18}$/).refine(value => BigInt(value) <= 9_223_372_036_854_775_807n);
const sessionDto = z.strictObject({
  user: z.strictObject({ id: decimalId, email: z.email(), display_name: z.string().nullable(),
    avatar_url: z.string().nullable(), role: z.string(), created_at: z.iso.datetime({ offset: true }).nullable() }),
  csrf_token: z.string().regex(/^[A-Za-z0-9_-]{43}$/),
});
export type BrowserUser = Readonly<z.infer<typeof sessionDto>['user']>;
export type BrowserSession = Readonly<z.infer<typeof sessionDto>>;
let csrfToken: string | null = null;

export class BrowserSessionError extends Error {
  readonly status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

export function getBrowserCsrfToken(): string | null { return csrfToken; }

export function browserRequestHeaders(extra: Record<string, string> = {}, override: string | null | undefined = undefined): Record<string, string> {
  const value = override === undefined ? csrfToken : override;
  if (value !== null && !/^[A-Za-z0-9_-]{43}$/.test(value)) throw new BrowserSessionError(401, 'Please log in again.');
  const headers = { ...extra };
  for (const key of Object.keys(headers)) if (/^(?:authorization|cookie|x-ink-csrf)$/i.test(key)) delete headers[key];
  if (value !== null) headers['x-ink-csrf'] = value;
  return headers;
}

export function clearBrowserSession(): void { csrfToken = null; }

export async function loadBrowserSession(transport: typeof fetch = fetch, signal?: AbortSignal): Promise<BrowserSession | null> {
  let response: Response;
  try { response = await transport('/auth/session', { credentials: 'include', cache: 'no-store', signal }); }
  catch { throw new BrowserSessionError(503, 'Unable to check your session. Please try again.'); }
  if (response.status === 401) { clearBrowserSession(); return null; }
  if (!response.ok) throw new BrowserSessionError(response.status, 'Unable to check your session. Please try again.');
  let payload: unknown;
  try { payload = await response.json(); } catch { throw new BrowserSessionError(503, 'Unable to check your session. Please try again.'); }
  const parsed = sessionDto.safeParse(payload);
  if (!parsed.success) throw new BrowserSessionError(503, 'Unable to check your session. Please try again.');
  csrfToken = parsed.data.csrf_token;
  return Object.freeze({ user: Object.freeze(parsed.data.user), csrf_token: parsed.data.csrf_token });
}

export async function revokeBrowserSession(transport: typeof fetch = fetch): Promise<void> {
  let response: Response;
  try { response = await transport('/auth/logout', { method: 'POST', credentials: 'include', cache: 'no-store', headers: browserRequestHeaders() }); }
  catch { throw new BrowserSessionError(503, 'Unable to log out. Please try again.'); }
  if (!response.ok) throw new BrowserSessionError(response.status, 'Unable to log out. Please try again.');
  let result: unknown;
  try { result = await response.json(); } catch { throw new BrowserSessionError(503, 'Unable to log out. Please try again.'); }
  if (!z.strictObject({ success: z.literal(true) }).safeParse(result).success) throw new BrowserSessionError(503, 'Unable to log out. Please try again.');
  clearBrowserSession();
}
