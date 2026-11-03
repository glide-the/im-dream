// [Input] Shared vector paths, current ink color, visible preparation state and system motion preference.
// [Output] A decorative breathing illustration while preparation is visible and the app is active.
// [Pos] Native preparation-page artwork; SessionGate owns readiness and navigation.
// [Sync] 2026-11-02: draw transparent vector linework and blue/white fills on the current app background.
// [Sync] 2026-11-03: explicitly keep the native vector viewport and animation container clear and borderless.
import {useEffect, useRef, useState} from 'react';
import {AccessibilityInfo, Animated, AppState, Easing} from 'react-native';
import Svg, {Path} from 'react-native-svg';
import artwork from '../assets/startup-artwork.json';
import useInkColors from './useInkColors.native';
import {STARTUP_BREATH_HALF_CYCLE_MS} from './startupPresentation';

export default function StartupArtwork({visible, size = 176}: {visible: boolean; size?: number}) {
  const colors = useInkColors();
  const progress = useRef(new Animated.Value(0)).current;
  const [active, setActive] = useState(AppState.currentState === 'active');
  const [reduceMotion, setReduceMotion] = useState(true);

  useEffect(() => {
    let mounted = true;
    let preferenceChanged = false;
    const motion = AccessibilityInfo.addEventListener('reduceMotionChanged', value => {
      preferenceChanged = true;
      setReduceMotion(value);
    });
    void AccessibilityInfo.isReduceMotionEnabled().then(value => {
      if (mounted && !preferenceChanged) setReduceMotion(value);
    }).catch(() => undefined);
    const state = AppState.addEventListener('change', next => setActive(next === 'active'));
    return () => { mounted = false; motion.remove(); state.remove(); };
  }, []);

  useEffect(() => {
    progress.setValue(0);
    if (!visible || !active || reduceMotion) return;
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(progress, {toValue: 1, duration: STARTUP_BREATH_HALF_CYCLE_MS, easing: Easing.inOut(Easing.sin), useNativeDriver: true, isInteraction: false}),
      Animated.timing(progress, {toValue: 0, duration: STARTUP_BREATH_HALF_CYCLE_MS, easing: Easing.inOut(Easing.sin), useNativeDriver: true, isInteraction: false}),
    ]));
    animation.start();
    return () => { animation.stop(); progress.setValue(0); };
  }, [active, progress, reduceMotion, visible]);

  return <Animated.View
    pointerEvents="none"
    accessible={false}
    accessibilityElementsHidden
    importantForAccessibility="no-hide-descendants"
    testID="startup-artwork"
    style={{width: size, height: size, backgroundColor: 'transparent', borderWidth: 0, transform: [{scale: progress.interpolate({inputRange: [0, 1], outputRange: [1, 1.035]})}]}}
  >
    <Svg width="100%" height="100%" viewBox={artwork.viewBox} color={colors['color-text-primary']} fill="none" strokeLinecap="round" strokeLinejoin="round" style={{backgroundColor:'transparent',borderWidth:0}} accessible={false}>
      {artwork.paths.map((shape, index) => <Path key={index} {...shape}/>)}
    </Svg>
  </Animated.View>;
}

