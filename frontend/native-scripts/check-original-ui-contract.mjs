// [Input] Canonical Web icon geometry/theme CSS and their native projections.
// [Output] Scoped fidelity receipt; this check makes no whole-page or business acceptance claim.
// [Pos] Source-level migration gate for original visual assets and token values.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {inkColors} from '../src/components/inkColors.ts';
// Validates only the fixed Deck assets; no native/web renderer is loaded into the other platform.
await import('./prepare-deck-icons.mjs');
const require = createRequire(import.meta.url);
const ts = require('typescript');
const root = new URL('../', import.meta.url);
const load = async name => readFile(new URL(name, root), 'utf8');
function icons(source) {
  const parsed = ts.createSourceFile('icons.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  const result = new Map();
  for (const statement of parsed.statements) {
    if (ts.isFunctionDeclaration(statement) && statement.name?.text.startsWith('Icon')) {
      const nodes = [];
      const visit = node => {
        if (ts.isJsxSelfClosingElement(node) || ts.isJsxOpeningElement(node)) {
          const name = node.tagName.getText(parsed).toLowerCase();
          const attributes = Object.fromEntries(node.attributes.properties.filter(ts.isJsxAttribute)
            .filter(attribute => name !== 'svg' || ['viewBox','fill','stroke'].includes(attribute.name.getText(parsed)))
            .map(attribute => [attribute.name.getText(parsed),attribute.initializer?.text]));
          nodes.push([name,attributes]);
        }
        ts.forEachChild(node,visit);
      };
      visit(statement.body);
      if (nodes.length) result.set(statement.name.text,nodes);
      continue;
    }
    if (!ts.isVariableStatement(statement)) continue;
    for (const declaration of statement.declarationList.declarations) {
      if (!ts.isIdentifier(declaration.name) || !declaration.name.text.startsWith('Icon') || !declaration.initializer || !ts.isCallExpression(declaration.initializer)) continue;
      const nodes = [];
      const visit = node => {
        if (ts.isJsxSelfClosingElement(node) || ts.isJsxOpeningElement(node)) {
          const attributes = Object.fromEntries(node.attributes.properties.filter(ts.isJsxAttribute).map(attribute => [attribute.name.getText(parsed), attribute.initializer?.text]));
          nodes.push([node.tagName.getText(parsed).toLowerCase(), attributes]);
        }
        ts.forEachChild(node,visit);
      };
      visit(declaration.initializer.arguments.at(-1));
      result.set(declaration.name.text,nodes);
    }
  }
  return result;
}
const original = icons(await load('app/_dream/components/chat/Icons.tsx'));
const native = icons(await load('app/_dream/components/chat/Icons.native.tsx'));
assert.ok(native.size > 0);
for (const [name, geometry] of native) assert.deepEqual(geometry,original.get(name),`Native geometry changed: ${name}`);
const css = await load('app/_dream/styles/tokens.css');
function tokens(selector) {
  const start = css.indexOf(selector);
  assert.ok(start >= 0);
  const body = css.slice(start + selector.length,css.indexOf('}', start));
  return Object.fromEntries([...body.matchAll(/--(color-[\w-]+):\s*([^;]+);/g)].map(match => [match[1],match[2].trim()]));
}
const palettes = [
  ['light',false,tokens(':root {')],
  ['dark',false,tokens("[data-theme='dark'] {")],
  ['system',true,tokens(":root:not([data-theme='light']) {")],
];
let checkedTokens = 0;
for (const [mode,systemDark,expected] of palettes) for (const [key,value] of Object.entries(inkColors(mode,systemDark))) {
  assert.equal(value,expected[key],`${mode} token changed: ${key}`); checkedTokens++;
}
console.log(JSON.stringify({originalIcons:original.size,nativeIcons:native.size,checkedTokens,scope:'SVG geometry and existing theme values only',wholePageAccepted:false}));
