// [Input] Public voiceApi module exports after daily-picture generation retirement.
// [Output] Verify Timeline retains historical reads without browser mutation transports.
// [Pos] Historical picture API boundary regression test in frontend/src/api/__tests__
// [Sync] 2026-08-31: lock the read-only Timeline picture client contract.

import { expect, test } from '@playwright/test';
import * as voiceApi from '../voiceApi';

test('Timeline picture transport is read-only', () => {
  expect(typeof voiceApi.getDailyPictures).toBe('function');
  expect(typeof voiceApi.getDailyPictureFull).toBe('function');
  expect('generateDailyPicture' in voiceApi).toBe(false);
  expect('saveDailyPicture' in voiceApi).toBe(false);
});
