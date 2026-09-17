// [Input] Server-owned public Admin origin/issuer/resource, excluding service credentials.
// [Output] Explicit 410 legacy-auth migration response without reading request bodies or forwarding.
// [Pos] Next retired issuer adapter; BFF/Admin alone execute actual authentication.
// [Sync] 2026-09-14: keep legacy paths explicit across both public Next and Python entry points.
import { publicAdminAuthority } from './admin-client.ts';

export function retiredAuthentication(environment: Readonly<Record<string, string | undefined>> = process.env): Response {
  try {
    const { origin, issuer, resource } = publicAdminAuthority(environment);
    return Response.json({ error: { code: 'DREAM_AUTHENTICATION_RETIRED', message: 'Use the Admin authentication authority.' },
      authentication: { issuer, authorization_endpoint: issuer + '/oauth2/authorize', token_endpoint: issuer + '/oauth2/token',
        device_authorization_endpoint: issuer + '/device/code', revocation_endpoint: issuer + '/oauth2/revoke', jwks_uri: issuer + '/jwks',
        verification_uri: origin + '/auth/device', resource } }, { status: 410, headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return Response.json({ error: { code: 'ADMIN_CONFIGURATION_INVALID', message: 'The Admin authentication authority is not configured.' } },
      { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
