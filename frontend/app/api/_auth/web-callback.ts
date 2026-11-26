// [Input] Admin OAuth token response, validated relative return and login transaction boundary.
// [Output] Non-cacheable nonce-protected document storing origin refresh and a one-time tab Access handoff.
// [Pos] Web callback document; application scripts and third-party content never load here.
// [Sync] 2026-11-20: share the Web credential lock and persist only refresh plus login identity across reopening.
import { randomBytes, randomUUID } from 'node:crypto';
import { STORAGE_KEYS } from '../../_dream/constants/storageKeys.ts';
import { BRAND_NAME } from '../../_dream/constants/brand.ts';

export function webCallbackDocument(tokens: { access_token: string; refresh_token?: string; expires_at: number }, returnTo: string, clearCookies: string[]): Response {
  const nonce = randomBytes(24).toString('base64url');
  const sessionId = randomUUID();
  const credentials = JSON.stringify({ session_id: sessionId, access_token: tokens.access_token, refresh_token: tokens.refresh_token,
    expires_at: tokens.expires_at }).replaceAll('<', '\\u003c');
  const persistent = JSON.stringify({ session_id: sessionId, refresh_token: tokens.refresh_token }).replaceAll('<', '\\u003c');
  const destination = JSON.stringify(returnTo).replaceAll('<', '\\u003c');
  const key = JSON.stringify(STORAGE_KEYS.WEB_OAUTH);
  const html = `<!doctype html><html><head><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>${BRAND_NAME}</title></head><body><p id="status">正在完成登录…</p><script nonce="${nonce}">history.replaceState(null,'','/auth/callback');(async()=>{try{await navigator.locks.request(${key},async()=>{localStorage.setItem(${key},JSON.stringify(${persistent}));sessionStorage.setItem(${key},JSON.stringify(${credentials}));});location.replace(${destination});}catch{document.getElementById('status').textContent='无法保存登录状态，请允许此网站使用浏览器存储后重新登录。';}})();</script></body></html>`;
  const headers = new Headers({ 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store',
    'referrer-policy': 'no-referrer', 'x-content-type-options': 'nosniff',
    'content-security-policy': `default-src 'none'; script-src 'nonce-${nonce}'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'` });
  for (const cookie of clearCookies) headers.append('set-cookie', cookie);
  return new Response(html, { headers });
}
