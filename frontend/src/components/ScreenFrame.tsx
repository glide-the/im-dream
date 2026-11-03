// [Sync] 2026-11-02: adopt display-only Kastention naming; existing behavior and technical identities remain.
// [Input] Platform content and the current OS appearance.
// [Output] Shared RN screen frame rendered natively or through React Native Web.
// [Pos] Shared UI source; no browser or WebView dependency.
import { BRAND_NAME } from '../../app/_dream/constants/brand';
import type {ReactNode} from 'react';
import {View, useColorScheme} from 'react-native';
export default function ScreenFrame({children}: {children: ReactNode}) {
  const dark = useColorScheme() === 'dark';
  return <View accessibilityLabel={`${BRAND_NAME} application`} style={{flex: 1, minHeight: '100%', backgroundColor: dark ? '#1f1b16' : '#f6efe5'}}>{children}</View>;
}
