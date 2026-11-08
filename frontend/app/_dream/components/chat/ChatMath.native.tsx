// [Input] Production Markdown inline nodes, caller-owned text appearance and existing link callbacks.
// [Output] A restricted MathML text document with matched height updates and readable source fallback.
// [Pos] Native formula-containing text only; surrounding Chat, copy and vertical scrolling remain native.
// [Sync] 2026-11-08: reuse KaTeX and the Web selection projection without network, route or file access.
import {useEffect, useMemo, useRef, useState} from 'react';
import {StyleSheet, Text, View, type TextStyle, type ViewProps, type ViewStyle} from 'react-native';
import {WebView} from 'react-native-webview';
import useInkColors from '../../../../src/components/useInkColors.native';
import {escapeMathHtml, loadChatKatex, mathText, nativeMathMarkup, type ChatKatex, type MathTextNode} from './chatMathRender';
import {projectMathSelection} from './chatMathSelection';

let documentSequence = 0;
interface Props {
  nodes: readonly MathTextNode[];
  textStyle: TextStyle;
  onOpenLink?: (href: string) => void;
  onLayout?: ViewProps['onLayout'];
}
export default function ChatMath({nodes, textStyle, onOpenLink, onLayout}: Props) {
  const colors = useInkColors();
  const [katex, setKatex] = useState<ChatKatex>();
  const [height, setHeight] = useState(0);
  const [failedId, setFailedId] = useState('');
  const active = useRef(true);
  useEffect(() => {
    let active = true;
    void loadChatKatex().then(module => { if (active) setKatex(module); }).catch(() => { /* Keep original text. */ });
    return () => { active = false; };
  }, []);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const markup = useMemo(() => nativeMathMarkup(nodes, katex), [nodes, katex]);
  const fontSize = textStyle.fontSize ?? 15.2, lineHeight = textStyle.lineHeight ?? 26.6;
  const color = String(textStyle.color ?? colors['color-text-body']);
  const background = String(textStyle.backgroundColor ?? colors['color-bg-app']);
  const fontWeight = textStyle.fontWeight ?? 'normal', fontStyle = textStyle.fontStyle ?? 'normal', textAlign = textStyle.textAlign ?? 'start';
  const document = useMemo(() => {
    const id = `ink-math-${++documentSequence}`;
    const css = `html,body{margin:0;padding:0;background:${escapeMathHtml(background)}}body{font-family:Excalifont,system-ui,sans-serif;font-size:${fontSize}px;line-height:${lineHeight}px;color:${escapeMathHtml(color)};font-weight:${fontWeight};font-style:${fontStyle};text-align:${textAlign};overflow-wrap:anywhere;white-space:pre-wrap}#content{display:flow-root;min-width:0}a{color:${escapeMathHtml(colors['color-action-link'])};text-decoration:underline}strong{color:${escapeMathHtml(colors['color-text-primary'])}}code{font-family:Menlo,monospace;font-size:.92em;color:${escapeMathHtml(colors['color-text-primary'])};background:${escapeMathHtml(colors['color-code-inline-bg'])}}.chat-math{display:inline-block;max-width:100%;overflow-x:auto;vertical-align:middle;padding-block:.2em;line-height:normal;white-space:pre-wrap}.chat-math--display{display:block;margin-block:.9em;text-align:center}.chat-math--display math{width:max-content;min-width:100%}math{font-size:1.21em}`;
    const script = `const root=document.getElementById('content');const report=()=>window.ReactNativeWebView?.postMessage(JSON.stringify({type:'height',id:'${id}',height:root.getBoundingClientRect().height}));new ResizeObserver(report).observe(root);report();document.addEventListener('copy',event=>{const value=(${projectMathSelection.toString()})(root);if(value&&event.clipboardData){event.clipboardData.setData('text/plain',value.text);event.clipboardData.setData('text/html',value.html);event.preventDefault();}});`;
    const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${id}'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><style>${css}</style></head><body><div id="content">${markup.html}</div><script nonce="${id}">${script}</script></body></html>`;
    return {id, source: {html}};
  }, [markup.html, fontSize, lineHeight, color, background, colors, fontWeight, fontStyle, textAlign]);
  const current = useRef({id: document.id, links: markup.links, onOpenLink});
  current.current = {id: document.id, links: markup.links, onOpenLink};
  if (!katex || failedId === document.id) return <Text selectable onLayout={onLayout} style={textStyle}>{mathText(nodes)}</Text>;
  return <View testID="native-chat-math" onLayout={onLayout} style={[textStyle as ViewStyle, {minWidth: 0, maxWidth: '100%', height: Math.max(lineHeight, height)}]}>
    <WebView source={document.source} originWhitelist={['*']} scrollEnabled={false}
      automaticallyAdjustContentInsets={false} contentInsetAdjustmentBehavior="never"
      setSupportMultipleWindows={false} javaScriptCanOpenWindowsAutomatically={false} allowFileAccess={false}
      onShouldStartLoadWithRequest={request => {
        if (!active.current || document.id !== current.current.id) return false;
        const match = /^ink-math-link:([0-9]+)$/.exec(request.url);
        if (match) { const link = current.current.links[Number(match[1])]; if (link !== undefined) current.current.onOpenLink?.(link); return false; }
        return request.url === 'about:blank' || request.url === 'about:srcdoc';
      }}
      onMessage={event => {
        if (!active.current || document.id !== current.current.id) return;
        if (!['about:blank','about:srcdoc'].includes(event.nativeEvent.url)) return;
        try {
          const data: unknown = JSON.parse(event.nativeEvent.data);
          if (!data || typeof data !== 'object') return;
          const value = data as Record<string, unknown>;
          if (value.type === 'height' && value.id === document.id && typeof value.height === 'number' && Number.isFinite(value.height) && value.height > 0) setHeight(Math.ceil(value.height));
        } catch { /* Ignore malformed document messages. */ }
      }}
      onError={() => setFailedId(document.id)} onContentProcessDidTerminate={() => setFailedId(document.id)}
      style={[StyleSheet.absoluteFill, {backgroundColor: background}]}/>
  </View>;
}
