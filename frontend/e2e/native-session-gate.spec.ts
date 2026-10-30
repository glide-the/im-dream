// [Input] Production SessionGate, original public session DTO and explicit HTTP/native completion boundaries.
// [Output] Home appears after login dismissal; foreground, cancellation and retry preserve the original session contract.
// [Pos] Provider-free technical fixture; actual UIKit sheet and normal-account login require target acceptance.
// Impact: login presentation changes; Thread, Project/Episode, artifacts, Run publication, Hook and real data remain unchanged.
import {expect,test,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const entry=String.raw`
import React from 'react';import {createRoot} from 'react-dom/client';
import SessionGate from '/src/platform/SessionGate.native.tsx';
function Home({logout,refresh,user}){return <div><h1>Native home</h1><span>{user.display_name}</span><button onClick={()=>void refresh()}>Refresh session</button><button onClick={()=>void logout().catch(()=>{})}>Logout</button></div>;}
createRoot(document.querySelector('#root')).render(<div style={{height:'100dvh',display:'flex',flexDirection:'column'}}><SessionGate>{(logout,refresh,user)=><Home {...{logout,refresh,user}}/>}</SessionGate></div>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
type Facts={authenticated:boolean;reads:number;failed:boolean;logoutFails:boolean;logoutCalls:number;errors:string[];httpStatuses:{path:string;status:number}[];httpDiagnostics:{path:string;status:number}[]};
const facts=new WeakMap<Page,Facts>();
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-login-ntn-20261030/vite-session',optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','zod']},resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/session-platform-web-boundary.ts'}]},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'native-session-fixture',enforce:'pre',resolveId(id){if(id==='/session-entry.tsx')return '\0session-entry';},async load(id){return id==='\0session-entry'?(await transformWithEsbuild(entry,'session-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'})).code:null;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native-session')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-session','<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/session-entry.tsx"></script></body></html>'));});}}]});
 await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('SESSION_FIXTURE_LISTENER');base='http://127.0.0.1:'+address.port+'/native-session';
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
 const f:Facts={authenticated:false,reads:0,failed:false,logoutFails:false,logoutCalls:0,errors:[],httpStatuses:[],httpDiagnostics:[]};facts.set(page,f);page.on('pageerror',error=>f.errors.push(error.message));page.on('console',message=>{if(message.type()!=='error')return;const match=message.text().match(/^Failed to load resource: the server responded with a status of (401|503) /);const path=new URL(message.location().url||'about:blank').pathname;if(match&&['/auth/session','/auth/logout'].includes(path))f.httpDiagnostics.push({path,status:Number(match[1])});else f.errors.push(message.text());});
 await page.route('**/auth/session',route=>{f.reads++;f.httpStatuses.push({path:'/auth/session',status:f.failed?503:f.authenticated?200:401});return f.failed?route.fulfill({status:503,json:{error:'Unavailable'}}):f.authenticated?route.fulfill({json:{user:{id:'7',email:'session@example.invalid',display_name:'Original account',avatar_url:null,role:'user',created_at:null},csrf_token:'s'.repeat(43)}}):route.fulfill({status:401,json:{error:'Unauthenticated'}});});
 await page.route('**/auth/logout',route=>{f.logoutCalls++;f.httpStatuses.push({path:'/auth/logout',status:f.logoutFails?503:200});if(!f.logoutFails)f.authenticated=false;return route.fulfill({status:f.logoutFails?503:200,json:f.logoutFails?{error:'Unavailable'}:{success:true}});});
});
test.afterEach(async({page})=>{const f=facts.get(page)!;expect(f.errors).toEqual([]);for(const item of f.httpDiagnostics)expect(f.httpStatuses).toContainEqual(item);});
async function open(page:Page){await page.goto(base);await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();}
test('login confirmation opens native home after the sheet settles, with no foreground race',async({page})=>{
 await open(page);await page.getByRole('button',{name:'登录',exact:true}).click();expect(await page.evaluate(()=>(window as any).__sessionPlatform.presented)).toBe(1);facts.get(page)!.authenticated=true;
 await page.evaluate(()=>(window as any).__sessionPlatform.active());await expect(page.getByRole('heading',{name:'Native home'})).toHaveCount(0);expect(facts.get(page)!.reads).toBe(1);
 await page.evaluate(()=>(window as any).__sessionPlatform.finish());await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();await expect(page.getByText('Original account',{exact:true})).toBeVisible();expect(facts.get(page)!.reads).toBe(2);
});
test('closing the login sheet is silent cancellation and allows a new login',async({page})=>{
 await open(page);await page.getByRole('button',{name:'登录',exact:true}).click();await page.evaluate(()=>(window as any).__sessionPlatform.cancel());await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();await expect(page.getByRole('alert')).toHaveCount(0);expect(facts.get(page)!.reads).toBe(1);
 await page.getByRole('button',{name:'登录',exact:true}).click();expect(await page.evaluate(()=>(window as any).__sessionPlatform.presented)).toBe(2);facts.get(page)!.authenticated=true;await page.evaluate(()=>(window as any).__sessionPlatform.finish());await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
});
test('a failed login presentation can be retried through the same public session path',async({page})=>{
 await open(page);await page.getByRole('button',{name:'登录',exact:true}).click();await page.evaluate(()=>(window as any).__sessionPlatform.cancel('LOGIN_UNAVAILABLE'));await expect(page.getByRole('alert')).toHaveText('登录未完成，可重新打开登录页面。');
 await page.getByRole('button',{name:'重新登录',exact:true}).click();facts.get(page)!.authenticated=true;await page.evaluate(()=>(window as any).__sessionPlatform.finish());await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
});
test('session-read recovery and failed logout retain the original account ownership',async({page})=>{
 const f=facts.get(page)!;f.failed=true;await page.goto(base);await expect(page.getByRole('alert')).toHaveText('工作区暂时无法打开，请重试。');f.failed=false;f.authenticated=true;await page.getByRole('button',{name:'重试',exact:true}).click();await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();
 f.logoutFails=true;await page.getByRole('button',{name:'Logout',exact:true}).click();await expect.poll(()=>f.logoutCalls).toBe(1);await expect(page.getByRole('heading',{name:'Native home'})).toBeVisible();f.logoutFails=false;await page.getByRole('button',{name:'Logout',exact:true}).click();await expect(page.getByRole('button',{name:'登录',exact:true})).toBeVisible();
});
