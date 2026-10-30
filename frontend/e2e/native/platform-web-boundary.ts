// [Input] Production native component calls at the native-tag/accessibility boundary.
// [Output] RNW rendering with fixture-owned native tags and focus observations.
// [Pos] Provider-free browser harness only; ordinary Web and mobile bundles exclude this module.
export * from 'react-native-web';
import {AccessibilityInfo as WebAccessibilityInfo} from 'react-native-web';
const tags=new WeakMap<object,number>();
let sequence=0;
export function findNodeHandle(node:object|null):number|null {
  if(!node)return null;
  let tag=tags.get(node);if(tag===undefined){tag=++sequence;tags.set(node,tag);}return tag;
}
export const AccessibilityInfo={...WebAccessibilityInfo,setAccessibilityFocus:(tag:number)=>{
  const fixture=(globalThis as any).__badgeFixture;
  fixture?.focuses.push(tag);
}};
