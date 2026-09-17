// [Input] Explicit Dream public/internal origins, cookie secret and browser login/callback inputs.
// [Output] Encrypted PKCE transaction cookies, restricted return locations and handle-bound CSRF.
// [Pos] Server-only BFF boundary beneath the sole Next App Router; no OAuth token authority.
// [Sync] 2026-09-17: accept only the configured loopback proxy origin when AutoDL rewrites URL and Host.
// [Sync] 2026-09-16: accept an exact configured Host when Next normalizes the server-internal request URL.
// [Sync] 2026-09-14: enforce actual login/API session security and forbid invalid-cookie Bearer fallback.
// [Sync] 2026-09-16: centralize control-character rejection without regex literals.

import {
  createCipheriv, createDecipheriv, createHash, createHmac,
  randomBytes, randomUUID, timingSafeEqual,
} from 'node:crypto';

export class BffBoundaryError extends Error {
  readonly code: string;
  readonly status: number;
  constructor(code: string, status: number) {
    super(code);
    this.code = code;
    this.status = status;
  }
}

export type LoginTransaction = Readonly<{
  transaction_id: string;
  state: string;
  nonce: string;
  code_verifier: string;
  return_to: string;
  expires_at: number;
}>;

function hasControlCharacter(value: string): boolean {
  for (const character of value) {
    const code = character.charCodeAt(0);
    if (code <= 31 || code === 127) return true;
  }
  return false;
}

function exactOrigin(value: string): string {
  try {
    const url = new URL(value);
    const loopback = url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
    if ((url.protocol !== 'https:' && !loopback) || url.username || url.password
      || url.pathname !== '/' || url.search || url.hash || value !== url.origin) {
      throw new Error();
    }
    return url.origin;
  } catch {
    throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
  }
}

export function relativeReturnLocation(raw: string): string {
  let decoded = raw;
  // Decoding strictly reduces the number of escaped bytes; this finite loop
  // also rejects nested encodings instead of guessing an arbitrary depth.
  for (;;) {
    if (!decoded.startsWith('/') || decoded.startsWith('//') || decoded.includes('\\') || hasControlCharacter(decoded)) {
      throw new BffBoundaryError('BFF_RETURN_LOCATION_INVALID', 400);
    }
    let next: string;
    try { next = decodeURIComponent(decoded); }
    catch { throw new BffBoundaryError('BFF_RETURN_LOCATION_INVALID', 400); }
    if (next === decoded) return raw;
    decoded = next;
  }
}

function constantEqual(left: string, right: string): boolean {
  const a = Buffer.from(left); const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

function readCookie(request: Request, name: string): string | null {
  const matches = (request.headers.get('cookie') ?? '').split(';').map(part => part.trim())
    .filter(part => part.startsWith(name + '='));
  if (matches.length !== 1) return null;
  return matches[0].slice(name.length + 1);
}

export class BffLoginBoundary {
  readonly publicOrigin: string;
  readonly internalOrigin: string | null;
  readonly callbackUri: string;
  readonly transactionCookieName: string;
  readonly handleCookieName: string;
  readonly #key: Buffer;
  readonly #csrfKey: Buffer;
  readonly #clock: () => number;
  readonly #transactionLifetime: number;
  readonly #secure: boolean;

  constructor(config: { publicOrigin: string; internalOrigin?: string; callbackUri: string; cookieSecret: string; transactionLifetimeSeconds?: number }, clock: () => number = () => Date.now() / 1_000) {
    this.publicOrigin = exactOrigin(config.publicOrigin);
    this.internalOrigin = config.internalOrigin ? exactOrigin(config.internalOrigin) : null;
    if (this.internalOrigin && !['localhost', '127.0.0.1', '[::1]'].includes(new URL(this.internalOrigin).hostname)) {
      throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
    }
    try {
      const callback = new URL(config.callbackUri);
      if (callback.origin !== this.publicOrigin || callback.username || callback.password || callback.search || callback.hash || callback.href !== config.callbackUri) throw new Error();
      this.callbackUri = config.callbackUri;
    } catch { throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503); }
    if (Buffer.byteLength(config.cookieSecret) < 32 || hasControlCharacter(config.cookieSecret)) {
      throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
    }
    this.#transactionLifetime = config.transactionLifetimeSeconds ?? 600;
    if (!Number.isSafeInteger(this.#transactionLifetime) || this.#transactionLifetime < 1) {
      throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
    }
    this.#clock = clock;
    this.#secure = this.publicOrigin.startsWith('https:');
    this.transactionCookieName = this.#secure ? '__Host-ink-dream-login' : 'ink-dream-login';
    this.handleCookieName = this.#secure ? '__Host-ink-dream-browser' : 'ink-dream-browser';
    this.#key = createHash('sha256').update('dream-login-cookie\0').update(config.cookieSecret).digest();
    this.#csrfKey = createHash('sha256').update('dream-bff-csrf\0').update(config.cookieSecret).digest();
  }

  static fromEnvironment(environment: Readonly<Record<string, string | undefined>> = process.env): BffLoginBoundary {
    const rawTTL = environment.INK_DREAM_BFF_LOGIN_TTL_SECONDS ?? '600';
    if (!/^[1-9][0-9]*$/.test(rawTTL)) throw new BffBoundaryError('BFF_CONFIGURATION_INVALID', 503);
    return new BffLoginBoundary({
      publicOrigin: environment.INK_DREAM_PUBLIC_ORIGIN ?? '',
      internalOrigin: environment.INK_DREAM_BFF_INTERNAL_ORIGIN,
      callbackUri: environment.INK_DREAM_BFF_REDIRECT_URI ?? '',
      cookieSecret: environment.INK_DREAM_BFF_COOKIE_SECRET ?? '',
      transactionLifetimeSeconds: Number(rawTTL),
    });
  }

  createTransaction(returnTo: string): LoginTransaction {
    return Object.freeze({
      transaction_id: randomUUID(), state: randomBytes(32).toString('base64url'),
      nonce: randomBytes(32).toString('base64url'), code_verifier: randomBytes(32).toString('base64url'),
      return_to: relativeReturnLocation(returnTo), expires_at: Math.floor(this.#clock()) + this.#transactionLifetime,
    });
  }

  codeChallenge(transaction: LoginTransaction): string {
    return createHash('sha256').update(transaction.code_verifier).digest('base64url');
  }

  transactionCookie(transaction: LoginTransaction): string {
    const iv = randomBytes(12);
    const cipher = createCipheriv('aes-256-gcm', this.#key, iv);
    cipher.setAAD(Buffer.from(this.publicOrigin));
    const data = Buffer.concat([cipher.update(JSON.stringify(transaction), 'utf8'), cipher.final()]);
    const encoded = Buffer.concat([iv, cipher.getAuthTag(), data]).toString('base64url');
    return this.#cookie(this.transactionCookieName, encoded, Math.max(0, transaction.expires_at - Math.floor(this.#clock())));
  }

  readTransaction(request: Request): LoginTransaction {
    this.requireRequestOrigin(request);
    try {
      const raw = readCookie(request, this.transactionCookieName);
      if (!raw || !/^[A-Za-z0-9_-]+$/.test(raw)) throw new Error();
      const bytes = Buffer.from(raw, 'base64url');
      const cipher = createDecipheriv('aes-256-gcm', this.#key, bytes.subarray(0, 12));
      cipher.setAAD(Buffer.from(this.publicOrigin)); cipher.setAuthTag(bytes.subarray(12, 28));
      const transaction = JSON.parse(Buffer.concat([cipher.update(bytes.subarray(28)), cipher.final()]).toString('utf8'));
      const keys = ['transaction_id', 'state', 'nonce', 'code_verifier', 'return_to', 'expires_at'];
      if (!transaction || Object.keys(transaction).length !== keys.length || !keys.every(key => Object.hasOwn(transaction, key))
        || !/^[A-Za-z0-9-]{36}$/.test(transaction.transaction_id)
        || !['state', 'nonce', 'code_verifier'].every(key => typeof transaction[key] === 'string' && /^[A-Za-z0-9_-]{43}$/.test(transaction[key]))
        || typeof transaction.return_to !== 'string' || !Number.isSafeInteger(transaction.expires_at)
        || transaction.expires_at <= this.#clock() || transaction.expires_at > this.#clock() + this.#transactionLifetime) throw new Error();
      relativeReturnLocation(transaction.return_to);
      return Object.freeze(transaction) as LoginTransaction;
    } catch {
      throw new BffBoundaryError('BFF_LOGIN_TRANSACTION_INVALID', 400);
    }
  }

  validateCallback(request: Request, expectedIssuer: string): LoginTransaction {
    const transaction = this.readTransaction(request);
    const url = new URL(request.url); const query = url.searchParams;
    if (this.#requestOrigin(request) + url.pathname !== this.callbackUri || query.getAll('state').length !== 1 || query.getAll('iss').length !== 1 || query.getAll('code').length !== 1
      || !constantEqual(query.get('state') ?? '', transaction.state) || query.get('iss') !== expectedIssuer || !query.get('code') || query.has('error')) {
      throw new BffBoundaryError('BFF_OAUTH_CALLBACK_INVALID', 400);
    }
    return transaction;
  }

  readHandle(request: Request): string {
    this.requireRequestOrigin(request);
    const handle = readCookie(request, this.handleCookieName);
    if (!handle || !/^dbr_[A-Za-z0-9_-]{43}$/.test(handle)) throw new BffBoundaryError('BFF_SESSION_REQUIRED', 401);
    return handle;
  }

  hasHandleCookie(request: Request): boolean {
    return (request.headers.get('cookie') ?? '').split(';')
      .some(part => part.trim().split('=', 1)[0] === this.handleCookieName);
  }

  handleCookie(handle: string, expiresAt: number): string {
    if (!/^dbr_[A-Za-z0-9_-]{43}$/.test(handle) || !Number.isFinite(expiresAt) || expiresAt <= this.#clock()) {
      throw new BffBoundaryError('BFF_SESSION_INVALID', 401);
    }
    return this.#cookie(this.handleCookieName, handle, Math.floor(expiresAt - this.#clock()));
  }

  csrfToken(handle: string): string {
    if (!/^dbr_[A-Za-z0-9_-]{43}$/.test(handle)) throw new BffBoundaryError('BFF_SESSION_REQUIRED', 401);
    return createHmac('sha256', this.#csrfKey).update(handle).digest('base64url');
  }

  requireRequestOrigin(request: Request): void {
    this.#requestOrigin(request);
  }

  requireMutation(request: Request): string {
    this.requireRequestOrigin(request);
    if (request.headers.get('origin') !== this.publicOrigin) throw new BffBoundaryError('BFF_ORIGIN_DENIED', 403);
    const handle = this.readHandle(request);
    if (!constantEqual(request.headers.get('x-ink-csrf') ?? '', this.csrfToken(handle))) {
      throw new BffBoundaryError('BFF_CSRF_INVALID', 403);
    }
    return handle;
  }

  clearTransactionCookie(): string { return this.#cookie(this.transactionCookieName, '', 0); }
  clearHandleCookie(): string { return this.#cookie(this.handleCookieName, '', 0); }

  #requestOrigin(request: Request): string {
    const requestOrigin = new URL(request.url).origin;
    if (requestOrigin === this.publicOrigin || (this.internalOrigin !== null && requestOrigin === this.internalOrigin)) return this.publicOrigin;
    const host = request.headers.get('host');
    if (host && host.toLowerCase() === new URL(this.publicOrigin).host.toLowerCase()) return this.publicOrigin;
    throw new BffBoundaryError('BFF_ORIGIN_DENIED', 403);
  }

  #cookie(name: string, value: string, maxAge: number): string {
    return `${name}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${this.#secure ? '; Secure' : ''}`;
  }
}
