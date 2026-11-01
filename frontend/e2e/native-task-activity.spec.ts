// [Input] Production Native task panel, observer, source navigation and synthetic original DTO transport.
// [Output] Five-section navigation, readonly detail, partial failure and lifecycle cancellation receipts.
// [Pos] Provider-free RNW qualification; actual Hermes/AppState and real business remain separate gates.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild,type ViteDevServer} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const platform=String.raw`export * from 'react-native-web';
const listeners=new Set();
export const AppState={currentState:'active',addEventListener(type,listener){listeners.add(listener);return {remove(){listeners.delete(listener);}}}};
window.__taskLifecycle=value=>{AppState.currentState=value;for(const listener of listeners)listener(value);};
export const NativeModules={InkRuntime:{copyText:async()=>{}}};`;
// Native SVG geometry is emitted through a DOM-only test renderer; the actual native package is verified in Hermes.
const svg=String.raw`import React from 'react';import {StyleSheet} from 'react-native-web';
export default function NativeSvg({accessible,style,...props}){const flat=StyleSheet.flatten(style)||{};return <svg {...props} aria-hidden={accessible===false?true:undefined} style={{...flat,transform:Array.isArray(flat.transform)?flat.transform.map(value=>Object.entries(value).map(([key,arg])=>key+'('+arg+')').join(' ')).join(' '):flat.transform}}/>;}
export const Circle=props=><circle {...props}/>,Line=props=><line {...props}/>,Path=props=><path {...props}/>,Polyline=props=><polyline {...props}/>,Rect=props=><rect {...props}/>;`;
const entry=String.raw`import React from 'react';import {createRoot} from 'react-dom/client';import {TaskActivityParity} from '/e2e/native/task-activity-parity.tsx';
createRoot(document.querySelector('#root')).render(<TaskActivityParity lifecycle={value=>window.__taskLifecycle(value)}/>);`;
let server:ViteDevServer,origin:string;
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-task-navigation-20261030/cache/native',define:{__DEV__:'false'},optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','text-encoding-utf-8','web-streams-polyfill','ai','zod','react-markdown','remark-gfm','react-i18next','i18next']},resolve:{alias:[{find:/^react-native$/,replacement:'/task-platform.tsx'},{find:/^react-native-svg$/,replacement:'/task-svg.tsx'}]},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[{name:'native-task-boundaries',enforce:'pre',resolveId(id,importer){if(id==='/task-platform.tsx')return '\0task-platform';if(id==='/task-entry.tsx')return '\0task-entry';if(id==='/task-svg.tsx')return '\0task-svg';if(id==='react-native-webview')return '\0task-webview';if(id==='../../hooks/useCopy'&&importer?.includes('/components/chat/'))return root+'app/_dream/hooks/useCopy.native.ts';if(id==='./Icons'&&importer?.includes('/components/chat/'))return root+'app/_dream/components/chat/Icons.native.tsx';},async load(id){const code=id==='\0task-platform'?platform:id==='\0task-entry'?entry:id==='\0task-svg'?svg:id==='\0task-webview'?`export const WebView=()=>null;`:null;if(code)return transformWithEsbuild(code,'fixture.tsx',{loader:'tsx',jsx:'automatic'});},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/native-task-activity')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native-task-activity','<html><head><link rel="icon" href="data:,"><style>html,body,#root{margin:0;height:100%;overflow:hidden}</style></head><body><div id="root"></div><script type="module" src="/task-entry.tsx"></script></body></html>'));});}}]});
 await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('Fixture port missing');origin=`http://127.0.0.1:${address.port}`;
});
test.afterAll(async()=>{await server?.close();});
const diagnostics=new WeakMap<Page,string[]>();
test.beforeEach(async({page})=>{
 const errors:string[]=[];diagnostics.set(page,errors);page.on('pageerror',error=>errors.push(error.message));page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
 await page.addInitScript(()=>localStorage.setItem('ink-language','en'));
 await page.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();errors.push('Unexpected external request');return route.abort();});
 await page.goto(origin+'/native-task-activity');await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture?.inspection.revision??0)).toBeGreaterThan(0);
});
test.afterEach(async({page})=>{expect(diagnostics.get(page)??[]).toEqual([]);});
const panel=(page:Page)=>page.getByTestId('native-task-activity-panel');
const fixture=(page:Page)=>page.getByTestId('task-fixture-inspection');
async function open(page:Page){await page.getByRole('button',{name:'Task activity',exact:true}).click();await expect(panel(page)).toBeVisible();}
async function close(page:Page){await panel(page).getByRole('button',{name:'Close',exact:true}).click();await expect(panel(page)).toHaveCount(0);}

test('five independent sections retain original status semantics, todo collapse and current composer',async({page})=>{
 await page.getByRole('textbox',{name:'Underlying Chat draft'}).fill('Keep this unsent draft');await open(page);
 for(const name of ['Scheduled tasks','Tasks created','Subagents','Plan','To-dos'])await expect(panel(page).getByRole('heading',{name,exact:true})).toBeVisible();
 await expect(panel(page).getByRole('button',{name:'Review task 0 · Ended',exact:true})).toBeVisible();
 await expect(panel(page).getByText('Todo item 3',{exact:true})).toHaveCount(0);await panel(page).getByRole('button',{name:'Show 2 more',exact:true}).click();await expect(panel(page).getByText('Todo item 4',{exact:true})).toBeVisible();
 await panel(page).getByRole('button',{name:'Collapse',exact:true}).click();await expect(panel(page).getByText('Todo item 4',{exact:true})).toHaveCount(0);
 await expect(panel(page).getByText('Reviewer',{exact:true})).toBeVisible();await expect(panel(page).getByText('⛔ previous task',{exact:true})).toBeVisible();
 await expect(panel(page).getByRole('heading',{name:'Original plan',exact:true})).toBeVisible();
 await close(page);await expect(page.getByRole('textbox',{name:'Underlying Chat draft'})).toHaveValue('Keep this unsent draft');
 expect(await page.evaluate(()=>(window as any).__taskFixture.f.calls.every((call:any)=>call.method==='GET'))).toBe(true);
});
test('task opens its original Thread and source marker appears once above first user text or pagination boundary',async({page})=>{
 await open(page);await panel(page).getByRole('button',{name:'Review task 0 · Ended',exact:true}).click();await expect(fixture(page)).toContainText('"threadId":"child-thread"');
 const source=page.getByRole('button',{name:'Open the source conversation',exact:true});await expect(source).toHaveCount(1);await expect(source).toBeVisible();
 let sourceBox=await source.boundingBox(),userBox=await page.getByText('Original user message.',{exact:true}).boundingBox();expect(sourceBox!.y).toBeLessThan(userBox!.y);
 await page.getByRole('button',{name:'Older pages',exact:true}).click();await expect(source).toHaveCount(1);sourceBox=await source.boundingBox();userBox=await page.getByText('Original user message.',{exact:true}).boundingBox();expect(sourceBox!.y).toBeLessThan(userBox!.y);
 await source.click();await expect(fixture(page)).toContainText('"threadId":"fixture-thread"');await expect(source).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__taskFixture.f.navigation)).toEqual(['child-thread','fixture-thread']);
});
test('subagent details remain readonly, pair one tool result and suppress server-redacted payloads',async({page})=>{
 await open(page);await panel(page).getByRole('button',{name:'Open subagent task: Review subagent 1',exact:true}).click();
 await expect(panel(page).getByRole('heading',{name:'Execution details',exact:true})).toBeVisible();await expect(panel(page).getByRole('heading',{name:'Review complete',exact:true})).toBeVisible();
 const tool=panel(page).getByRole('button',{name:'Used Read · Completed',exact:true});await expect(tool).toHaveCount(1);await tool.click();
 await expect(panel(page).getByText('Sensitive fields were redacted by the server.',{exact:true})).toBeVisible();await expect(panel(page).getByText('This tool record was shortened for safe display.',{exact:true})).toBeVisible();
 await expect(panel(page).getByText('SYNTHETIC REDACTED BODY MUST STAY HIDDEN',{exact:true})).toHaveCount(0);await expect(panel(page).getByRole('button',{name:/Stop|Approve|Send/})).toHaveCount(0);
 await panel(page).getByRole('button',{name:'Back to subagent tasks',exact:true}).click();await expect(panel(page).getByRole('heading',{name:'Subagents',exact:true})).toBeVisible();await expect(panel(page).getByText('Ended · 2',{exact:true})).toBeVisible();
});
test('every existing section alone exposes the entry, empty data hides it and read failure retains last success',async({page})=>{
 for(const key of ['links','scheduled','agents','plan','todos']){await page.getByRole('button',{name:'Only '+key,exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.inspection.loading)).toBe(false);await expect(page.getByRole('button',{name:'Task activity',exact:true})).toBeVisible();}
 await page.getByRole('button',{name:'All sections',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.inspection.loading)).toBe(false);
 await page.getByRole('button',{name:'Fail plan',exact:true}).click();await expect(fixture(page)).toContainText('"failed":["plan"]');await open(page);await expect(panel(page).getByRole('heading',{name:'Original plan',exact:true})).toBeVisible();await expect(panel(page).getByRole('alert')).toContainText('Tasks could not be loaded.');await close(page);
 await page.getByRole('button',{name:'Restore reads',exact:true}).click();await expect(fixture(page)).toContainText('"failed":[]');await page.getByRole('button',{name:'Empty sections',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.inspection.loading)).toBe(false);await expect(page.getByRole('button',{name:'Task activity',exact:true})).toHaveCount(0);
});
test('a held source allows other cards to refresh and retry aborts it without losing the current draft',async({page})=>{
 await page.getByRole('textbox',{name:'Underlying Chat draft'}).fill('Pending read must retain composer');await page.getByRole('button',{name:'Hold plan',exact:true}).click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.f.pending.length)).toBe(1);await expect(fixture(page)).toContainText('Review task 1');await expect(fixture(page)).toContainText('"loading":true');await open(page);
 await expect(panel(page).getByRole('button',{name:'Refresh',exact:true})).toBeEnabled();await panel(page).getByRole('button',{name:'Refresh',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.f.pending[0].signal.aborted)).toBe(true);await close(page);
 await page.getByRole('button',{name:'Restore reads',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.inspection.loading)).toBe(false);
 await page.evaluate(()=>{for(const value of (window as any).__taskFixture.f.pending)value.release();});await expect(page.getByRole('textbox',{name:'Underlying Chat draft'})).toHaveValue('Pending read must retain composer');
});
test('Thread switch, hidden reader and background reject late reads; foreground reloads without task mutations',async({page})=>{
 await page.getByRole('button',{name:'Hold plan',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.f.pending.length)).toBe(1);
 await page.getByRole('button',{name:'Switch Thread',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.f.pending[0].signal.aborted)).toBe(true);await expect(fixture(page)).toContainText('"threadId":"child-thread"');
 await page.getByRole('button',{name:'Restore reads',exact:true}).click();await page.evaluate(()=>(window as any).__taskFixture.f.pending[0].release());await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.inspection.plan)).toBe(null);
 await page.getByRole('button',{name:'Switch Thread',exact:true}).click();await page.getByRole('button',{name:'Hold plan',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.f.pending.length)).toBeGreaterThan(1);
 await page.getByRole('button',{name:'Hide reader',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.f.pending.at(-1).signal.aborted)).toBe(true);const reads=await page.evaluate(()=>(window as any).__taskFixture.f.calls.length);
 await page.getByRole('button',{name:'Background',exact:true}).click();await expect(fixture(page)).toContainText('"foreground":false');expect(await page.evaluate(()=>(window as any).__taskFixture.f.calls.length)).toBe(reads);
 await page.getByRole('button',{name:'Restore reads',exact:true}).click();await page.getByRole('button',{name:'Show reader',exact:true}).click();expect(await page.evaluate(()=>(window as any).__taskFixture.f.calls.length)).toBe(reads);
 await page.getByRole('button',{name:'Foreground',exact:true}).click();await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.f.calls.length)).toBeGreaterThan(reads);await page.evaluate(()=>{for(const value of (window as any).__taskFixture.f.pending)value.release();});await expect.poll(()=>page.evaluate(()=>(window as any).__taskFixture.inspection.loading)).toBe(false);
 expect(await page.evaluate(()=>(window as any).__taskFixture.f.calls.every((call:any)=>call.method==='GET'))).toBe(true);
});
test('scheduled entry opens the existing detail owner and closes the task panel',async({page})=>{
 await open(page);await panel(page).getByRole('button',{name:/Morning note/}).click();await expect(panel(page)).toHaveCount(0);expect(await page.evaluate(()=>(window as any).__taskFixture.f.scheduled)).toEqual(['schedule-one']);
});
