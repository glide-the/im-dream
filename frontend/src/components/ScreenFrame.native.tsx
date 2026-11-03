// [Sync] 2026-11-02: adopt display-only Kastention naming; existing behavior and technical identities remain.
// [Input] Native content and the persisted explicit/system appearance.
// [Output] Original theme background behind the native application and side-chat sheet.
// [Pos] Native variant; Web keeps ScreenFrame.tsx and its existing stylesheet.
import { BRAND_NAME } from '../../app/_dream/constants/brand';
import type {ReactNode} from 'react';
import {View} from 'react-native';
import useInkColors from './useInkColors.native';
export default function ScreenFrame({children}:{children:ReactNode}) {
  const colors=useInkColors();
  return <View accessibilityLabel={`${BRAND_NAME} application`} style={{flex:1,minHeight:'100%',backgroundColor:colors['color-bg-app']}}>{children}</View>;
}
