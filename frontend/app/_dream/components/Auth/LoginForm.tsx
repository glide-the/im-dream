// [Input] Existing Dream authentication surface and Admin-owned login/register flow.
// [Output] Reusable public authorization entry with full-page PKCE return.
// [Pos] LoginForm import boundary; email/signup/Google choices remain on Admin.
// [Sync] 2026-09-14: delegate the sole auth UI without collecting credentials in Dream.
import AuthEntry from './AuthEntry';

interface LoginFormProps {
  // Existing callers retain their navigation callbacks; OAuth completion returns
  // through BFF and reloads the canonical page rather than invoking local login.
  onSuccess: () => void;
  onSwitchToRegister: () => void;
}
export default function LoginForm(_props: LoginFormProps) { return <AuthEntry />; }
