// [Input] Canonical navigation intent and native WebKit state events.
// [Output] A persistent instance of the existing iOS business WebView.
// [Pos] RN native-view boundary; WebKit retains authentication and business HTTP.
import {requireNativeComponent, type NativeSyntheticEvent, type ViewProps} from 'react-native';

export type WebState = {
  path?: string;
  authenticated?: boolean;
  loading?: boolean;
  failed?: boolean;
  background?: string;
  mode?: 'light' | 'dark' | 'system';
  authFailure?: boolean;
};
type Props = ViewProps & {
  navigationRequest: {path: string; revision: number};
  logoutRequest: number;
  onHostState: (event: NativeSyntheticEvent<WebState>) => void;
};
export default requireNativeComponent<Props>('InkBusinessSurface');
