// [Input] react-markdown's existing micromark and mdast extension points.
// [Output] Explicit paired math tokens with lossless source; code and escaped markers stay in Markdown.
// [Pos] Shared Web/Native message syntax, matching the reference HT/UT delimiter set.
// [Sync] 2026-11-08: add inline parentheses and display brackets/double dollars without single-dollar math.
import type {Plugin} from 'unified';
import type {Construct, Extension, State, Token, Tokenizer} from 'micromark-util-types';
import type {Extension as MdastExtension} from 'mdast-util-from-markdown';

declare module 'micromark-util-types' {
  interface TokenTypeMap { chatMath: 'chatMath'; chatMathMarker: 'chatMathMarker'; chatMathData: 'chatMathData' }
  interface Token { mathClosed?: boolean; mathDisplay?: boolean }
}

const tokenize: Tokenizer = function(effects, ok, nok) {
  let first: number, end: number, display = false;
  let token: Token;
  return start;
  function start(code: Parameters<State>[0]) {
    if (code !== 92 && code !== 36) return nok(code);
    token = effects.enter('chatMath');
    effects.enter('chatMathMarker');
    first = code;
    effects.consume(code);
    return opening;
  }
  function opening(code: Parameters<State>[0]) {
    if (first === 36 ? code !== 36 : code !== 40 && code !== 91) return nok(code);
    display = first === 36 || code === 91;
    end = first === 36 ? 36 : code === 40 ? 41 : 93;
    token.mathDisplay = display;
    effects.consume(code);
    effects.exit('chatMathMarker');
    return content;
  }
  function finish(code: Parameters<State>[0], closed: boolean) {
    token.mathClosed = closed;
    effects.exit('chatMath');
    return ok(code);
  }
  function content(code: Parameters<State>[0]): ReturnType<State> {
    if (code === null || (!display && (code === -5 || code === -4 || code === -3))) return finish(code, false);
    if (code === -5 || code === -4 || code === -3) {
      effects.enter('lineEnding');
      effects.consume(code);
      effects.exit('lineEnding');
      return content;
    }
    if (code === first) {
      effects.enter('chatMathMarker');
      effects.consume(code);
      return closing;
    }
    effects.enter('chatMathData');
    return data(code);
  }
  function data(code: Parameters<State>[0]): ReturnType<State> {
    if (code === null || code === first || code === -5 || code === -4 || code === -3) {
      effects.exit('chatMathData');
      return content(code);
    }
    effects.consume(code);
    return data;
  }
  function closing(code: Parameters<State>[0]): ReturnType<State> {
    if (code === end) {
      effects.consume(code);
      effects.exit('chatMathMarker');
      return closed;
    }
    // A doubled backslash is a TeX command, so its second slash cannot close math.
    if (first === 92 && code === 92) {
      effects.consume(code);
      effects.exit('chatMathMarker');
      return content;
    }
    effects.exit('chatMathMarker');
    return content(code);
  }
  function closed(code: Parameters<State>[0]) { return finish(code, true); }
};
const construct: Construct = {name: 'chatMath', tokenize};
const syntax: Extension = {text: {36: construct, 92: construct}};
const mdast: MdastExtension = {
  enter: {
    chatMath(token) {
      const source = this.sliceSerialize(token);
      this.enter({
        type: 'inlineCode', value: source,
        data: {hName: 'span', hProperties: {
          dataMathSource: source,
          dataMathDisplay: token.mathDisplay ? 'true' : 'false',
          dataMathClosed: token.mathClosed ? 'true' : 'false',
        }},
      }, token);
    },
  },
  exit: {chatMath(token) { this.exit(token); }},
};

const remarkChatMath: Plugin = function() {
  const data = this.data() as {micromarkExtensions?: Extension[]; fromMarkdownExtensions?: MdastExtension[]};
  (data.micromarkExtensions ??= []).push(syntax);
  (data.fromMarkdownExtensions ??= []).push(mdast);
};
export default remarkChatMath;
