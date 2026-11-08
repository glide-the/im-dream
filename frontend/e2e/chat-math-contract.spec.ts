// [Input] Production react-markdown syntax extension, KaTeX renderer and restricted native serializer.
// [Output] Deterministic delimiter, literal-code, fallback and content-boundary regression receipts.
// [Pos] Provider-free math contract tests; no browser, account, database or model writes.
// [Sync] 2026-11-08: cover explicit delimiters, partial streams and executable-content rejection.
import {test, expect} from '@playwright/test';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import katex from 'katex';
import remarkChatMath from '../app/_dream/components/chat/remarkChatMath';
import {nativeMathMarkup, renderChatFormula, type MathTextNode} from '../app/_dream/components/chat/chatMathRender';

function parse(text: string) {
  return renderToStaticMarkup(createElement(Markdown, {remarkPlugins:[remarkGfm, remarkChatMath], children:text}));
}
test('the three reference delimiter forms retain full source and display semantics', () => {
  const html = parse(String.raw`First \(x_1^2\), next \(y\).

\[\frac{a}{b}\]

$$\sum_{i=1}^{n} i$$`);
  expect(html.match(/data-math-source=/g)).toHaveLength(4);
  expect(html.match(/data-math-display="true"/g)).toHaveLength(2);
  expect(html.match(/data-math-closed="true"/g)).toHaveLength(4);
  expect(html).toContain('\\(x_1^2\\)');
});
test('money, single dollars, escaped delimiters, code fences and destinations stay literal', () => {
  const text = String.raw`Price $5 and $10. $x$.

Escaped \\(x\\) and \\[y\\].

\`\(inline\)\`

\`\`\`tex
\[code\]
$$code$$
\`\`\`

[Docs](https://example.test/price$5)` .replace(/\\`/g, '`');
  const html = parse(text);
  expect(html).not.toContain('data-math-source');
  expect(html).toContain('$5 and $10');
  expect(html).toContain('<code>\\(inline\\)</code>');
  expect(html).toContain('href="https://example.test/price$5"');
});
for (const source of [String.raw`\(\frac{1}{`, String.raw`\[\frac{1}{`, '$$x^']) {
  test(`unclosed source remains readable: ${source}`, () => {
    const html = parse('Before ' + source);
    expect(html).toContain('data-math-closed="false"');
    expect(html).toContain(source);
    expect(html).toContain('Before ');
  });
}
test('a completed later snapshot renders independently of a previous incomplete one', () => {
  expect(parse(String.raw`\(a_`)).toContain('data-math-closed="false"');
  expect(parse(String.raw`\(a_1\)`)).toContain('data-math-closed="true"');
  expect(parse(String.raw`\(a\)
\(b\)`)).toContain('data-math-closed="true"');
  expect(parse(String.raw`\(a
b\)`)).toContain('data-math-closed="false"');
});
test('multiline display math and TeX newlines survive the Markdown parser', () => {
  const source = String.raw`\[
\begin{aligned}
x &= 1 \\
y &= 2
\end{aligned}
\]`;
  expect(parse(source)).toContain('data-math-closed="true"');
  expect(renderChatFormula(katex, source, true, 'htmlAndMathml')).toContain('katex-display');
});
test('every stream prefix stays parseable inside nested Markdown and across display lines', () => {
  const samples = [
    String.raw`> \[
> \frac{a}{b}
> \]`,
    String.raw`- First **\(x_1\)**
  - Next \(y_2\)`,
    '| A | B |\n|---|---|\n| \\(x\\) | \\(y\\) |',
    String.raw`$$
\begin{aligned}
x &= 1 \\
y &= 2
\end{aligned}
$$`,
  ];
  for (const sample of samples) {
    for (let end=1; end<=sample.length; end++) expect(() => parse(sample.slice(0,end))).not.toThrow();
    expect(parse(sample)).toContain('data-math-closed="true"');
  }
});
test('math coexists with GFM, links, Mermaid and raw HTML safety', () => {
  const html = parse('| Name | Value |\n| --- | --- |\n| result | \\(x\\) |\n\n```mermaid\nflowchart LR\n A --> B\n```\n\n<script>window.attack=true</script>\n\n[Bad](javascript:alert%281%29)');
  expect(html).toContain('<table>');
  expect(html).toContain('data-math-source');
  expect(html).toContain('class="language-mermaid"');
  expect(html).not.toContain('<script>');
  expect(html).not.toContain('href="javascript:');
});
test('native math HTML escapes all source and uses numeric link handles', () => {
  const nodes: MathTextNode[] = [
    {type:'text',value:'<script>bad</script>'},
    {type:'element',tagName:'a',properties:{href:'javascript:alert(1)'},children:[{type:'text',value:'Read'}]},
    {type:'element',tagName:'span',properties:{dataMathSource:String.raw`\(\unknown{x}\)`,dataMathDisplay:'false',dataMathClosed:'true'}},
  ];
  const markup = nativeMathMarkup(nodes, katex);
  expect(markup.html).not.toContain('<script>');
  expect(markup.html).not.toContain('javascript:');
  expect(markup.html).toContain('ink-math-link:0');
  expect(markup.links).toEqual(['javascript:alert(1)']);
  expect(markup.html).toContain('\\unknown{x}');
});
test('KaTeX trust remains disabled and invalid formula throws to the source fallback', () => {
  expect(() => renderChatFormula(katex, String.raw`\(\unknown{x}\)`, false, 'htmlAndMathml')).toThrow();
  const html = renderChatFormula(katex, String.raw`\(\href{javascript:alert(1)}{x}\)`, false, 'htmlAndMathml');
  expect(html).not.toContain('<a ');
  expect(html).not.toContain('href="javascript:');
});
