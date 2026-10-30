// [Input] Original deckVisuals map and the installed, lockfile-owned react-icons package.
// [Output] Identical fixed SVG paths and theme-token names for native Deck/Agent rows.
// [Pos] Build-time asset projection; Web icons and third-party package code remain unchanged.
// [Sync] 2026-10-29: project the original preview FaPlay separately from configured Deck icon keys.
import {readFile,writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {Children,isValidElement} from 'react';
const require=createRequire(import.meta.url);
const {iconMap,COLORS}=require('../app/_dream/components/deckVisuals.ts');
const {FaPlay}=require('react-icons/fa');
const packageInfo=JSON.parse(await readFile(new URL('./package.json',pathToFileURL(require.resolve('react-icons'))),'utf8'));
function projectIcon(name,Icon) {
  const element=Icon({});
  if(!isValidElement(element) || typeof element.props.attr?.viewBox!=='string')throw new Error(`Invalid original icon: ${name}`);
  return {viewBox:element.props.attr.viewBox,paths:Children.toArray(element.props.children).map(child=>{
    if(!isValidElement(child) || child.type!=='path' || typeof child.props.d!=='string')throw new Error(`Unsupported original path: ${name}`);
    const {children,...attributes}=child.props;return attributes;
  })};
}
const icons=Object.fromEntries(Object.entries(iconMap).map(([name,Icon])=>[name,projectIcon(name,Icon)]));
const actions={play:projectIcon('FaPlay',FaPlay)};
const colors=Object.fromEntries(Object.entries(COLORS).map(([name,{hex}])=>{
  const match=/^var\(--(color-[\w-]+)\)$/.exec(hex);
  if(!match)throw new Error(`Invalid original token: ${name}`);
  return [name,match[1]];
}));
const data={source:{package:'react-icons',version:packageInfo.version,owner:'app/_dream/components/deckVisuals.ts',actionOwner:'app/_dream/components/deck/DeckManagerPanels.tsx',glyphs:'Font Awesome 5',license:'CC BY 4.0',attribution:'Font Awesome by Fonticons, Inc.',licenseUrl:'https://fontawesome.com/license/free'},icons,actions,colors};
const target=new URL('../shared/deck-icons.json',import.meta.url);
if(process.argv.includes('--write'))await writeFile(target,JSON.stringify(data,null,2)+'\n');
else if(JSON.stringify(JSON.parse(await readFile(target,'utf8')))!==JSON.stringify(data))throw new Error('Native Deck icons differ from the current Web assets');
console.log(JSON.stringify({deckIcons:Object.keys(icons).length,actionIcons:Object.keys(actions).length,colorTokens:Object.keys(colors).length,packageVersion:packageInfo.version,geometry:'identical',written:process.argv.includes('--write')}));
