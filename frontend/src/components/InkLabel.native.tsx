// [Input] Existing product label and RN Text props.
// [Output] Native text retaining the original Latin/Chinese font selection.
// [Pos] Typography-only adapter for migrated labels.
import {Text, type TextProps} from 'react-native';
import {inkFontRuns} from './fontRuns';
export default function InkLabel({children, style, ...props}: Omit<TextProps,'children'> & {children:string}) {
  return <Text {...props} style={[{fontFamily:'Excalifont'},style]}>{inkFontRuns(children).map((run,index) =>
    <Text key={index} style={{fontFamily:run.family}}>{run.text}</Text>
  )}</Text>;
}
