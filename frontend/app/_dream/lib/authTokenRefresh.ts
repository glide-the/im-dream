// [Input] Backend sliding token renewal via X-New-Access-Token response header.
// [Output] Global fetch interceptor that adopts renewed tokens into localStorage
//          and notifies the React auth context.
// [Pos] frontend auth token refresh helper
// [Sync] 2026-08-03: backend access tokens now expire after 1h with sliding
//                    renewal; active sessions adopt fresh tokens automatically.
/**
 * Sliding token renewal interceptor.
 *
 * The backend attaches a freshly signed JWT to the `X-New-Access-Token`
 * response header once the current token is past half of its lifetime. This
 * module patches `window.fetch` once so every API response is inspected and
 * renewed tokens are adopted transparently.
 */

import { STORAGE_KEYS } from '../constants/storageKeys';

export const AUTH_TOKEN_RENEWED_EVENT = 'auth:token-renewed';
const NEW_ACCESS_TOKEN_HEADER = 'x-new-access-token';

let installed = false;

export function installAuthTokenRefreshInterceptor(): void {
  if (installed || typeof window === 'undefined' || typeof window.fetch !== 'function') {
    return;
  }
  installed = true;

  const originalFetch = window.fetch.bind(window);

  window.fetch = async (...args: Parameters<typeof fetch>): Promise<Response> => {
    const response = await originalFetch(...args);

    try {
      const newToken = response.headers.get(NEW_ACCESS_TOKEN_HEADER);
      if (newToken && newToken !== localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN)) {
        localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, newToken);
        window.dispatchEvent(
          new CustomEvent<string>(AUTH_TOKEN_RENEWED_EVENT, { detail: newToken })
        );
      }
    } catch {
      // Token adoption must never break the underlying request.
    }

    return response;
  };
}
