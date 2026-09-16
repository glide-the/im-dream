// [Input] Existing Dream login callbacks and the shared Admin-submitting product form.
// [Output] Restored Dream login card with email/password/Google choices.
// [Pos] LoginForm import boundary; validation, Session and token authority remain Admin-owned.
// [Sync] 2026-09-17: restore the original login interaction on the Admin form-entry contract.
import AuthEntry from './AuthEntry';

interface LoginFormProps {
  onSuccess: () => void;
  onSwitchToRegister: () => void;
}
export default function LoginForm(props: LoginFormProps) {
  void props.onSuccess;
  return <AuthEntry mode="login" onSwitch={props.onSwitchToRegister} />;
}
