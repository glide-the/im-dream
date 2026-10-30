// [Sync] 2026-10-28: retain original download/maximize SVG geometry for native Workspace references.
// [Sync] 2026-10-28: retain original copy/check, history disclosure and scroll-to-bottom SVG geometry.
// [Input] Geometry copied exactly from the corresponding Icons.tsx exports.
// [Output] Native SVG leaf icons; the existing DOM SVG file remains unchanged.
// [Pos] Platform-specific renderer for the original Chat icon family.
// [Sync] 2026-10-28: retain original trash geometry for the native queue-card actions.
// [Sync] 2026-10-28: retain original IconFile geometry for native attachment cards.
// [Sync] 2026-10-28: retain original message-circle geometry for native history search results.
import type {ReactNode} from 'react';
import Svg, {Circle, Line, Path, Polyline, Rect} from 'react-native-svg';
import type {SvgProps} from 'react-native-svg';
type IconProps = Pick<SvgProps, 'width' | 'height' | 'color' | 'style'>;
function createIcon(paths: ReactNode) {
  return function Icon({width = 16, height = 16, color, style}: IconProps) {
    return <Svg width={width} height={height} color={color} style={style} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" accessible={false}>{paths}</Svg>;
  };
}
export const IconSearch = createIcon(<><Circle cx="11" cy="11" r="7" /><Path d="M20 20l-3.5-3.5" /></>);
export const IconBell = createIcon(<><Path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><Path d="M10 21h4" /></>);
export const IconImage = createIcon(<><Rect x="3" y="4" width="18" height="16" rx="3" /><Path d="M7 14l3-3 4 4 3-3 3 3" /><Circle cx="9" cy="9" r="1.5" /></>);
export const IconPlus = createIcon(<><Path d="M12 5v14" /><Path d="M5 12h14" /></>);
export const IconEdit = createIcon(<><Path d="M12 20h9" /><Path d="M16.5 3.5l4 4L7 21H3v-4L16.5 3.5z" /></>);
export const IconMoreHorizontal = createIcon(<><Circle cx="5" cy="12" r="1" /><Circle cx="12" cy="12" r="1" /><Circle cx="19" cy="12" r="1" /></>);
export const IconX = createIcon(<><Path d="M18 6L6 18" /><Path d="M6 6l12 12" /></>);
export const IconFolder = createIcon(<Path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />);
export const IconFile = createIcon(<><Path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><Polyline points="14 2 14 8 20 8" /></>);
export const IconClock = createIcon(<><Circle cx="12" cy="12" r="10" /><Polyline points="12 6 12 12 16 14" /></>);
export const IconMessageCircle = createIcon(<><Path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.7 8.7 0 0 1-7.8 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.5a8.4 8.4 0 0 1-.9-3.8 8.7 8.7 0 0 1 4.7-7.8 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5z" /></>);
export const IconShare = createIcon(<><Path d="M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7" /><Path d="M16 6l-4-4-4 4" /><Path d="M12 2v14" /></>);
export const IconArrowUp = createIcon(<><Line x1="12" y1="19" x2="12" y2="5" /><Polyline points="5 12 12 5 19 12" /></>);
export function IconStop({width=16,height=16,color,style}:IconProps) {
  return <Svg width={width} height={height} color={color} style={style} viewBox="0 0 24 24" fill="currentColor" accessible={false}><Rect x="6" y="6" width="12" height="12" rx="2" /></Svg>;
}

export const IconChevronRight = createIcon(<Path d="M9 6l6 6-6 6" />);
export const IconCheck = createIcon(<Polyline points="20 6 9 17 4 12" />);
export const IconCopy = createIcon(<><Rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><Path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></>);
export const IconArrowDown = createIcon(<><Line x1="12" y1="5" x2="12" y2="19" /><Polyline points="5 12 12 19 19 12" /></>);
export const IconTrash = createIcon(<><Path d="M3 6h18" /><Path d="M8 6V4h8v2" /><Path d="M19 6l-1 14H6L5 6" /><Path d="M10 11v6" /><Path d="M14 11v6" /></>);

export const IconDownload = createIcon(<><Path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><Polyline points="7 10 12 15 17 10" /><Line x1="12" y1="15" x2="12" y2="3" /></>);
export const IconMaximize = createIcon(<><Polyline points="15 3 21 3 21 9" /><Polyline points="9 21 3 21 3 15" /><Line x1="21" y1="3" x2="14" y2="10" /><Line x1="3" y1="21" x2="10" y2="14" /></>);
