// [Input] Actual Settings presenters, shared hook/API, synthetic HTTP and installed Chrome.
// [Output] Menu/dialog, revocation/recovery, theme/locale/responsive and native-boundary evidence.
// [Pos] Technical isolation: UI changes; API/ownership/CSRF contract retained; Project/Episode/Artifact/.dream/Run/Hook/DB/model out of scope.
import {test, expect, type Page} from '@playwright/test';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
import type {ExternalShare} from '../app/_dream/api/externalShareApi';
import type {ExternalLinksFixture} from './fixtures/external-links-harness';
const root=fileURLToPath(new URL('../',import.meta.url));
const first='11111111-1111-4111-8111-111111111111', second='22222222-2222-4222-8222-222222222222';
const title='周末安排的讨论';
let server: Awaited<ReturnType<typeof createServer>>, base: string;
interface Scenario {
  records: ExternalShare[]; owner: string; fault: number; commitOnError: boolean;
  writes: {id:string; key:string; csrf:string|undefined}[];
  reads: string[]; errors: string[]; expectedFailures: Set<string>;
}
const scenarios=new WeakMap<Page,Scenario>();
const facts=(page:Page)=>page.evaluate(()=>(window as unknown as {externalLinksFixture:ExternalLinksFixture}).externalLinksFixture);
test.beforeAll(async()=>{
  const native=`export * from ${JSON.stringify(root+'e2e/native/appearance-platform-web-boundary.ts')};
export const NativeModules={InkRuntime:{copyText:async value=>navigator.clipboard.writeText(value)}};
export const Linking={openURL:async value=>window.externalLinksFixture.opened.push(value)};`;
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:root+'test-results/external-links-popup/cache',resolve:{dedupe:['react','react-dom']},server:{host:'127.0.0.1',port:0,hmr:false},optimizeDeps:{entries:['e2e/fixtures/external-links-harness.tsx'],include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','i18next','react-i18next','zod']},plugins:[{
    name:'external-links-boundaries',enforce:'pre',
    resolveId(id,importer){if(id==='react-native')return '\0external-links-native';if(id.endsWith('/interfaceSettings')&&importer&&!importer.endsWith('interfaceSettings.ios.ts'))return root+'src/platform/interfaceSettings.ios.ts';},
    load(id){if(id==='\0external-links-native')return native;},
    configureServer(vite){vite.middlewares.use(async(req,res,next)=>{
      if(!req.url?.startsWith('/external-links-harness'))return next();
      res.setHeader('content-type','text/html; charset=utf-8');res.end(await vite.transformIndexHtml('/external-links-harness','<html><head><meta charset="UTF-8"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/external-links-harness.tsx"></script></body></html>'));
    });},
  }]});await server.listen();base=server.resolvedUrls!.local[0];
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page,context})=>{
  const state:Scenario={records:[
    {id:first,kind:'chat',source_id:'thread-a',title,path:'/share/'+'a'.repeat(43),status:'active',source_available:true,created_at:'2026-11-12T08:00:00Z',revoked_at:null},
    {id:second,kind:'chat',source_id:'thread-b',title:'保留的另一份对话',path:'/share/'+'b'.repeat(43),status:'active',source_available:false,created_at:'2026-11-11T08:00:00Z',revoked_at:null},
  ],owner:'42',fault:0,commitOnError:false,writes:[],reads:[],errors:[],expectedFailures:new Set()};scenarios.set(page,state);
  page.on('pageerror',error=>state.errors.push(error.message));
  page.on('console',message=>{
    if(message.type()!=='error')return;
    // Only the explicitly injected revoke HTTP failures are expected browser diagnostics.
    if(state.expectedFailures.has(message.location().url)&&/Failed to load resource:.*status of (403|500)/.test(message.text()))return;
    state.errors.push(message.text());
  });
  page.on('requestfailed',request=>{if(request.failure()?.errorText!=='net::ERR_ABORTED')state.errors.push(request.url());});
  await context.route('https://public.example/share/*',route=>route.fulfill({contentType:'text/html',body:'<h1>Shared fixture</h1>'}));
  await page.route('**/auth/session',route=>route.fulfill({json:{user:{id:state.owner,email:'fixture@example.com',display_name:null,avatar_url:null,role:'user',created_at:null},csrf_token:'c'.repeat(43)}}));
  await page.route('**/api/shares**',async route=>{
    const request=route.request(),url=new URL(request.url()),id=url.pathname.split('/')[3];
    if(request.method()==='POST'){
      const body=request.postDataJSON() as {request_key:string};state.writes.push({id,key:body.request_key,csrf:request.headers()['x-ink-csrf']});
      const share=state.records.find(item=>item.id===id)!;
      if(!state.fault||state.commitOnError){share.status='revoked';share.revoked_at='2026-11-13T09:00:00Z';}
      if(state.fault){state.expectedFailures.add(request.url());await route.fulfill({status:state.fault,json:{detail:'injected revoke failure'}});}else await route.fulfill({json:{share}});
      return;
    }
    state.reads.push(url.pathname);
    if(id){await route.fulfill({json:{share:state.records.find(item=>item.id===id)}});return;}
    const kind=url.searchParams.get('kind'),status=url.searchParams.get('status');
    await route.fulfill({json:{public_origin:'https://public.example',shares:state.records.filter(item=>item.kind===kind&&item.status===status),counts:{chat:state.records.filter(item=>item.kind==='chat'&&item.status==='active').length,note:0},next_cursor:null}});
  });
});
test.afterEach(async({page})=>{expect(scenarios.get(page)!.errors).toEqual([]);});
async function openList(page:Page,native=false){await page.goto(base+'external-links-harness'+(native?'?native=1':''));await page.getByRole('button',{name:/AI对话/}).click();await expect(page.getByText(title,{exact:true}).first()).toBeVisible();}
const more=(page:Page)=>page.getByRole('button',{name:title+'的操作'});
async function openSettings(page:Page){await more(page).click();await page.getByRole('menuitem',{name:'设置',exact:true}).click();await expect(page.getByRole('dialog',{name:'共享设置'})).toBeVisible();return page.getByRole('dialog',{name:'共享设置'});}
async function revoke(page:Page){const dialog=page.getByRole('dialog',{name:'共享设置'});await dialog.getByRole('button',{name:'网络上拥有该链接的任何人',exact:true}).click();await dialog.getByRole('menuitem',{name:/使链接失效/}).click();}

test('three anchored actions preserve row layout, support keyboard and dismiss outside',async({page},testInfo)=>{
  await openList(page);
  const before=await page.getByText('保留的另一份对话',{exact:true}).boundingBox();
  await more(page).click();const menu=page.getByRole('menu');await expect(menu.getByRole('menuitem')).toHaveText(['拷贝链接','查看','设置']);
  expect(await page.getByText('保留的另一份对话',{exact:true}).boundingBox()).toEqual(before);
  await page.screenshot({path:testInfo.outputPath('link-actions.png')});
  await expect(menu.getByRole('menuitem').first()).toBeFocused();await page.keyboard.press('ArrowDown');await expect(menu.getByRole('menuitem',{name:'查看',exact:true})).toBeFocused();
  await page.keyboard.press('Escape');await expect(menu).toHaveCount(0);await expect(more(page)).toBeFocused();
  await more(page).click();await page.getByRole('heading',{name:'AI对话',exact:true}).click();await expect(menu).toHaveCount(0);
  await page.setViewportSize({width:390,height:340});await more(page).click();const bounds=await menu.boundingBox();expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.y).toBeGreaterThanOrEqual(0);expect(bounds!.y+bounds!.height).toBeLessThanOrEqual(340);
});
for(const width of [1200,390])for(const theme of ['Light','Dark'])test(`settings dialog at ${width}px ${theme}`,async({page},testInfo)=>{
  await page.setViewportSize({width,height:850});await openList(page);await page.getByRole('button',{name:theme,exact:true}).click();
  const dialog=await openSettings(page);await expect(dialog.getByText('通用访问权限')).toBeVisible();await expect(dialog.getByText('可以查看',{exact:true})).toBeVisible();
  await expect(dialog.getByRole('button',{name:'关闭',exact:true})).toBeFocused();
  const bounds=await dialog.boundingBox();expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(width);expect(bounds!.y+bounds!.height).toBeLessThanOrEqual(850);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);expect(scenarios.get(page)!.writes).toHaveLength(0);
  await page.screenshot({path:testInfo.outputPath('share-settings.png')});
  await dialog.getByRole('button',{name:'查看链接信息'}).click();await expect(dialog.getByRole('textbox',{name:'分享链接'})).toHaveValue('https://public.example/share/'+'a'.repeat(43));
  await dialog.getByRole('button',{name:'网络上拥有该链接的任何人',exact:true}).click();await page.keyboard.press('Escape');await expect(dialog).toBeVisible();await expect(dialog.getByRole('menu')).toHaveCount(0);
  await page.keyboard.press('Escape');await expect(dialog).toHaveCount(0);await expect(more(page)).toBeFocused();
});

test('copy/view recheck status and clipboard failure exposes the complete address',async({page,context})=>{
  await openList(page);await more(page).click();await page.getByRole('menuitem',{name:'拷贝链接'}).click();await expect.poll(async()=>(await facts(page)).copied).toEqual(['https://public.example/share/'+'a'.repeat(43)]);
  await more(page).click();const opened=context.waitForEvent('page');await page.getByRole('menuitem',{name:'查看',exact:true}).click();const popup=await opened;await popup.waitForURL('https://public.example/share/*');expect(await popup.evaluate(()=>window.opener)).toBeNull();await popup.close();
  await page.evaluate(()=>(window as unknown as {externalLinksFixture:ExternalLinksFixture}).externalLinksFixture.failCopy=true);
  await more(page).click();await page.getByRole('menuitem',{name:'拷贝链接'}).click();await expect(page.getByRole('textbox',{name:'分享链接'})).toHaveValue('https://public.example/share/'+'a'.repeat(43));
  expect(scenarios.get(page)!.reads.filter(path=>path.endsWith(first))).toHaveLength(3);expect(scenarios.get(page)!.writes).toHaveLength(0);
});

test('English labels and source navigation remain available in settings',async({page})=>{
  await openList(page);await page.getByRole('button',{name:'English',exact:true}).click();await page.getByRole('button',{name:'Actions for '+title}).click();await expect(page.getByRole('menuitem')).toHaveText(['Copy link','View','Settings']);await page.getByRole('menuitem',{name:'Settings',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Share settings'});await expect(dialog.getByText('General access')).toBeVisible();await dialog.getByRole('button',{name:'View original'}).click();await expect(dialog).toHaveCount(0);expect((await facts(page)).sources).toEqual([first]);
});

test('revocation retries the same request and moves only the selected record after confirmation',async({page})=>{
  const state=scenarios.get(page)!;state.fault=403;await openList(page);const dialog=await openSettings(page);await revoke(page);
  await expect(dialog.getByRole('alert')).toContainText('请重试');await expect(dialog.getByRole('button',{name:'网络上拥有该链接的任何人',exact:true})).toBeEnabled();await expect(more(page)).toHaveCount(1);
  state.fault=0;await revoke(page);await expect(dialog).toHaveCount(0);await expect(page.getByRole('status').filter({hasText:'链接已失效'})).toBeVisible();await expect(more(page)).toHaveCount(0);await expect(page.getByText('保留的另一份对话',{exact:true})).toBeVisible();
  expect(state.writes).toHaveLength(2);expect(state.writes[0].key).toBe(state.writes[1].key);expect(state.writes.every(write=>write.id===first&&write.csrf==='c'.repeat(43))).toBe(true);
  await page.getByRole('button',{name:'已失效',exact:true}).click();await more(page).click();await expect(page.getByRole('menuitem')).toHaveText(['设置']);await page.getByRole('menuitem',{name:'设置',exact:true}).click();await expect(page.getByRole('dialog').getByRole('button',{name:'链接访问已关闭',exact:true})).toBeDisabled();
});
for(const committed of [false,true])test(`unknown revoke result recovers by reading status, committed=${committed}`,async({page})=>{
  const state=scenarios.get(page)!;state.fault=500;state.commitOnError=committed;await openList(page);const dialog=await openSettings(page);await revoke(page);
  await expect(dialog.getByRole('button',{name:'网络上拥有该链接的任何人',exact:true})).toBeDisabled();await expect(dialog.getByRole('status')).toContainText('结果待确认');expect(state.writes).toHaveLength(1);
  await dialog.getByRole('button',{name:'刷新状态',exact:true}).click();
  if(committed){await expect(dialog).toHaveCount(0);await expect(more(page)).toHaveCount(0);}else{await expect(dialog.getByRole('button',{name:'网络上拥有该链接的任何人',exact:true})).toBeEnabled();await expect(dialog.getByRole('alert')).toHaveCount(0);}
  expect(state.writes).toHaveLength(1);
});

test('account replacement closes the old menu and settings content',async({page})=>{
  await openList(page);await openSettings(page);const state=scenarios.get(page)!;state.owner='84';state.records=[];
  // The fixture emits an external account replacement while the production dialog is open.
  await page.evaluate(()=>window.dispatchEvent(new Event('fixture:replace-account')));
  await expect(page.getByRole('dialog')).toHaveCount(0);await expect(page.getByText(title,{exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:/AI对话/})).toBeVisible();
});

test('deleted original retains sharing access and disables only source navigation',async({page})=>{
  await openList(page);await page.getByRole('button',{name:'保留的另一份对话的操作'}).click();await page.getByRole('menuitem',{name:'设置',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'共享设置'});await expect(dialog.getByText('原内容已删除')).toBeVisible();await expect(dialog.getByRole('button',{name:'查看原内容',exact:true})).toBeDisabled();await expect(dialog.getByRole('button',{name:'网络上拥有该链接的任何人',exact:true})).toBeEnabled();
});

test('native presenter uses the same three actions, access settings and platform copy owner',async({page})=>{
  await openList(page,true);await page.getByRole('button',{name:'⋯',exact:true}).first().click();await page.getByRole('button',{name:'拷贝链接',exact:true}).click();await expect.poll(async()=>(await facts(page)).copied).toHaveLength(1);
  await page.getByRole('button',{name:'⋯',exact:true}).first().click();await page.getByRole('button',{name:'查看',exact:true}).click();await expect.poll(async()=>(await facts(page)).opened).toEqual(['https://public.example/share/'+'a'.repeat(43)]);
  await page.getByRole('button',{name:'⋯',exact:true}).first().click();await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByRole('heading',{name:'共享设置'})).toBeVisible();await page.getByRole('button',{name:/网络上拥有该链接的任何人/}).click();await page.getByRole('button',{name:'使链接失效',exact:true}).click();await expect(page.getByRole('heading',{name:'共享设置'})).toHaveCount(0);await expect(page.getByText('保留的另一份对话',{exact:true})).toBeVisible();expect(scenarios.get(page)!.writes).toHaveLength(1);
});
