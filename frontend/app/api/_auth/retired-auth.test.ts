// [Input] Actual thin Next legacy-route exports and shared configured public authority parser.
// [Output] Explicit410 before generic auth; no password/code/body/key forwarding or cookie mutation.
// [Pos] Provider-free public Next issuer-retirement contracts; actual Admin OAuth is separate.
// [Sync] 2026-09-14: preserve all eight Next legacy methods and safe503 configuration failure.
import test from 'node:test';
import assert from 'node:assert/strict';
import { retiredAuthentication } from './retired-auth.ts';
import { POST as login } from '../login/route.ts';
import { POST as register } from '../register/route.ts';
import { GET as googleLogin } from '../../oauth/google/login/route.ts';
import { GET as googleCallback } from '../../oauth/google/callback/route.ts';
import { POST as deviceCode } from '../../oauth/device/code/route.ts';
import { GET as deviceGet, POST as devicePost } from '../../oauth/device/verify/route.ts';
import { POST as token } from '../../oauth/token/route.ts';

const config = { INK_ADMIN_DREAM_BASE_URL: 'https://admin.example', INK_ADMIN_AUTH_ISSUER: 'https://admin.example/api/auth', INK_DREAM_API_RESOURCE: 'https://dream.example/api' };

for (const [name, handler] of Object.entries({ login, register, googleLogin, googleCallback, deviceCode, deviceGet, devicePost, token })) {
  test(name + ' returns configured410 without a session or service credential', async () => {
    const previous = Object.fromEntries(Object.keys(config).map(key => [key, process.env[key]]));
    Object.assign(process.env, config);
    try {
      const response = handler();
      assert.equal(response.status, 410);
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.equal(response.headers.get('set-cookie'), null);
      assert.equal(response.headers.get('location'), null);
      const body = await response.json();
      assert.equal(body.error.code, 'DREAM_AUTHENTICATION_RETIRED');
      assert.equal(body.authentication.token_endpoint, 'https://admin.example/api/auth/oauth2/token');
      assert.equal(body.authentication.verification_uri, 'https://admin.example/auth/device');
      assert.equal(Object.keys(body.authentication).length, 8);
    } finally {
      for (const [key, value] of Object.entries(previous)) if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  });
}

test('retired owner reads only configured public authority fields', () => {
  const publicOnly = new Proxy(config, { get(object, key) { assert.ok(key in config); return object[key as keyof typeof config]; } });
  assert.equal(retiredAuthentication(publicOnly).status, 410);
});

for (const patch of [{ INK_ADMIN_DREAM_BASE_URL: '' }, { INK_ADMIN_DREAM_BASE_URL: 'http://remote.example' },
  { INK_ADMIN_AUTH_ISSUER: 'https://another.example/api/auth' }, { INK_DREAM_API_RESOURCE: 'invalid\nresource' }]) {
  test('invalid authority returns503 without guessing or publishing an endpoint: ' + Object.keys(patch)[0], async () => {
    const response = retiredAuthentication({ ...config, ...patch });
    assert.equal(response.status, 503);
    assert.ok(!(await response.text()).includes('https://'));
  });
}
