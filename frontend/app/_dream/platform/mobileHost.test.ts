// [Input] Browser and RN-host route intents against the actual route resolver.
// [Output] Mobile scope, canonical-route preservation and credential-free state contract evidence.
// [Pos] Provider-free RN navigation regression tests.
import assert from 'node:assert/strict';
import test from 'node:test';
import {isReactNativeHost, mobileHostPath, reportMobileHostRoute} from './mobileHost';

test('ordinary Web keeps its current routes', () => {
  Object.defineProperty(globalThis, 'window', {configurable: true, value: {location: {origin: 'http://localhost:5173'}}});
  assert.equal(isReactNativeHost(), false);
  assert.equal(mobileHostPath('/story-workspace/dream'), '/story-workspace/dream');
  assert.equal(mobileHostPath('/story-workspace/runs/run_existing/execution'), '/story-workspace/runs/run_existing/execution');
});

test('RN navigation preserves supported paths and excludes the Dream workbench', () => {
  Object.defineProperty(globalThis, 'window', {configurable: true, value: {
    __INK_NATIVE_HOST__: {framework: 'react-native'}, location: {origin: 'http://localhost:5173'},
  }});
  for (const path of ['/story-workspace/chat?thread=existing', '/story-workspace/decks', '/story-workspace/writing',
    '/story-workspace/timeline', '/story-workspace/analysis?section=echoes', '/story-workspace/settings/model',
    '/story-workspace/subscription', '/story-workspace/characters']) {
    assert.equal(mobileHostPath(path), path);
  }
  for (const path of ['/story-workspace/dream', '/story-workspace/creation-guide',
    '/story-workspace/runs/run_existing/execution', '/story-workspace/episodes/episode_existing/review',
    '/story-workspace/runs/run_existing', '/oauth/device/verify', 'https://example.com/story-workspace/chat']) {
    assert.equal(mobileHostPath(path), '/story-workspace/chat');
  }
});

test('host reports path and authenticated boolean without session data', () => {
  const values: unknown[] = [];
  Object.defineProperty(globalThis, 'window', {configurable: true, value: {
    __INK_NATIVE_HOST__: {framework: 'react-native'},
    location: {origin: 'http://localhost:5173', pathname: '/story-workspace/chat', search: ''},
    webkit: {messageHandlers: {inkHostState: {postMessage: (value: unknown) => values.push(value)}}},
  }});
  reportMobileHostRoute(true);
  reportMobileHostRoute(false);
  assert.deepEqual(values, [
    {path: '/story-workspace/chat', authenticated: true, authFailure: false},
    {path: '/story-workspace/chat', authenticated: false, authFailure: false},
  ]);
  Reflect.deleteProperty(globalThis, 'window');
});
