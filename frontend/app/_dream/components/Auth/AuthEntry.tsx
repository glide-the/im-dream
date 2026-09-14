// [Input] AuthContext Admin login entry and public session-check feedback.
// [Output] One reusable login/register card linking to Admin email/signup/Google choices.
// [Pos] Existing Dream auth surface; no password collection or token authority.
// [Sync] 2026-09-14: reuse the original paper-card styles for the sole Admin authorization entry.
import { useAuth } from '../../contexts/AuthContext';

export default function AuthEntry() {
  const { login, authError } = useAuth();
  return <div style={{ width: '100%', maxWidth: '400px', margin: '0 auto', padding: '32px', backgroundColor: 'var(--color-bg-paper)', border: '2px solid var(--color-border-paper)', borderRadius: '12px', boxShadow: '0 4px 12px var(--color-shadow-soft)', fontFamily: "'Excalifont', 'Xiaolai', 'Georgia', serif" }}>
    <h2 style={{ margin: '0 0 16px', fontSize: '24px', color: 'var(--color-text-body)', textAlign: 'center' }}>Log in or create an account</h2>
    <p style={{ color: 'var(--color-text-secondary)', textAlign: 'center', marginBottom: '24px' }}>Use your email or Google account.</p>
    {authError && <p role="alert" style={{ color: 'var(--color-state-danger)' }}>{authError}</p>}
    <button type="button" onClick={login} style={{ width: '100%', padding: '12px', border: 'none', borderRadius: '6px', backgroundColor: 'var(--color-action-link)', color: 'var(--color-text-on-action)', fontSize: '16px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>Continue</button>
  </div>;
}
