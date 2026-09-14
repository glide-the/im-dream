// [Input] Explicit Admin service configuration and canonical v1 browser/principal/profile DTOs.
// [Output] Bounded, no-retry server transport; OAuth credentials never leave this private module.
// [Pos] BFF Admin consumer behind the sole Next App Router, independent of database entities.
// [Sync] 2026-09-14: share public authority parsing for retired endpoints; keep Runtime discovery and private callback credentials.
import { z } from 'zod';
import { BffBoundaryError } from './login-boundary.ts';

const identifier = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/);
const decimalId = z.string().regex(/^[1-9]\d{0,18}$/).refine(value => BigInt(value) <= 9_223_372_036_854_775_807n);
const isoTime = z.iso.datetime({ offset: true });
const handle = z.string().regex(/^dbr_[A-Za-z0-9_-]{43}$/);
export const principalDto = z.strictObject({
  subject: z.string().min(1).max(160), canonical_user_id: decimalId,
  client_id: z.string().min(1).max(160), scopes: z.array(z.string()), status: z.literal('active'),
});
const operationDto = z.strictObject({
  name: z.string().min(1), kind: z.enum(['read', 'write']), user_scope: z.string().nullable(),
  background_scope: z.string().nullable(), input_schema_version: z.literal(1),
  output_schema_version: z.literal(1), contract_sha256: z.string().regex(/^[a-f0-9]{64}$/),
});
const capabilitiesDto = z.strictObject({
  version: z.literal('1'),
  auth: z.strictObject({ issuer: z.string(), jwks_uri: z.string(), algorithm: z.literal('ES256'), resource: z.string(),
    clients: z.strictObject({ browser: z.string().min(1), device: z.string().min(1) }), scopes: z.array(z.string()),
    delegations: z.array(z.strictObject({ name: z.enum(['runtime-delegation.create', 'runtime-delegation.renew', 'runtime-delegation.revoke', 'runtime-delegation.receipt']),
      method: z.enum(['POST', 'GET']), path: z.string(), input_schema_version: z.literal(1), output_schema_version: z.literal(1),
      contract_sha256: z.string().regex(/^[a-f0-9]{64}$/) })) }),
  schema_capabilities: z.array(z.strictObject({ capability: z.string().min(1), version: z.number().int().positive(), contract_sha256: z.string().regex(/^[a-f0-9]{64}$/) })),
  operations: z.array(operationDto),
});
const exchangedDto = z.strictObject({ handle, expires_at: isoTime });
const resolvedDto = z.strictObject({ access_token: z.string().min(1), expires_at: isoTime, principal: principalDto });
const profileDto = z.strictObject({ user: z.strictObject({
  id: decimalId, email: z.email(), display_name: z.string().nullable(), avatar_url: z.string().nullable(),
  role: z.string(), created_at: isoTime.nullable(), updated_at: isoTime.nullable(),
  auth_providers: z.array(z.enum(['google', 'credential'])),
}) });
const profileCapability = {
  name: 'user-profile.current', kind: 'read', user_scope: 'dream:read', background_scope: null,
  input_schema_version: 1, output_schema_version: 1,
  contract_sha256: '01011316efa10475dd1d1aa8856c82cb17ddbeb404125ebcd80af5f250f2a9d0',
} as const;
const errorDto = z.strictObject({ request_id: identifier, error: z.strictObject({ code: identifier, message: z.string() }) });
export type BrowserResolution = z.infer<typeof resolvedDto>;
export type AdminBffConfig = Readonly<{
  origin: string; issuer: string; resource: string; serviceId: string; serviceSecret: string;
  timeoutMilliseconds: number; maxResponseBytes: number;
}>;

function required(environment: Readonly<Record<string, string | undefined>>, key: string): string {
  const value = environment[key]?.trim() ?? '';
  if (!value || /[\u0000-\u001f\u007f]/.test(value)) throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
  return value;
}

export function publicAdminAuthority(environment: Readonly<Record<string, string | undefined>> = process.env): Readonly<{ origin: string; issuer: string; resource: string }> {
  const origin = required(environment, 'INK_ADMIN_DREAM_BASE_URL');
  try {
    const url = new URL(origin);
    if (origin !== url.origin || url.username || url.password
      || (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)))) throw new Error();
  } catch { throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503); }
  const issuer = required(environment, 'INK_ADMIN_AUTH_ISSUER');
  const resource = required(environment, 'INK_DREAM_API_RESOURCE');
  if (issuer !== origin + '/api/auth' || /\s/.test(resource)) throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
  return Object.freeze({ origin, issuer, resource });
}

export function adminBffConfig(environment: Readonly<Record<string, string | undefined>> = process.env): AdminBffConfig {
  const { origin, issuer, resource } = publicAdminAuthority(environment);
  const serviceId = required(environment, 'INK_ADMIN_DREAM_SERVICE_CLIENT_ID');
  const serviceSecret = required(environment, 'INK_ADMIN_DREAM_SERVICE_SECRET');
  const timeoutMilliseconds = Math.ceil(Number(environment.INK_ADMIN_DREAM_TIMEOUT_SECONDS ?? '10') * 1_000);
  const maxResponseBytes = Number(environment.INK_ADMIN_DREAM_MAX_RESPONSE_BYTES ?? '1048576');
  if (issuer !== origin + '/api/auth' || /\s/.test(resource) || /\s/.test(serviceId)
    || Buffer.byteLength(serviceSecret) < 32 || !Number.isSafeInteger(timeoutMilliseconds)
    || timeoutMilliseconds < 1 || timeoutMilliseconds > 2_147_483_647
    || !Number.isSafeInteger(maxResponseBytes) || maxResponseBytes < 1) throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
  return Object.freeze({ origin, issuer, resource, serviceId, serviceSecret, timeoutMilliseconds, maxResponseBytes });
}

export class AdminBffClient {
  readonly origin: string;
  readonly issuer: string;
  readonly resource: string;
  readonly #config: AdminBffConfig;
  readonly #fetch: typeof fetch;
  constructor(config: AdminBffConfig, transport: typeof fetch = fetch) {
    this.#config = config;
    this.origin = config.origin;
    this.issuer = config.issuer;
    this.resource = config.resource;
    this.#fetch = transport;
  }

  async #request<T>(path: string, requestId: string, schema: z.ZodType<T>, body?: unknown, token?: string, signal?: AbortSignal): Promise<T> {
    identifier.parse(requestId);
    if (token !== undefined && (!token || /\s|[\u0000-\u001f\u007f]/.test(token))) throw new BffBoundaryError('BFF_SESSION_INVALID', 401);
    const headers = new Headers({ accept: 'application/json', 'x-request-id': requestId,
      'X-Ink-Dream-Service': this.#config.serviceId, 'X-Ink-Dream-Credential': this.#config.serviceSecret });
    if (body !== undefined) headers.set('content-type', 'application/json');
    if (token !== undefined) headers.set('authorization', 'Bearer ' + token);
    let response: Response;
    let raw: string;
    try {
      const timeout = AbortSignal.timeout(this.#config.timeoutMilliseconds);
      response = await this.#fetch(this.origin + '/api/internal/dream/v1' + path, {
        method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body),
        cache: 'no-store', redirect: 'manual', signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
      });
      const reader = response.body?.getReader();
      const chunks: Uint8Array[] = []; let length = 0;
      if (reader) {
        try {
          for (;;) {
            const chunk = await reader.read(); if (chunk.done) break;
            length += chunk.value.length;
            if (length > this.#config.maxResponseBytes) { await reader.cancel(); throw new BffBoundaryError('BFF_ADMIN_RESPONSE_INVALID', 503); }
            chunks.push(chunk.value);
          }
        } finally { reader.releaseLock(); }
      }
      raw = Buffer.concat(chunks).toString('utf8');
    } catch (error) {
      if (error instanceof BffBoundaryError) throw error;
      throw new BffBoundaryError('BFF_ADMIN_UNAVAILABLE', 503);
    }
    let payload: unknown;
    try { payload = JSON.parse(raw); } catch { throw new BffBoundaryError('BFF_ADMIN_RESPONSE_INVALID', 503); }
    if (!response.ok) {
      const parsed = errorDto.safeParse(payload);
      if (!parsed.success || parsed.data.request_id !== requestId) throw new BffBoundaryError('BFF_ADMIN_RESPONSE_INVALID', 503);
      const status = [400, 401, 403, 404, 409, 422, 429, 503, 504].includes(response.status) ? response.status : 503;
      throw new BffBoundaryError(parsed.data.error.code, status);
    }
    const parsed = z.strictObject({ request_id: identifier, data: schema }).safeParse(payload);
    if (!parsed.success || parsed.data.request_id !== requestId) throw new BffBoundaryError('BFF_ADMIN_RESPONSE_INVALID', 503);
    return parsed.data.data;
  }

  async capabilities(requestId: string, signal?: AbortSignal) {
    const result = await this.#request('/capabilities', requestId, capabilitiesDto, undefined, undefined, signal);
    if (result.auth.issuer !== this.issuer || result.auth.jwks_uri !== this.issuer + '/jwks'
      || result.auth.resource !== this.resource || new Set(result.operations.map(item => item.name)).size !== result.operations.length) {
      throw new BffBoundaryError('BFF_ADMIN_RESPONSE_INVALID', 503);
    }
    return result;
  }

  async exchange(transactionId: string, code: string, codeVerifier: string, redirectUri: string, signal?: AbortSignal) {
    const body = z.strictObject({ request_id: identifier, transaction_id: identifier, code: z.string().min(1).max(2048),
      code_verifier: z.string().regex(/^[A-Za-z0-9._~-]{43,128}$/), redirect_uri: z.string().min(1).max(2048) })
      .parse({ request_id: transactionId, transaction_id: transactionId, code, code_verifier: codeVerifier, redirect_uri: redirectUri });
    return this.#request('/browser-sessions/exchange', transactionId, exchangedDto, body, undefined, signal);
  }

  async resolve(browserHandle: string, requestId: string, signal?: AbortSignal): Promise<BrowserResolution> {
    return this.#request('/browser-sessions/resolve', requestId, resolvedDto, { request_id: identifier.parse(requestId), handle: handle.parse(browserHandle) }, undefined, signal);
  }

  async revoke(browserHandle: string, requestId: string, signal?: AbortSignal) {
    return this.#request('/browser-sessions/revoke', requestId, z.strictObject({ revoked: z.literal(true) }), { request_id: identifier.parse(requestId), handle: handle.parse(browserHandle) }, undefined, signal);
  }

  async currentProfile(resolution: BrowserResolution, requestId: string, signal?: AbortSignal) {
    const caps = await this.capabilities(requestId, signal);
    const operation = caps.operations.find(item => item.name === profileCapability.name);
    if (!operation || Object.entries(profileCapability).some(([key, value]) => operation[key as keyof typeof operation] !== value)) throw new BffBoundaryError('BFF_ADMIN_CAPABILITY_UNAVAILABLE', 503);
    if (!resolution.principal.scopes.includes('dream:read')) throw new BffBoundaryError('INSUFFICIENT_SCOPE', 403);
    const result = await this.#request('/operations/user-profile.current', requestId, profileDto, { request_id: requestId, input: {} }, resolution.access_token, signal);
    if (result.user.id !== resolution.principal.canonical_user_id) throw new BffBoundaryError('BFF_ADMIN_RESPONSE_INVALID', 503);
    return result.user;
  }
}
