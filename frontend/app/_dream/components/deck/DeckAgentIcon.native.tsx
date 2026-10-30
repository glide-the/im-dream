// [Input] Original configured icon key, size and resolved project theme color.
// [Output] The same fixed Font Awesome path geometry through react-native-svg.
// [Pos] Native icon leaf; upstream attribution stays with the generated shared asset.
// [Sync] 2026-10-29: retain original FaPlay geometry as a separate preview action glyph.
import Svg,{Path} from 'react-native-svg';
import data from '../../../../shared/deck-icons.json';
import type {InkColors} from '../../../../src/components/inkColors';
export function deckAgentColor(name:string,colors:InkColors):string {
  const token=data.colors[name as keyof typeof data.colors];
  return colors[token as keyof InkColors] ?? colors['color-action-link'];
}
export function DeckPlayIcon({size=13,color}:{size?:number;color:string}) {
  const icon=data.actions.play;
  return <Svg width={size} height={size} viewBox={icon.viewBox} fill={color} accessible={false}>
    {icon.paths.map((path,index)=><Path key={index} {...path}/>)}
  </Svg>;
}
export default function DeckAgentIcon({name,size=14,color}:{name:string;size?:number;color:string}) {
  const icon=data.icons[name as keyof typeof data.icons] ?? data.icons.brain;
  return <Svg width={size} height={size} viewBox={icon.viewBox} fill={color} stroke={color} strokeWidth={0} accessible={false}>
    {icon.paths.map((path,index)=><Path key={index} {...path} />)}
  </Svg>;
}
