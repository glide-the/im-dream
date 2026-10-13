// [Input] Same-origin browser requests, the private login boundary and Admin DTO transport.
// [Output] Actual PKCE login/session/logout handlers plus request-selected Admin form actions, exposing no credential or token.
// [Pos] Server BFF product boundary shared by thin Next auth Route Handlers.
// [Sync] 2026-10-11: select browser center from validated client access while keeping issuer and backchannel fixed.
// [Sync] 2026-09-17: project Admin form actions while preserving recovery and server-only OAuth credentials.
import { randomUUID } from 'node:crypto';
import { AdminBffClient, configuredAdminBffClient } from './admin-client.ts';
import { BffBoundaryError, BffLoginBoundary } from './login-boundary.ts';

function json(body: unknown, status = 200): Response {
  return Response.json(body, { status, headers: { 'cache-control': 'no-store' } });
}

export function bffFailure(error: unknown): Response {
  const failure = error instanceof BffBoundaryError ? error : new BffBoundaryError('BFF_REQUEST_FAILED', 503);
  return json({ detail: failure.code }, failure.status);
}

function browserAdminOrigin(request: Request, boundary: BffLoginBoundary, admin: AdminBffClient): string {
  const client = new URL(boundary.browserRequestOrigin(request));
  if (!['localhost', '127.0.0.1', '[::1]'].includes(client.hostname)) return admin.origin;
  const destination = new URL(admin.transportOrigin);
  if (!['localhost', '127.0.0.1', '[::1]'].includes(destination.hostname)) {
    throw new BffBoundaryError('BFF_ADMIN_LOCAL_UNAVAILABLE', 503);
  }
  destination.hostname = client.hostname;
  return destination.origin;
}

export function createBffHandlers(boundary: BffLoginBoundary, admin: AdminBffClient) {
  const browserAdmin = admin.forBrowserOrigin(boundary.publicOrigin);
  return {
    async options(request: Request): Promise<Response> {
      try {
        const adminOrigin = browserAdminOrigin(request, boundary, browserAdmin);
        await browserAdmin.capabilities(randomUUID(), request.signal);
        return json({
          password_action: new URL('/auth/dream/password', adminOrigin).href,
          google_action: new URL('/auth/dream/google', adminOrigin).href,
        });
      } catch (error) { return bffFailure(error); }
    },
    async device(request: Request): Promise<Response> {
      try {
        const adminOrigin = browserAdminOrigin(request, boundary, browserAdmin);
        const incoming = new URL(request.url);
        if (incoming.searchParams.getAll('user_code').length > 1) throw new BffBoundaryError('BFF_DEVICE_CODE_INVALID', 400);
        await browserAdmin.capabilities(randomUUID(), request.signal);
        const destination = new URL('/auth/device', adminOrigin);
        const code = incoming.searchParams.get('user_code');
        if (code !== null) destination.searchParams.set('user_code', code);
        return new Response(null, { status: 303, headers: { location: destination.href, 'cache-control': 'no-store' } });
      } catch (error) { return bffFailure(error); }
    },
    async start(request: Request): Promise<Response> {
      try {
        const adminOrigin = browserAdminOrigin(request, boundary, browserAdmin);
        const incoming = new URL(request.url);
        if (incoming.searchParams.getAll('return_to').length > 1) throw new BffBoundaryError('BFF_RETURN_LOCATION_INVALID', 400);
        const transaction = boundary.createTransaction(incoming.searchParams.get('return_to') ?? '/');
        const caps = await browserAdmin.capabilities(transaction.transaction_id, request.signal);
        const authorize = new URL('/api/auth/oauth2/authorize', adminOrigin);
        authorize.search = new URLSearchParams({
          response_type: 'code', client_id: caps.auth.clients.browser, redirect_uri: boundary.callbackUri,
          resource: browserAdmin.resource, scope: caps.auth.scopes.join(' '), state: transaction.state,
          nonce: transaction.nonce, code_challenge: boundary.codeChallenge(transaction), code_challenge_method: 'S256',
        }).toString();
        return new Response(null, { status: 303, headers: {
          location: authorize.href, 'set-cookie': boundary.transactionCookie(transaction), 'cache-control': 'no-store',
        } });
      } catch (error) { return bffFailure(error); }
    },

    async callback(request: Request): Promise<Response> {
      try {
        const transaction = boundary.validateCallback(request, browserAdmin.issuer);
        const code = new URL(request.url).searchParams.get('code')!;
        const result = await browserAdmin.exchange(transaction.transaction_id, code, transaction.code_verifier, boundary.callbackUri, request.signal);
        const headers = new Headers({ location: transaction.return_to, 'cache-control': 'no-store' });
        headers.append('set-cookie', boundary.handleCookie(result.handle, Date.parse(result.expires_at) / 1_000));
        headers.append('set-cookie', boundary.clearTransactionCookie());
        return new Response(null, { status: 303, headers });
      } catch (error) {
        // Keep the original transaction cookie after an unknown exchange.
        // Reloading this same callback recovers Admin's encrypted original handle.
        return bffFailure(error);
      }
    },

    async session(request: Request): Promise<Response> {
      try {
        const browserHandle = boundary.readHandle(request);
        const requestId = randomUUID();
        const resolution = await browserAdmin.resolve(browserHandle, requestId, request.signal);
        const profile = await browserAdmin.currentProfile(resolution, requestId, request.signal);
        return json({
          user: { id: profile.id, email: profile.email, display_name: profile.display_name,
            avatar_url: profile.avatar_url, role: profile.role, created_at: profile.created_at },
          csrf_token: boundary.csrfToken(browserHandle),
        });
      } catch (error) { return bffFailure(error); }
    },

    async logout(request: Request): Promise<Response> {
      try {
        const browserHandle = boundary.requireMutation(request);
        await browserAdmin.revoke(browserHandle, randomUUID(), request.signal);
        const response = json({ success: true });
        response.headers.append('set-cookie', boundary.clearHandleCookie());
        response.headers.append('set-cookie', boundary.clearTransactionCookie());
        return response;
      } catch (error) {
        // An unavailable revoke retains the handle for explicit same-handle recovery.
        return bffFailure(error);
      }
    },
  };
}

export function configuredBffHandlers(request: Request) {
  return createBffHandlers(BffLoginBoundary.fromRequest(request), configuredAdminBffClient());
}
