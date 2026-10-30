// [Input] Production native SVG leaves and the installed react-native-svg Web renderer.
// [Output] Original SVG geometry with native accessible=false represented by aria-hidden.
// [Pos] Provider-free browser boundary; no application icon or third-party source changes.
import {forwardRef,type ComponentProps,type ComponentRef} from 'react';
import WebSvg from 'react-native-svg/lib/module/elements.web.js';
export * from 'react-native-svg/lib/module/elements.web.js';
type Props=ComponentProps<typeof WebSvg>&{accessible?:boolean};
export const Svg=forwardRef<ComponentRef<typeof WebSvg>,Props>(({accessible,...props},ref)=><WebSvg {...props} aria-hidden={accessible===false?true:props['aria-hidden']} ref={ref}/>);
export default Svg;
