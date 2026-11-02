// [Input] Existing browser authentication context and normal login forms.
// [Output] Public authenticated content using the current Web login contract.
// [Pos] Web platform session boundary.
import {useState, type ReactNode} from 'react';
import {AuthProvider, useAuth} from '../../app/_dream/contexts/AuthContext';
import LoginForm from '../../app/_dream/components/Auth/LoginForm';
import RegisterForm from '../../app/_dream/components/Auth/RegisterForm';
import {Text} from 'react-native';
function Session({children}: {children: (logout: () => Promise<void>) => ReactNode}) {
  const auth = useAuth();
  const [register, setRegister] = useState(false);
  if (auth.isLoading) return <Text>正在打开工作区…</Text>;
  if (!auth.isAuthenticated) return register
    ? <RegisterForm onSuccess={() => undefined} onSwitchToLogin={() => setRegister(false)} />
    : <LoginForm onSuccess={() => undefined} onSwitchToRegister={() => setRegister(true)} />;
  return children(auth.logout);
}
export default function SessionGate(props: {children: (logout: () => Promise<void>) => ReactNode}) {
  return <AuthProvider><Session {...props} /></AuthProvider>;
}
