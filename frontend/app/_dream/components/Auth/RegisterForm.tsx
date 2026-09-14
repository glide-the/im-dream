// [Input] Existing Dream authentication surface and Admin-owned login/register flow.
// [Output] Reusable public authorization entry with full-page PKCE return.
// [Pos] RegisterForm import boundary; email/signup/Google choices remain on Admin.
// [Sync] 2026-09-14: delegate the sole auth UI without collecting credentials in Dream.
import AuthEntry from './AuthEntry';

interface RegisterFormProps {
  // Existing callers retain their navigation callbacks; OAuth completion returns
  // through BFF and reloads the canonical page rather than invoking local login.
  onSuccess: () => void;
  onSwitchToLogin: () => void;
}
export default function RegisterForm(_props: RegisterFormProps) { return <AuthEntry />; }
