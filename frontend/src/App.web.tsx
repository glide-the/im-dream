// [Input] Existing complete Web business application and shared RN layout.
// [Output] Next Web through react-native-web with current business pages preserved during migration.
// [Pos] Explicit Web variant; shared native business pages replace each Web subtree after parity checks.
import DreamRoot from '../app/_dream/DreamRoot';
import ScreenFrame from './components/ScreenFrame';
export default function App() {
  return <ScreenFrame><DreamRoot frontendVersion="next-phase1" /></ScreenFrame>;
}
