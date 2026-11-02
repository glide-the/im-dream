// [Input] Bundled React Native application.
// [Output] InkMemory root registration for the existing iOS host.
// [Pos] Native JavaScript entry, independent of Metro at runtime.
import {AppRegistry} from 'react-native';
import App from './src/App';
AppRegistry.registerComponent('InkMemory', () => App);
