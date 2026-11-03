// [Sync] 2026-11-02: connect original account failures to runtime diagnostics and align the packaged native callback.
// [Sync] 2026-11-02: register a diagnostics-only native window leaf on the existing bridge and runtime snapshot.
// [Input] Existing startup/read results, original errors and the native copy action.
// [Sync] 2026-11-03: show actual bounded CPU/activity charts with a foreground-only shared sampler lease.
// [Output] Read-only startup diagnostics available before local services or authentication are ready.
// [Pos] Shared native developer leaf; refresh never starts a runtime or sends an HTTP request.
// [Sync] 2026-11-01: show and copy original error text, including native error details, without redaction.
import {useEffect, useRef, useState} from 'react';
import {AppState, BackHandler, NativeModules, Platform, Pressable, ScrollView, StyleSheet, Text, View} from 'react-native';
import InkLabel from './InkLabel.native';
import useInkColors from './useInkColors.native';
import RuntimePerformanceCharts from './RuntimePerformanceCharts.native';
import {initialPerformanceState} from '../runtime/runtimePerformance';
import {BackendRuntimeManager, formatRuntimeDiagnostics} from '../runtime/BackendRuntimeManager';

const startupLabels = {idle: '尚未启动', starting: '正在启动', ready: '本地服务已就绪', failed: '启动失败'};
const sessionLabels = {reading: '正在读取', available: '原会话有效', signed_out: '当前未登录', unavailable: '原会话读取失败'};
const errorLabels = {startup: '启动', session: '登录会话', config: '配置读取', catalog: 'Agent 目录', login: '登录页面', registration: '注册', google: 'Google 登录', recovery: '输入恢复'};

export function RuntimeDiagnosticsWindow() {
  return <RuntimeDiagnostics onBack={()=>NativeModules.InkRuntime.dismissRuntimeDiagnostics()}/>;
}

export default function RuntimeDiagnostics({onBack,active=true}: {onBack: () => void;active?:boolean}) {
  const colors = useInkColors();
  const [snapshot, setSnapshot] = useState(BackendRuntimeManager.getSnapshot);
  const [paused, setPaused] = useState(AppState.currentState === 'background' || AppState.currentState === 'inactive');
  const [readAt, setReadAt] = useState(Date.now);
  const [feedback, setFeedback] = useState('');
  const mounted = useRef(true), copying = useRef(false);
  useEffect(() => {
    mounted.current = true;
    setPaused(!active||AppState.currentState!=='active');
    let unsubscribe: (() => void) | undefined;
    const read = () => { setSnapshot(BackendRuntimeManager.getSnapshot()); setReadAt(Date.now()); };
    const observe = () => { unsubscribe?.(); read(); unsubscribe = BackendRuntimeManager.subscribe(read); };
    if (active&&AppState.currentState === 'active') observe();
    const performanceLease=BackendRuntimeManager.observePerformance(active&&AppState.currentState==='active');
    const lifecycle = AppState.addEventListener('change', state => {
      const foreground = state === 'active'; setPaused(!active||!foreground);
      performanceLease.setActive(active&&foreground);
      if (active&&foreground) observe(); else { unsubscribe?.(); unsubscribe = undefined; }
    });
    return () => { mounted.current = false; unsubscribe?.(); lifecycle.remove(); performanceLease.release(); };
  }, [active]);
  useEffect(() => {
    if (Platform.OS !== 'android') return;
    const listener = BackHandler.addEventListener('hardwareBackPress', () => { onBack(); return true; });
    return () => listener.remove();
  }, [onBack]);
  const text = {color: colors['color-text-primary']};
  const date = (value?: number) => value === undefined ? '未观测' : new Date(value).toLocaleString();
  const row = (label: string, value: string) => <View style={styles.row}><InkLabel style={{color: colors['color-text-secondary']}}>{label}</InkLabel><InkLabel selectable style={text}>{value}</InkLabel></View>;
  const refresh = () => { setSnapshot(BackendRuntimeManager.getSnapshot()); setReadAt(Date.now()); setFeedback('状态已刷新'); };
  async function copy() {
    if (copying.current) return;
    copying.current = true;
    try {
      await NativeModules.InkRuntime.copyText(formatRuntimeDiagnostics(snapshot));
      if (mounted.current) setFeedback('诊断摘要已复制');
    } catch { if (mounted.current) setFeedback('复制失败，请重试。'); }
    finally { copying.current = false; }
  }
  return <View accessibilityViewIsModal style={[styles.fill, {backgroundColor: colors['color-bg-app']}]}>
    <View style={styles.header}><Pressable accessibilityRole="button" onPress={onBack} style={styles.button}><InkLabel style={text}>返回</InkLabel></Pressable><InkLabel accessibilityRole="header" style={[styles.title, text]}>开发者控制页</InkLabel></View>
    <ScrollView style={styles.fill} contentContainerStyle={styles.content}>
      {row('启动状态', startupLabels[snapshot.state])}
      <RuntimePerformanceCharts state={snapshot.performance??initialPerformanceState()} onPause={value=>BackendRuntimeManager.pausePerformance(value)}/>
      <InkLabel accessibilityRole="header" style={[styles.title, text]}>错误日志</InkLabel>
      <InkLabel style={{color: colors['color-text-secondary']}}>本次应用中各来源最近一次错误，按原文显示。</InkLabel>
      {Object.values(snapshot.errors ?? {}).sort((a, b) => b.at - a.at).map(item => <View key={item.source} style={styles.row}>
        <InkLabel style={text}>{`${errorLabels[item.source]} · ${date(item.at)}`}</InkLabel>
        <Text selectable style={[text, {fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace'}]}>{item.text}</Text>
      </View>)}
      {!Object.keys(snapshot.errors ?? {}).length ? <InkLabel style={text}>当前没有错误记录</InkLabel> : null}
      {row('开始时间', date(snapshot.startedAt))}
      {row('总耗时', snapshot.elapsedMs === undefined ? '尚未完成' : `${snapshot.elapsedMs} ms`)}
      {row('最后更新时间', date(snapshot.updatedAt))}
      {row('本地就绪', snapshot.state === 'ready' ? '原启动装配已完成' : '尚未就绪')}
      {row('原会话读取', snapshot.sessionRead ? sessionLabels[snapshot.sessionRead.state] : '未观测')}
      {row('会话观测时间', date(snapshot.sessionRead?.updatedAt))}
      {row('公网连接', '未单独观测')}
      {row('启动错误码', snapshot.errorCode ?? '无')}
      {snapshot.state === 'failed' ? <InkLabel style={text}>{snapshot.errorCode === 'CAPABILITY_UNAVAILABLE' ? '当前端侧运行能力尚未就绪。' : '本地启动失败，请关闭后重新打开应用。'}</InkLabel> : null}
      <InkLabel style={{color: colors['color-text-secondary']}}>展示当前应用内的启动、会话与本进程采样结果。</InkLabel>
      {row(paused ? '观测已暂停，上次读取' : '本页读取时间', date(readAt))}
    </ScrollView>
    <View style={[styles.footer, {borderColor: colors['color-border-paper']}]}>
      <View style={styles.actions}><Pressable accessibilityRole="button" disabled={paused} onPress={refresh} style={styles.button}><InkLabel style={text}>刷新</InkLabel></Pressable><Pressable accessibilityRole="button" disabled={paused || snapshot.state === 'idle'} onPress={() => void copy()} style={styles.button}><InkLabel style={text}>复制诊断摘要</InkLabel></Pressable></View>
      <InkLabel accessibilityLiveRegion="polite" style={text}>{feedback}</InkLabel>
    </View>
  </View>;
}

const styles = StyleSheet.create({fill: {flex: 1, minHeight: 0}, header: {flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12}, title: {fontSize: 22}, button: {minHeight: 44, padding: 12, justifyContent: 'center'}, content: {padding: 20, gap: 20}, row: {gap: 6}, footer: {padding: 12, borderTopWidth: StyleSheet.hairlineWidth, gap: 6}, actions: {flexDirection: 'row', flexWrap: 'wrap', gap: 12}});
