// [Input] Same-origin BFF session/profile, in-memory CSRF and Admin-submitting Dream login forms.
// [Output] React public user/authentication state with success-only logout and safe failure feedback.
// [Pos] Browser auth context; Admin/Dream servers own all OAuth credentials.
// [Sync] 2026-09-17: let restored Dream forms submit directly to Admin while keeping browser state token-free.
// [Sync] 2026-09-15: commit only the current Browser owner snapshot after asynchronous session loading.
import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { STORAGE_KEYS } from '../constants/storageKeys';
import { isBrowserSessionCurrent, loadBrowserSession, revokeBrowserSession, type BrowserUser } from '../lib/browserSession';

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
    const abort = new AbortController();
    // Discard retired credentials without adopting or transmitting them.
    try { localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN); } catch { /* Cookie auth does not depend on Browser storage. */ }
    if (new URLSearchParams(window.location.hash.slice(1)).has('access_token')) {
      window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
    }
    void loadBrowserSession(fetch, abort.signal).then(session => {
      if (!abort.signal.aborted && isBrowserSessionCurrent(session)) { setUser(session?.user ?? null); setAuthError(null); }
    }).catch(() => {
      if (!abort.signal.aborted) setAuthError('Unable to check your session. Please try again.');
    }).finally(() => { if (!abort.signal.aborted) setIsLoading(false); });
    return () => abort.abort();
  }, []);

  const logout = async () => {
    try { await revokeBrowserSession(); setUser(null); setAuthError(null); }
    catch { setAuthError('Unable to log out. Please try again.'); }
  };
  return <AuthContext.Provider value={{ user, isLoading, authError, logout, isAuthenticated: user !== null }}>{children}</AuthContext.Provider>;
}

// This hook shares the private provider context and exports no credential state.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
