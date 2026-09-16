// [Input] Existing Dream registration callbacks and the shared Admin-submitting product form.
// [Output] Restored Dream registration card with optional display name, password and Google choices.
// [Pos] RegisterForm import boundary; account creation, Session and token authority remain Admin-owned.
// [Sync] 2026-09-17: restore the original registration interaction on the Admin form-entry contract.
import AuthEntry from './AuthEntry';

interface RegisterFormProps {
  onSuccess: () => void;
  onSwitchToLogin: () => void;
}
export default function RegisterForm(props: RegisterFormProps) {
  void props.onSuccess;
  return <AuthEntry mode="register" onSwitch={props.onSwitchToLogin} />;
}
