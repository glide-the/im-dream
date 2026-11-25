// [Input] TextCell content and ordered references already identified in its original string.
// [Output] Logical lines with source offsets, including empty and trailing lines.
// [Pos] Writing display model. Persisted text and article URLs retain their original spelling.
import type {NotionArticleLink} from './notionArticleLinks';

export function articleLines(content: string, links: NotionArticleLink[]) {
  let start = 0;
  let linkIndex = 0;
  return content.split('\n').map(text => {
    const end = start + text.length;
    const firstLink = linkIndex;
    while (linkIndex < links.length && links[linkIndex].start < end) linkIndex++;
    const line = {start, end, text, links: links.slice(firstLink, linkIndex)};
    start = end + 1;
    return line;
  });
}
