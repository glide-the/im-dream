// [Input] Production Web/Native settings, AuthProvider and intercepted public API DTOs.
// [Output] Visible link actions with theme/language/account controls and platform-operation receipts.
// [Pos] Technical fixture; synthetic HTTP only. Project/Episode/Artifact/.dream/Run/Hook/PostgreSQL are out of scope.
import {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AuthProvider, useAuth} from '../../app/_dream/contexts/AuthContext';
import ExternalLinksSettings from '../../app/_dream/components/sharing/ExternalLinksSettings';
import NativeSettings from '../../app/_dream/views/story-workspace/ExternalLinksSettings.native';
import {setThemeMode} from '../../app/_dream/utils/theme';
import i18n from '../../app/_dream/i18n';
import '../../app/_dream/index.css';
await i18n.changeLanguage('zh');
setThemeMode('dark');
const facts = {copied: [] as string[], opened: [] as string[], sources: [] as string[], failCopy: false};
export type ExternalLinksFixture = typeof facts;
(window as unknown as {externalLinksFixture: ExternalLinksFixture}).externalLinksFixture = facts;
Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async (value: string) => {if (facts.failCopy) throw Error('fixture clipboard'); facts.copied.push(value);}}});
function Settings() {
  const {user} = useAuth();
  if (!user) return null;
  const source = async (share: {id: string}) => {facts.sources.push(share.id);};
  return new URLSearchParams(location.search).has('native')
    ? <NativeSettings ownerId={user.id} origin="https://public.example" active transport={fetch} onBack={() => {}} onSessionExpired={() => {}} onOpenSource={source}/>
    : <ExternalLinksSettings onOpenSource={source}/>;
}
export function Fixture() {
  const [account, setAccount] = useState(0);
  useEffect(() => {
    const replace = () => setAccount(value => value + 1);
    window.addEventListener('fixture:replace-account', replace);
    return () => window.removeEventListener('fixture:replace-account', replace);
  }, []);
  return <main style={{minHeight:'100dvh',boxSizing:'border-box',padding:20,background:'var(--color-bg-app)',color:'var(--color-text-primary)'}}>
    <nav style={{display:'flex',gap:12,flexWrap:'wrap',marginBottom:24}}>
      <button onClick={() => setThemeMode('light')}>Light</button><button onClick={() => setThemeMode('dark')}>Dark</button>
      <button onClick={() => void i18n.changeLanguage('zh')}>中文</button><button onClick={() => void i18n.changeLanguage('en')}>English</button>
      <button onClick={() => setAccount(value => value + 1)}>Change account</button>
    </nav>
    <div style={{maxWidth:1000,margin:'0 auto',minWidth:0}}><AuthProvider key={account}><Settings/></AuthProvider></div>
  </main>;
}
createRoot(document.getElementById('root')!).render(<Fixture/>);
