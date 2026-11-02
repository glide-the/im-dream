// [Input] Platform content and the current OS appearance.
// [Output] Shared RN screen frame rendered natively or through React Native Web.
// [Pos] Shared UI source; no browser or WebView dependency.
import type {ReactNode} from 'react';
import {View, useColorScheme} from 'react-native';
export default function ScreenFrame({children}: {children: ReactNode}) {
  const dark = useColorScheme() === 'dark';
  return <View accessibilityLabel="Ink Memory application" style={{flex: 1, minHeight: '100%', backgroundColor: dark ? '#1f1b16' : '#f6efe5'}}>{children}</View>;
}
