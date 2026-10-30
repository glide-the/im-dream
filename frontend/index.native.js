// [Input] Shared React Native application.
// [Sync] 2026-10-29: restore local appearance and language before mounting the application.
// [Output] Native InkMemory application registration.
// [Pos] iOS/Android entry.
// [Sync] 2026-10-28: initialize canonical i18n explicitly before the native application mounts.
// [Sync] 2026-10-28: register missing UTF-8 and basic Stream constructors before any original AI SDK dependency is evaluated.
import './src/platform/sdkWebApis.native';
import {AppRegistry} from 'react-native';
import './app/_dream/i18n';
import App from './src/App';
import {initTheme} from './app/_dream/utils/theme.native';
import {initInterfaceLanguage} from './src/platform/interfacePreferences.native';
initTheme();
initInterfaceLanguage();
AppRegistry.registerComponent('InkMemory', () => App);
