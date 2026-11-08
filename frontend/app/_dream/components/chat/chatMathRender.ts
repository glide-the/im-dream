// [Input] Explicit math source tokens and inline Markdown nodes from the production parser.
// [Output] Shared lazy KaTeX, safe inline serialization and source-preserving text fallbacks.
// [Pos] DOM-independent math presentation helpers used by Web and Native adapters.
// [Sync] 2026-11-08: pin KaTeX to the existing lock entry and keep native HTML closed to arbitrary tags.
export type ChatKatex = typeof import('katex')['default'];

let pending: Promise<ChatKatex> | undefined;
export function loadChatKatex(): Promise<ChatKatex> {
  pending ??= import('katex').then(module => module.default).catch(error => {
    pending = undefined;
    throw error;
  });
  return pending;
}
export interface MathTextNode {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: readonly MathTextNode[];
}
export function mathSource(node: MathTextNode): string | undefined {
  const value = node.properties?.dataMathSource;
  return typeof value === 'string' ? value : undefined;
}
export function hasMath(nodes: readonly MathTextNode[]): boolean {
  return nodes.some(node => mathSource(node) !== undefined || (node.children && hasMath(node.children)));
}
export function mathText(nodes: readonly MathTextNode[]): string {
  return nodes.map(node => mathSource(node) ?? node.value ?? (node.tagName === 'br' ? '\n' : mathText(node.children ?? []))).join('');
}
export function escapeMathHtml(value: string): string {
  return value.replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]!));
}
export function renderChatFormula(katex: ChatKatex, source: string, display: boolean, output: 'htmlAndMathml' | 'mathml'): string {
  return katex.renderToString(source.slice(2, -2).trim(), {
    displayMode: display, output, strict: 'ignore', trust: false, throwOnError: true,
  });
}

// Only text-level Markdown tags enter the native document; links use numeric local handles.
export function nativeMathMarkup(nodes: readonly MathTextNode[], katex?: ChatKatex): {html: string; links: string[]} {
  const links: string[] = [];
  function render(node: MathTextNode): string {
    const source = mathSource(node);
    if (source !== undefined) {
      const display = node.properties?.dataMathDisplay === 'true';
      let content = escapeMathHtml(source);
      if (katex && node.properties?.dataMathClosed === 'true') {
        try { content = renderChatFormula(katex, source, display, 'mathml'); } catch { /* Keep original delimiters. */ }
      }
      return `<span class="chat-math${display ? ' chat-math--display' : ''}" data-math-source="${escapeMathHtml(source)}">${content}</span>`;
    }
    if (node.type === 'text') return escapeMathHtml(node.value ?? '');
    const children = (node.children ?? []).map(render).join('');
    if (node.tagName === 'br') return '<br>';
    if (node.tagName === 'input' && node.properties?.type === 'checkbox') return node.properties.checked ? '☑ ' : '☐ ';
    if (node.tagName === 'a' && typeof node.properties?.href === 'string') {
      links.push(node.properties.href);
      return `<a href="ink-math-link:${links.length - 1}">${children}</a>`;
    }
    return ['strong','em','del','s','code','sup','sub'].includes(node.tagName ?? '')
      ? `<${node.tagName}>${children}</${node.tagName}>` : children;
  }
  return {html: nodes.map(render).join(''), links};
}
