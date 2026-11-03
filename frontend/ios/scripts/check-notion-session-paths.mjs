// [Input] Production host connect validation and named canonical credential-home fixtures.
// [Output] Acceptance of original actor/thread homes and rejection of other paths, executables and ambient credentials.
// [Pos] Provider-free iOS transport regression; no commands, network, accounts or credential files are used.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import vm from 'node:vm';

const host = fs.readFileSync(new URL('../runtime/host.cjs', import.meta.url), 'utf8');
const start = host.indexOf('        let canonicalDirectory = false;');
const end = host.indexOf('        try {\n          refreshGuestResolver();', start);
assert(start > 0 && end > start, 'Production connect validator must be present');
const validate = '(function () {\n' + host.slice(start, end) + '\nreturn "accepted";})()';
const temporary = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ink-notion-session-paths-')));
let passed = 0;
try {
  const root = path.join(temporary, 'workspaces');
  const actor = path.join(temporary, 'notion-runtime', 'users', 'fixture', 'home');
  const thread = path.join(root, 'fixture-thread', '.notion-home');
  const outside = path.join(temporary, 'outside', '.notion-home');
  const nested = path.join(thread, 'child');
  for (const directory of [actor, nested, outside]) fs.mkdirSync(directory, {recursive: true, mode: 0o700});
  const executable = path.join(temporary, 'ntn');
  const binary = Buffer.from('fixture executable; never executed');
  fs.writeFileSync(executable, binary);
  const manifest = {binarySha256: crypto.createHash('sha256').update(binary).digest('hex')};
  const alias = path.join(root, 'fixture-thread', 'alias', '.notion-home');
  fs.symlinkSync(path.dirname(outside), path.dirname(alias));
  const cases = [
    ['actor', actor, {}, 'accepted'],
    ['thread', thread, {}, 'accepted'],
    ['outside', outside, {}, 'IOS_RUNTIME_SESSION_INVALID'],
    ['nested', nested, {}, 'IOS_NOTION_CLI_EXECUTABLE_INVALID'],
    ['workspace', path.dirname(thread), {}, 'IOS_NOTION_CLI_EXECUTABLE_INVALID'],
    ['alias', alias, {}, 'IOS_RUNTIME_SESSION_INVALID'],
    ['sibling-prefix', path.join(temporary, 'workspaces-other', 'fixture', '.notion-home'), {}, 'IOS_RUNTIME_SESSION_INVALID'],
    ['ambient-home', thread, {HOME: thread}, 'IOS_NOTION_CLI_EXECUTABLE_INVALID'],
    ['ambient-token', thread, {NOTION_API_TOKEN: 'fixture-must-be-rejected'}, 'IOS_NOTION_CLI_EXECUTABLE_INVALID'],
    ['mismatched-home', thread, {NOTION_HOME: actor}, 'IOS_NOTION_CLI_EXECUTABLE_INVALID'],
    ['keyring', thread, {NOTION_KEYRING: '1'}, 'IOS_NOTION_CLI_EXECUTABLE_INVALID'],
  ];
  for (const [name, cwd, extra, expected] of cases) {
    const message = {type: 'connect', purpose: 'notion-cli', cwd, argv: [executable, '--version'],
      env: {NOTION_HOME: cwd, NOTION_KEYRING: '0', ...extra}};
    let error;
    const context = vm.createContext({message, root, fs, path, crypto, defaultDirectory: temporary,
      notionExecutable: executable, notionManifest: manifest,
      withinRoot: value => typeof value === 'string' && (value === root || value.startsWith(root + path.sep)),
      fail: code => {error = code;}});
    const result = vm.runInContext(validate, context);
    assert.equal(error || result, expected, name);
    passed++;
  }
  console.log(JSON.stringify({passed, failed: 0, commandExecutions: 0, networkRequests: 0, credentialReads: 0}));
} finally {
  fs.rmSync(temporary, {recursive: true, force: true});
}
