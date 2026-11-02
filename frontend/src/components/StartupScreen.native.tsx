// [Input] Existing preparation/session phase, current theme and the diagnostics action.
// [Output] Centered vector/wordmark composition with a separate status and utility footer.
// [Pos] Native initial preparation view; SessionGate owns startup, login and failure transitions.
// [Sync] 2026-11-02: align transparent artwork, project typography and safe-area content in short/portrait/landscape layouts.
import {ActivityIndicator, Pressable, StyleSheet, useWindowDimensions, View} from 'react-native';
import InkLabel from './InkLabel.native';
import StartupArtwork from './StartupArtwork.native';
import useInkColors from './useInkColors.native';

export default function StartupScreen({visible, checkingSession, onDiagnostics}: {visible: boolean; checkingSession: boolean; onDiagnostics: () => void}) {
  const colors = useInkColors();
  const {height, width} = useWindowDimensions();
  const size = Math.min(176, height * 0.26, width * 0.44);
  return <View testID="startup-screen" style={[styles.screen, {backgroundColor: colors['color-bg-app']}]}>
    <View style={styles.brand}>
      <StartupArtwork visible={visible} size={size}/>
      <InkLabel style={[styles.wordmark, {color: colors['color-text-primary']}]}>Ink &amp; Memory</InkLabel>
    </View>
    <View style={styles.footer}>
      <View accessibilityRole="progressbar" style={styles.status}>
        <ActivityIndicator size="small" color={colors['color-text-muted']}/>
        <InkLabel style={[styles.statusText, {color: colors['color-text-secondary']}]}>{checkingSession ? '正在检查登录状态' : '正在准备'}</InkLabel>
      </View>
      <Pressable accessibilityRole="button" onPress={onDiagnostics} style={styles.developer}>
        <InkLabel style={[styles.developerText, {color: colors['color-text-muted']}]}>开发者控制页</InkLabel>
      </Pressable>
    </View>
  </View>;
}

const styles = StyleSheet.create({
  screen: {flex: 1, paddingHorizontal: 24},
  brand: {position: 'absolute', top: 0, bottom: 0, left: 24, right: 24, alignItems: 'center', justifyContent: 'center', gap: 12, paddingBottom: 36},
  wordmark: {fontSize: 24, lineHeight: 32},
  footer: {position: 'absolute', bottom: 8, left: 24, right: 24, alignItems: 'center', gap: 6},
  status: {flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, minHeight: 24},
  statusText: {fontSize: 13, lineHeight: 20},
  developer: {minHeight: 44, justifyContent: 'center', paddingHorizontal: 12},
  developerText: {fontSize: 12, lineHeight: 18},
});
