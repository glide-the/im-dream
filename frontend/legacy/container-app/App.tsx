// [Input] Historical embedded backend readiness, persistent WebView state and user navigation.
// [Output] RN startup/recovery UI and Chat/Decks/More navigation around unchanged business pages.
// [Pos] iOS/Android RN composition root; native platform modules own runtime/system resources.
import {useEffect, useState} from 'react';
import {
  ActivityIndicator, Keyboard, Pressable, SafeAreaView, StatusBar,
  StyleSheet, Text, useColorScheme, View,
} from 'react-native';
import {BackendRuntimeManager} from './runtime/BackendRuntimeManager';
import BusinessWebSurface, {type WebState} from './web/BusinessWebSurface';

const paths = {
  chat: '/story-workspace/chat', decks: '/story-workspace/decks',
  writing: '/story-workspace/writing', timeline: '/story-workspace/timeline',
  analysis: '/story-workspace/analysis', settings: '/story-workspace/settings',
};

export default function App() {
  const systemDark = useColorScheme() === 'dark';
  const [runtime, setRuntime] = useState<'starting' | 'ready' | 'failed'>('starting');
  const [attempt, setAttempt] = useState(0);
  const [web, setWeb] = useState<WebState>({loading: true, authenticated: false});
  const [navigation, setNavigation] = useState({path: paths.chat, revision: 0});
  const [more, setMore] = useState(false);
  const [keyboard, setKeyboard] = useState(false);
  const [logoutRequest, setLogoutRequest] = useState(0);
  const dark = web.mode === 'dark' || (web.mode !== 'light' && systemDark);
  const background = web.background ?? (dark ? '#1f1b16' : '#f6efe5');
  const foreground = dark ? '#f2e8d8' : '#30291f';

  useEffect(() => {
    let active = true;
    setRuntime('starting');
    BackendRuntimeManager.ensureStarted().then(
      () => {if (active) setRuntime('ready');},
      () => {if (active) setRuntime('failed');},
    );
    return () => {active = false;};
  }, [attempt]);
  useEffect(() => {
    const shown = Keyboard.addListener('keyboardWillShow', () => setKeyboard(true));
    const hidden = Keyboard.addListener('keyboardWillHide', () => setKeyboard(false));
    return () => {shown.remove(); hidden.remove();};
  }, []);
  useEffect(() => {if (!web.authenticated) setMore(false);}, [web.authenticated]);
  const navigate = (path: string) => {
    setMore(false);
    setNavigation(current => ({path, revision: current.revision + 1}));
  };
  const button = (label: string, action: () => void, selected = false) => (
    <Pressable accessibilityRole="button" accessibilityLabel={label}
      accessibilityState={{selected}} onPress={action}
      style={[styles.button, selected && {backgroundColor: dark ? '#3a3026' : '#e9ddcb'}]}>
      <Text style={{color: foreground, fontSize: 17}}>{label}</Text>
    </Pressable>
  );
  return (
    <SafeAreaView style={[styles.root, {backgroundColor: background}]}>
      <StatusBar barStyle={dark ? 'light-content' : 'dark-content'} />
      {runtime !== 'ready' ? (
        <View style={styles.startup} accessibilityLabel="Ink Memory startup">
          <Text style={[styles.title, {color: foreground}]}>Ink &amp; Memory</Text>
          {runtime === 'starting' ? <ActivityIndicator color={foreground} /> : null}
          <Text style={{color: foreground}}>{runtime === 'starting' ? '正在打开工作区…' : '工作区暂时无法打开，请重试。'}</Text>
          {runtime === 'failed' ? button('重试', () => setAttempt(value => value + 1)) : null}
        </View>
      ) : (
        <>
          <View style={styles.content}>
            <BusinessWebSurface style={styles.content} navigationRequest={navigation} logoutRequest={logoutRequest}
              onHostState={event => {
                const state = event.nativeEvent;
                setWeb(current => ({...current, ...state}));
              }} />
            {web.loading || web.failed ? (
              <View style={[styles.recovery, {backgroundColor: background}]}>
                {web.failed ? <>
                  <Text style={{color: foreground}}>页面载入失败，当前任务与历史保留。</Text>
                  {button('重新载入', () => navigate(web.path ?? paths.chat))}
                </> : <ActivityIndicator color={foreground} />}
              </View>
            ) : null}
            {more && web.authenticated ? (
              <View style={[StyleSheet.absoluteFill, styles.more, {backgroundColor: background}]}>
                <Text style={[styles.title, {color: foreground}]}>More</Text>
                {button('Write', () => navigate(paths.writing))}
                {button('Timeline', () => navigate(paths.timeline))}
                {button('Analysis', () => navigate(paths.analysis))}
                {button('Settings', () => navigate(paths.settings))}
                {button('退出登录', () => setLogoutRequest(value => value + 1))}
                {web.authFailure ? <Text style={{color: foreground}}>退出失败，请重试。</Text> : null}
                {button('返回', () => setMore(false))}
              </View>
            ) : null}
          </View>
          {web.authenticated && !keyboard ? (
            <View style={[styles.tabs, {borderColor: dark ? '#514535' : '#d7c7af'}]}>
              {button('Chat', () => navigate(paths.chat), !more && web.path?.startsWith(paths.chat))}
              {button('Decks', () => navigate(paths.decks), !more && web.path?.startsWith(paths.decks))}
              {button('More', () => setMore(value => !value), more || (!!web.path && !web.path.startsWith(paths.chat) && !web.path.startsWith(paths.decks)))}
            </View>
          ) : null}
        </>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1}, content: {flex: 1},
  startup: {flex: 1, alignItems: 'center', justifyContent: 'center', gap: 24, padding: 24},
  title: {fontSize: 24, fontWeight: '600', marginBottom: 16},
  tabs: {flexDirection: 'row', justifyContent: 'space-around', borderTopWidth: StyleSheet.hairlineWidth, padding: 6},
  button: {minHeight: 48, minWidth: 82, padding: 12, borderRadius: 14, alignItems: 'center', justifyContent: 'center'},
  more: {padding: 24, gap: 12},
  recovery: {...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center', gap: 20},
});
