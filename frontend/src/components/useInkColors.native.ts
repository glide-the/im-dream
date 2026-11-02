// [Input] Native theme preference and application/system appearance subscriptions.
// [Output] Original explicit-light, explicit-dark or system-dark token palette.
// [Pos] Native presentation hook; palette values remain owned by inkColors.ts.
import {useSyncExternalStore} from 'react';
import {useColorScheme} from 'react-native';
import {getThemeMode,onThemeChange,type ThemeMode} from '../../app/_dream/utils/theme.native';
import {inkColors} from './inkColors';
const subscribe=(changed:()=>void)=>onThemeChange(changed);
export function useNativeThemeMode():ThemeMode {return useSyncExternalStore(subscribe,getThemeMode,getThemeMode);}
export default function useInkColors(requested?:ThemeMode) {
  const mode=useNativeThemeMode(),systemDark=useColorScheme()==='dark';
  return inkColors(requested??mode,systemDark);
}
