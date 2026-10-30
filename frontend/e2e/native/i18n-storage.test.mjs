// [Input] Production i18n module in fresh SSR, native-like and Web storage hosts.
// [Output] Evidence for native registration safety and unchanged saved Web locale behavior.
// [Pos] Explicit isolated platform initialization tests; no UI, backend, accounts or models.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import test from 'node:test';
const frontend = new URL('../../',import.meta.url);
function scenario(program) {
  const result = spawnSync(process.execPath,['--experimental-strip-types','--input-type=module','-e',program],{cwd:frontend,encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
}
const importModule = "const {default:i18n,LANGUAGE_STORAGE_KEY} = await import('./app/_dream/i18n.ts');";
test('SSR keeps the existing English fallback',() => scenario(`
  import assert from 'node:assert/strict';
  ${importModule}
  assert.equal(i18n.language,'en');
`));
test('native-like window without localStorage initializes and switches language',() => scenario(`
  import assert from 'node:assert/strict';
  globalThis.window = {};
  ${importModule}
  assert.equal(i18n.language,'en');
  await i18n.changeLanguage('zh');
  assert.equal(i18n.language,'zh');
`));
test('Web keeps the stored language and original persistence key',() => scenario(`
  import assert from 'node:assert/strict';
  globalThis.window = {};
  let saved = 'zh'; let writtenKey;
  globalThis.localStorage = {getItem:() => saved,setItem:(key,value) => {writtenKey=key;saved=value;}};
  ${importModule}
  assert.equal(i18n.language,'zh');
  await i18n.changeLanguage('en');
  assert.equal(saved,'en'); assert.equal(writtenKey,LANGUAGE_STORAGE_KEY);
`));
test('unavailable browser storage uses the same fallback',() => scenario(`
  import assert from 'node:assert/strict';
  globalThis.window = {};
  globalThis.localStorage = {getItem:() => {throw new Error('storage unavailable');}};
  ${importModule}
  assert.equal(i18n.language,'en');
`));
