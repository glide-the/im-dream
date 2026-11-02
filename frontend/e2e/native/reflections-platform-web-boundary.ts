// [Input] Existing isolated Settings/UUID and native accessibility facades.
// [Output] Explicit iOS platform substitutes for the production Reflections controls.
// [Pos] Technical harness only; actual Foundation, UIKit, URLSession and UserDefaults need target validation.
export * from './settings-platform-web-boundary';
export {AccessibilityInfo,findNodeHandle} from './platform-web-boundary';
import {Keyboard as WebKeyboard} from 'react-native-web';
export const Keyboard={...WebKeyboard,metrics:()=>undefined};
