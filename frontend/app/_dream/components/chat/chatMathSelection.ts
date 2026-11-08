// [Input] A selection wholly contained in the current Markdown/math document.
// [Output] Selection HTML/plain text with each touched formula replaced by complete original source.
// [Pos] Shared browser copy projection, serialized into the restricted native math document.
// [Sync] 2026-11-08: avoid duplicate MathML/visual text and preserve existing message-level copying.
export function projectMathSelection(container: Element): {html: string; text: string} | null {
  const selection = container.ownerDocument.getSelection();
  if (!selection || selection.isCollapsed || !selection.rangeCount) return null;
  const range = selection.getRangeAt(0).cloneRange();
  if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) return null;
  const closest = (node: Node) => (node.nodeType === 1 ? node as Element : node.parentElement)?.closest('[data-math-source]');
  const start = closest(range.startContainer), end = closest(range.endContainer);
  if (start && container.contains(start)) range.setStartBefore(start);
  if (end && container.contains(end)) range.setEndAfter(end);
  const fragment = range.cloneContents();
  const formulas = fragment.querySelectorAll('[data-math-source]');
  if (!formulas.length) return null;
  for (const formula of formulas) formula.replaceWith(container.ownerDocument.createTextNode(formula.getAttribute('data-math-source') ?? ''));
  const wrapper = container.ownerDocument.createElement('div');
  wrapper.append(fragment);
  function text(node: Node): string {
    if (node.nodeType === 3) return node.textContent ?? '';
    const element = node as Element;
    if (element.tagName === 'BR') return '\n';
    const value = Array.from(node.childNodes).map(text).join('');
    if (['P','DIV','LI','TR','PRE','BLOCKQUOTE'].includes(element.tagName)) return value + '\n';
    if (['TD','TH'].includes(element.tagName)) return value + '\t';
    return value;
  }
  return {html: wrapper.innerHTML, text: Array.from(wrapper.childNodes).map(text).join('').replace(/\n$/, '')};
}
