// [Input] Production BFF/OAuth handlers and deterministic Admin/Python transport replacements.
// [Output] Isolated HTTP browser journey with real PKCE, Bearer proxy and SSE protocol boundaries.
// [Pos] Technical harness only; no normal services, database, credentials or model calls.
import { createHash, randomUUID } from 'node:crypto';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
import { AdminBffClient, type AdminBffConfig } from '../../app/api/_auth/admin-client';
import { BffLoginBoundary } from '../../app/api/_auth/login-boundary';
import { createBffHandlers } from '../../app/api/_auth/handlers';
import { createApiProxy } from '../../app/api/_auth/api-proxy';

const profile = { id: '42', email: 'fixture@example.test', display_name: 'Web OAuth fixture', avatar_url: null, role: 'user', created_at: null, updated_at: null, auth_providers: ['credential'] };
export async function startWebBearerHarness() {
  process.env.INK_TRACE_ENABLED = 'false';
  let base = '';
  const state = {
    resolves: 0, grants: 0, refreshes: 0, revokes: 0, codeChecks: 0, refreshUnavailable: false, revokeUnavailable: false,
    lifetime: 300, revoked: false, accessInvalid: false,
    requests: [] as { path: string; method: string; bearer: boolean; cookie: boolean; csrf: boolean }[],
    reset() { this.resolves = this.grants = this.refreshes = this.revokes = this.codeChecks = 0; this.requests.length = 0;
      this.revoked = this.accessInvalid = this.refreshUnavailable = this.revokeUnavailable = false; this.lifetime = 300; codes.clear(); refreshes.clear(); accesses.clear(); },
  };
  const codes = new Map<string, { challenge: string; redirect: string }>();
  const refreshes = new Set<string>();
  const accesses = new Map<string, number>();
  const entry = `
import React,{useRef,useState} from 'react';import {createRoot} from 'react-dom/client';
import {AuthProvider,useAuth} from '/app/_dream/contexts/AuthContext.tsx';
import {installBrowserBearerFetch,browserRequestHeaders} from '/app/_dream/lib/browserSession.web.ts';
import {ClaudeAgentChatTransport} from '/app/_dream/lib/claude-agent-transport.ts';
import {requestClaudeThreadStop} from '/app/_dream/components/chat/threadStop.ts';
import {AuthenticatedImage,AuthenticatedLink} from '/app/_dream/components/chat/AuthenticatedResource.tsx';
installBrowserBearerFetch();
function Surface(){const auth=useAuth();const [result,setResult]=useState(''),[chat,setChat]=useState('');const abort=useRef(null);
 if(auth.isLoading)return React.createElement('p',null,'Loading session');
 if(!auth.isAuthenticated)return React.createElement('main',null,React.createElement('h1',null,'Sign in'),auth.authError&&React.createElement('p',{role:'alert'},auth.authError),React.createElement('a',{href:'/auth/start?return_to=/bearer-harness'},'Sign in with Admin'));
 const run=fn=>()=>Promise.resolve().then(fn).catch(()=>setResult('Request failed'));
 async function send(){const controller=new AbortController();abort.current=controller;setChat('');const transport=new ClaudeAgentChatTransport({api:'/api/claude-agent',headers:()=>browserRequestHeaders()});
 const reader=(await transport.sendMessages({trigger:'submit-message',chatId:'fixture-thread',messageId:undefined,abortSignal:controller.signal,messages:[{id:'message-'+Date.now(),role:'user',parts:[{type:'text',text:'请向我问好。'}]}]})).getReader();
 for(;;){const next=await reader.read();if(next.done)break;if(next.value.type==='text-delta')setChat(text=>text+next.value.delta);}}
 return React.createElement('main',null,React.createElement('h1',null,'Signed in '+auth.user.display_name),auth.authError&&React.createElement('p',{role:'alert'},auth.authError),
 React.createElement('button',{onClick:run(async()=>{const replies=await Promise.all(Array.from({length:12},()=>fetch('/api/decks')));setResult(replies.every(response=>response.ok)?'12 requests succeeded':'Request failed');})},'Load concurrently'),
 React.createElement('button',{onClick:run(send)},'Send chat'),
 React.createElement('button',{onClick:run(async()=>{await requestClaudeThreadStop('fixture-thread');abort.current?.abort();setResult('Stopped');})},'Stop chat'),
 React.createElement('button',{onClick:run(async()=>{const form=new FormData();form.append('file',new Blob(['upload bytes'],{type:'text/plain'}),'note.txt');const response=await fetch('/api/storage/upload',{method:'POST',body:form});setResult(response.ok?'Uploaded':'Request failed');})},'Upload file'),
 React.createElement('button',{onClick:()=>auth.logout()},'Log out'),React.createElement('output',{'aria-label':'Result'},result),React.createElement('output',{'aria-label':'Chat'},chat),
 React.createElement(AuthenticatedImage,{src:'/api/storage/file/image',alt:'Private image'}),React.createElement(AuthenticatedLink,{href:'/api/storage/file/note',download:'note.txt'},'Download file'));
}
createRoot(document.getElementById('root')).render(React.createElement(AuthProvider,null,React.createElement(Surface)));
`;
  async function handle(incoming: IncomingMessage, outgoing: ServerResponse, next: () => void) {
    const url = new URL(incoming.url!, base);
    if (url.pathname === '/api/auth/oauth2/authorize') {
      const code = randomUUID(); codes.set(code, { challenge: url.searchParams.get('code_challenge')!, redirect: url.searchParams.get('redirect_uri')! });
      const destination = new URL('/auth/callback', base);
      destination.search = new URLSearchParams({ code, state: url.searchParams.get('state')!, iss: base + '/api/auth' }).toString();
      outgoing.setHeader('content-type', 'text/html');
      outgoing.end(`<html><head><link rel="icon" href="data:,"></head><body><h1>Admin authorization fixture</h1><a href="${destination.href.replaceAll('&', '&amp;')}">Continue test account</a></body></html>`); return;
    }
    if (!url.pathname.startsWith('/auth/') && !url.pathname.startsWith('/api/')) return next();
    const headers = new Headers();
    for (const [key, value] of Object.entries(incoming.headers)) if (value !== undefined) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
    const chunks: Buffer[] = []; for await (const chunk of incoming) chunks.push(Buffer.from(chunk));
    const method = incoming.method!;
    const abort = new AbortController(); outgoing.once('close', () => abort.abort());
    const request = new Request(url, { method, headers, signal: abort.signal, ...(['GET', 'HEAD'].includes(method) ? {} : { body: Buffer.concat(chunks) }) });
    state.requests.push({ path: url.pathname, method, bearer: /^Bearer /.test(headers.get('authorization') ?? ''), cookie: headers.has('cookie'), csrf: headers.has('x-ink-csrf') });
    let response: Response;
    if (url.pathname === '/auth/start') response = await handlers.start(request);
    else if (url.pathname === '/auth/callback') response = await handlers.webCallback(request);
    else if (url.pathname === '/auth/refresh') response = await handlers.refresh(request);
    else if (url.pathname === '/auth/session') response = await handlers.session(request);
    else if (url.pathname === '/auth/logout') response = await handlers.logout(request);
    else response = await proxy(request);
    outgoing.statusCode = response.status;
    for (const [key, value] of response.headers) if (key !== 'set-cookie') outgoing.setHeader(key, value);
    const cookies = response.headers.getSetCookie(); if (cookies.length) outgoing.setHeader('set-cookie', cookies);
    const reader = response.body?.getReader();
    if (reader) { try { for (;;) { const next = await reader.read(); if (next.done) break; if (outgoing.destroyed) { await reader.cancel(); break; } outgoing.write(next.value); } } finally { reader.releaseLock(); } }
    outgoing.end();
  }
  const server = await createServer({ root: fileURLToPath(new URL('../../', import.meta.url)), configFile: false, logLevel: 'silent',
    resolve: { alias: [{ find: /^(?:.*\/)?browserSession(?:\.ts)?$/, replacement: fileURLToPath(new URL('../../app/_dream/lib/browserSession.web.ts', import.meta.url)) }] },
    server: { host: '127.0.0.1', port: 0 }, plugins: [{ name: 'web-bearer-fixture', enforce: 'pre',
      configureServer(vite) { vite.middlewares.use((incoming, outgoing, next) => {
        if (incoming.url?.split('?')[0] === '/bearer-harness') {
          void vite.transformIndexHtml('/bearer-harness', '<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/bearer-harness.js"></script></body></html>').then(html => { outgoing.setHeader('content-type', 'text/html'); outgoing.end(html); }); return;
        }
        void handle(incoming, outgoing, next).catch(() => { if (!outgoing.headersSent) outgoing.statusCode = 500; outgoing.end(); });
      }); },
      resolveId(id) { return id === '/bearer-harness.js' ? '\0bearer-harness.js' : null; }, load(id) { return id === '\0bearer-harness.js' ? entry : null; },
    }] });
  await server.listen();
  const address = server.httpServer!.address(); if (!address || typeof address === 'string') throw Error('FIXTURE_ADDRESS_REQUIRED');
  base = `http://127.0.0.1:${address.port}`;
  const boundary = new BffLoginBoundary({ publicOrigin: base, callbackUri: base + '/auth/callback', cookieSecret: 'fixture-cookie-secret-'.repeat(3) });
  const configuration: AdminBffConfig = { origin: base, transportOrigin: base, issuer: base + '/api/auth', resource: base + '/api', serviceId: 'fixture-service', serviceSecret: 'fixture-service-secret-'.repeat(3), timeoutMilliseconds: 5_000, maxResponseBytes: 100_000 };
  function issue() {
    const access = randomUUID(), refresh = randomUUID(); accesses.set(access, Date.now() + state.lifetime * 1_000); refreshes.add(refresh);
    state.revoked = state.accessInvalid = false;
    return Response.json({ access_token: access, refresh_token: refresh, token_type: 'Bearer', expires_in: state.lifetime });
  }
  const transport: typeof fetch = async (input, init) => {
    const url = new URL(String(input)); const headers = new Headers(init?.headers);
    if (url.pathname === '/api/auth/oauth2/token') {
      const body = new URLSearchParams(String(init?.body));
      if (body.get('client_id') !== 'fixture-browser' || body.get('resource') !== configuration.resource) return Response.json({ error: 'invalid_client' }, { status: 400 });
      if (body.get('grant_type') === 'authorization_code') {
        const code = codes.get(body.get('code')!); codes.delete(body.get('code')!);
        const challenge = createHash('sha256').update(body.get('code_verifier') ?? '').digest('base64url');
        if (!code || challenge !== code.challenge || code.redirect !== body.get('redirect_uri')) return Response.json({ error: 'invalid_grant' }, { status: 400 });
        state.grants++; state.codeChecks++; return issue();
      }
      state.refreshes++;
      if (state.refreshUnavailable) return Response.json({ error: 'temporarily_unavailable' }, { status: 503 });
      if (state.revoked || !refreshes.delete(body.get('refresh_token')!)) return Response.json({ error: 'invalid_grant' }, { status: 400 });
      return issue();
    }
    if (url.pathname === '/api/auth/oauth2/revoke') {
      state.revokes++;
      if (state.revokeUnavailable) return Response.json({ error: 'temporarily_unavailable' }, { status: 503 });
      refreshes.delete(new URLSearchParams(String(init?.body)).get('token')!); return Response.json({});
    }
    const envelope = (data: unknown) => Response.json({ request_id: headers.get('x-request-id'), data });
    if (url.pathname.endsWith('/browser-sessions/resolve')) { state.resolves++; throw Error('UNEXPECTED_SESSION_RESOLVE'); }
    if (url.pathname.endsWith('/capabilities')) return envelope({ version: '1', auth: { issuer: configuration.issuer, jwks_uri: configuration.issuer + '/jwks', algorithm: 'ES256', resource: configuration.resource,
      clients: { browser: 'fixture-browser', device: 'fixture-device' }, scopes: ['openid', 'offline_access', 'dream:read', 'dream:write'], delegations: [] }, schema_capabilities: [],
      operations: [{ name: 'user-profile.current', kind: 'read', user_scope: 'dream:read', background_scope: null, input_schema_version: 1, output_schema_version: 1, contract_sha256: '01011316efa10475dd1d1aa8856c82cb17ddbeb404125ebcd80af5f250f2a9d0' }] });
    if (url.pathname.endsWith('/principal')) return envelope({ subject: 'fixture-subject', canonical_user_id: profile.id, client_id: 'fixture-browser', scopes: ['dream:read', 'dream:write'], status: 'active' });
    if (url.pathname.endsWith('/operations/user-profile.current')) return envelope({ user: profile });
    throw Error('UNEXPECTED_ADMIN_PATH');
  };
  const admin = new AdminBffClient(configuration, transport, async () => 'fixture-service-token');
  const handlers = createBffHandlers(boundary, admin);
  const proxy = createApiProxy(boundary, admin, new URL('http://python.fixture.invalid'), async (input, init) => {
    const path = new URL(String(input)).pathname;
    const access = new Headers(init?.headers).get('authorization')?.slice(7) ?? '';
    if (state.accessInvalid || !accesses.has(access) || accesses.get(access)! <= Date.now()) return Response.json({ detail: 'ACCESS_TOKEN_REQUIRED' }, { status: 401 });
    if (path === '/api/claude-agent') {
      const events = [{ type: 'text-start', id: 'text-1' }, { type: 'text-delta', id: 'text-1', delta: '你好，浏览器。' }, { type: 'text-end', id: 'text-1' }, { type: 'finish', finishReason: 'stop' }];
      const stream = new ReadableStream<Uint8Array>({ async pull(controller) { const event = events.shift(); if (!event) { controller.close(); return; } await new Promise(resolve => setTimeout(resolve, 10)); controller.enqueue(new TextEncoder().encode('data: ' + JSON.stringify(event) + '\n\n')); } });
      return new Response(stream, { headers: { 'content-type': 'text/event-stream' } });
    }
    if (path.endsWith('/stop')) return Response.json({ ok: true, thread_id: 'fixture-thread', stop_requested: true, running: false, lifecycle: 'idle' });
    if (path === '/api/storage/file/image') return new Response(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64'), { headers: { 'content-type': 'image/png' } });
    if (path === '/api/storage/file/note') return new Response('private attachment', { headers: { 'content-type': 'text/plain' } });
    if (path === '/api/storage/upload') { const body = await new Response(init?.body).text(); return body.includes('upload bytes') ? Response.json({ key: 'fixture-upload' }) : new Response(null, { status: 400 }); }
    return Response.json({ decks: [] });
  });
  return { base, state, close: () => server.close() };
}
