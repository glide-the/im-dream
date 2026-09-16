// [Input] Server-projected Admin form actions, selected login/register mode and public auth feedback.
// [Output] Restored Dream email/password/register/Google card submitting credentials directly to Admin.
// [Pos] Dream product login interaction; Admin remains the only credential validator and Session authority.
// [Sync] 2026-09-17: restore the original form while preserving Admin Better Auth + PKCE ownership.
import { useEffect, useState, type FormEvent } from 'react';
import { FaGoogle } from 'react-icons/fa';
import { z } from 'zod';
import { useAuth } from '../../contexts/AuthContext';

const optionsDto = z.strictObject({ password_action: z.url(), google_action: z.url() });
const navigationDto = z.strictObject({ next_url: z.url() });
type EntryMode = 'login' | 'register';

function currentReturnLocation() {
  const target = new URL(window.location.href);
  target.searchParams.delete('auth_error');
  return target.pathname + target.search;
}

function returnedError() {
  const value = new URLSearchParams(window.location.search).get('auth_error');
  if (value === 'credentials') return 'Login failed. Check your email and password.';
  if (value === 'registration') return 'Account creation was not completed. Check the details and try again.';
  if (value === 'google') return 'Google login was not completed. Please try again.';
  return null;
}

const inputStyle = {
  width: '100%', marginTop: '6px', padding: '10px 12px', border: '1px solid var(--color-border-paper)',
  borderRadius: '6px', fontSize: '15px', fontFamily: 'inherit', backgroundColor: 'var(--color-bg-surface-solid)',
  color: 'var(--color-text-body)', boxSizing: 'border-box',
} as const;
const labelStyle = { display: 'block', marginBottom: '16px', fontSize: '14px', fontWeight: 500, color: 'var(--color-text-secondary)' } as const;

export default function AuthEntry({ mode, onSwitch }: { mode: EntryMode; onSwitch: () => void }) {
  const { authError } = useAuth();
  const [options, setOptions] = useState<z.infer<typeof optionsDto> | null>(null);
  const [entryError, setEntryError] = useState<string | null>(() => returnedError());
  const [busy, setBusy] = useState(false);
  const returnTo = currentReturnLocation();

  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.has('auth_error')) {
      url.searchParams.delete('auth_error');
      window.history.replaceState(null, document.title, url.pathname + url.search + url.hash);
    }
    const abort = new AbortController();
    void fetch('/auth/options', { credentials: 'same-origin', cache: 'no-store', signal: abort.signal })
      .then(async response => {
        if (!response.ok) throw new Error('AUTH_OPTIONS_UNAVAILABLE');
        const parsed = optionsDto.safeParse(await response.json());
        if (!parsed.success) throw new Error('AUTH_OPTIONS_INVALID');
        setOptions(parsed.data);
      })
      .catch(() => { if (!abort.signal.aborted) setEntryError('Login is temporarily unavailable. Please try again.'); });
    return () => abort.abort();
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>, kind: 'password' | 'google') => {
    event.preventDefault();
    if (!options) {
      setEntryError('Login is temporarily unavailable. Please try again.');
      return;
    }
    setBusy(true);
    setEntryError(null);
    const form = event.currentTarget;
    const body = new URLSearchParams();
    for (const [key, value] of new FormData(form)) {
      if (typeof value === 'string') body.append(key, value);
    }
    try {
      const response = await fetch(form.action, {
        method: 'POST', body, credentials: 'include', cache: 'no-store', headers: { accept: 'application/json' },
      });
      if (!response.ok) {
        setEntryError(kind === 'google'
          ? 'Google login was not completed. Please try again.'
          : mode === 'register'
          ? 'Account creation was not completed. Check the details and try again.'
          : 'Login failed. Check your email and password.');
        return;
      }
      const parsed = navigationDto.safeParse(await response.json());
      if (!parsed.success) throw new Error('AUTH_NAVIGATION_INVALID');
      window.location.assign(parsed.data.next_url);
    } catch {
      setEntryError('Login is temporarily unavailable. Please try again.');
    } finally {
      setBusy(false);
    }
  };
  const error = authError || entryError;

  return <div style={{ width: '100%', maxWidth: '400px', margin: '0 auto', padding: '32px', backgroundColor: 'var(--color-bg-paper)', border: '2px solid var(--color-border-paper)', borderRadius: '12px', boxShadow: '0 4px 12px var(--color-shadow-soft)', fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif" }}>
    <h2 style={{ margin: '0 0 24px', fontSize: '24px', fontWeight: 600, color: 'var(--color-text-body)', textAlign: 'center' }}>{mode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
    {error && <div role="alert" style={{ padding: '12px', marginBottom: '16px', backgroundColor: 'color-mix(in srgb, var(--color-state-danger) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--color-state-danger) 25%, transparent)', borderRadius: '6px', fontSize: '14px', color: 'var(--color-state-danger)' }}>{error}</div>}
    <form action={options?.google_action} method="post" onSubmit={event => { void handleSubmit(event, 'google'); }}>
      <input name="return_to" type="hidden" value={returnTo} />
      <button type="submit" disabled={busy || !options} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '11px', border: '1px solid var(--color-border-paper)', borderRadius: '6px', backgroundColor: 'var(--color-bg-surface-solid)', color: 'var(--color-text-body)', fontSize: '15px', fontWeight: 600, cursor: busy || !options ? 'not-allowed' : 'pointer', fontFamily: 'inherit', marginBottom: '18px' }}><FaGoogle aria-hidden="true" />Continue with Google</button>
    </form>
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '18px', color: 'var(--color-text-muted)', fontSize: '13px' }}><div style={{ flex: 1, height: '1px', backgroundColor: 'var(--color-border-paper)' }} /><span>or</span><div style={{ flex: 1, height: '1px', backgroundColor: 'var(--color-border-paper)' }} /></div>
    <form action={options?.password_action} method="post" onSubmit={event => { void handleSubmit(event, 'password'); }}>
      <input name="mode" type="hidden" value={mode} />
      <input name="return_to" type="hidden" value={returnTo} />
      {mode === 'register' && <label style={labelStyle}>Display Name (Optional)<input autoComplete="name" disabled={busy} name="name" style={inputStyle} /></label>}
      <label style={labelStyle}>Email<input autoComplete="email" disabled={busy} name="email" required type="email" style={inputStyle} /></label>
      <label style={{ ...labelStyle, marginBottom: '24px' }}>Password<input autoComplete={mode === 'register' ? 'new-password' : 'current-password'} disabled={busy} minLength={mode === 'register' ? 6 : undefined} name="password" required type="password" style={inputStyle} />{mode === 'register' && <span style={{ display: 'block', marginTop: '4px', fontSize: '12px', color: 'var(--color-text-muted)' }}>At least 6 characters</span>}</label>
      <button type="submit" disabled={busy || !options} style={{ width: '100%', padding: '12px', border: 'none', borderRadius: '6px', backgroundColor: busy || !options ? 'var(--color-disabled-bg)' : 'var(--color-action-link)', color: 'var(--color-text-on-action)', fontSize: '16px', fontWeight: 600, cursor: busy || !options ? 'not-allowed' : 'pointer', fontFamily: 'inherit' }}>{busy ? (mode === 'login' ? 'Logging in...' : 'Creating account...') : mode === 'login' ? 'Login' : 'Register'}</button>
    </form>
    <div style={{ marginTop: '20px', textAlign: 'center', fontSize: '14px', color: 'var(--color-text-secondary)' }}>{mode === 'login' ? "Don't have an account? " : 'Already have an account? '}<button type="button" onClick={onSwitch} disabled={busy} style={{ background: 'none', border: 'none', color: 'var(--color-action-link)', cursor: busy ? 'not-allowed' : 'pointer', textDecoration: 'underline', fontSize: '14px', fontFamily: 'inherit' }}>{mode === 'login' ? 'Register' : 'Login'}</button></div>
  </div>;
}
