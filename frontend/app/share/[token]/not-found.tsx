// [Input] Missing, malformed or revoked public share result.
// [Output] One anonymous unavailable state without source or account disclosure.
// [Pos] Public share error boundary.
export default function ShareNotFound() {return <main style={{padding: 32, color: 'var(--color-text-primary)'}}><h1>此链接已失效或无法访问</h1><p>This share link is unavailable.</p></main>;}
