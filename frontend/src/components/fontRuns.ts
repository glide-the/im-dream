// [Input] Label text and the original App.css Chinese @font-face unicode range.
// [Output] Font runs retaining Excalifont Latin and Xiaolai Chinese presentation.
// [Pos] Native typography adapter; fonts come from the existing public assets.
const chinese = /[\u4E00-\u9FFF\u3400-\u4DBF\u{20000}-\u{2A6DF}\uF900-\uFAFF\u3000-\u303F]/u;
export function inkFontRuns(text: string): Array<{text:string; family:'Excalifont' | 'Xiaolai'}> {
  const runs: Array<{text:string; family:'Excalifont' | 'Xiaolai'}> = [];
  for (const character of text) {
    const family = chinese.test(character) ? 'Xiaolai' : 'Excalifont';
    const previous = runs.at(-1);
    if (previous?.family === family) previous.text += character;
    else runs.push({text:character,family});
  }
  return runs;
}
