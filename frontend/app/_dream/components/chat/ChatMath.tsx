// [Input] One parsed formula's original source, display flag and closure state.
// [Output] Lazy KaTeX HTML/MathML or readable original source on syntax/module failure.
// [Pos] Web inline math leaf inside the existing ChatMarkdown tree.
// [Sync] 2026-11-08: restrict generated HTML to KaTeX with trust disabled; inherit message appearance.
import {useEffect, useState} from 'react';
import {loadChatKatex, renderChatFormula} from './chatMathRender';
import 'katex/dist/katex.min.css';
import './ChatMath.css';

export default function ChatMath({source, display, closed}: {source: string; display: boolean; closed: boolean}) {
  const [result, setResult] = useState<{source: string; html: string} | null>(null);
  useEffect(() => {
    let active = true;
    if (closed) void loadChatKatex().then(katex => {
      let html: string;
      try { html = renderChatFormula(katex, source, display, 'htmlAndMathml'); } catch { return; }
      if (active) setResult({source, html});
    }).catch(() => { /* Source remains readable; remount permits another module request. */ });
    return () => { active = false; };
  }, [source, display, closed]);
  const html = result?.source === source && closed ? result.html : undefined;
  return <span className={`chat-math${display ? ' chat-math--display' : ''}`} data-math-source={source}>
    {html ? <span dangerouslySetInnerHTML={{__html: html}}/> : source}
  </span>;
}
