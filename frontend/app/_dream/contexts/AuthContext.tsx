// [Input] OAuth Bearer profile state and Admin-submitting Dream login forms.
// [Output] React public user/authentication state with success-only logout and safe failure feedback.
// [Pos] Public authentication context; Web credentials stay in the private transport owner.
// [Sync] 2026-11-20: restore cross-tab login changes and discard React commits superseded by shared logout.
// [Sync] 2026-11-19: reflect revoked/cleared Web credentials without exposing credentials to React consumers.
// [Sync] 2026-09-17: let restored Dream forms submit directly to Admin while keeping browser state token-free.
// [Sync] 2026-09-15: commit only the current Browser owner snapshot after asynchronous session loading.
// [Sync] 2026-10-27: publish only authenticated state to the RN navigation owner.
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { STORAGE_KEYS } from '../constants/storageKeys';
import { isBrowserSessionCurrent, loadBrowserSession, revokeBrowserSession, type BrowserUser } from '../lib/browserSession';
import {isReactNativeHost, reportMobileHostRoute} from '../platform/mobileHost';

interface AuthContextType {
  user: BrowserUser | null;
  isLoading: boolean;
  authError: string | null;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<BrowserUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  useEffect(() => {
    if (!isLoading) reportMobileHostRoute(user !== null, authError !== null);
  }, [isLoading, user, authError]);
  useEffect(() => {
    const abort = new AbortController();
    let restoreIdentity: object = {};
    const restoreSession = () => {
      const identity = {}; restoreIdentity = identity;
      setIsLoading(true);
      const current = () => !abort.signal.aborted && restoreIdentity === identity;
      void loadBrowserSession(fetch, abort.signal).then(session => {
        if (current() && isBrowserSessionCurrent(session)) { setUser(session?.user ?? null); setAuthError(null); }
      }).catch(() => {
        if (current()) setAuthError('Unable to check your session. Please try again.');
      }).finally(() => { if (current()) setIsLoading(false); });
    };
    const authChanged = (event: Event) => {
      if (abort.signal.aborted) return;
      restoreIdentity = {}; setUser(null); setAuthError(null);
      if ((event as CustomEvent<{ restore?: boolean }>).detail?.restore) restoreSession();
      else setIsLoading(false);
    };
    window.addEventListener('ink:auth-state', authChanged);
    // Discard retired credentials without adopting or transmitting them.
    try { localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN); } catch { /* Retired localStorage credentials never participate in authentication. */ }
    if (new URLSearchParams(window.location.hash.slice(1)).has('access_token')) {
      window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
    }
    restoreSession();
    return () => { abort.abort(); window.removeEventListener('ink:auth-state', authChanged); };
  }, []);

  const logout = useCallback(async () => {
    try { await revokeBrowserSession(); setUser(null); setAuthError(null); }
    catch { setAuthError('Unable to log out. Please try again.'); }
  }, []);
  useEffect(() => {
    if (!isReactNativeHost()) return;
    const requestLogout = () => { void logout(); };
    window.addEventListener('ink:host-logout', requestLogout);
    return () => window.removeEventListener('ink:host-logout', requestLogout);
  }, [logout]);
  return <AuthContext.Provider value={{ user, isLoading, authError, logout, isAuthenticated: user !== null }}>{children}</AuthContext.Provider>;
}

// This hook shares the private provider context and exports no credential state.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
