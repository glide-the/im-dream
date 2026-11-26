// [Sync] 2026-11-13: prove zero Chat connection PATCH, Thread selection isolation and desktop Agent cascade.
// [Input] Production component fixture, strict synthetic HTTP receipts and installed local Chrome.
// [Output] User-journey assertions for Agent/tool selection, revision conflicts, drafts and responsive panels.
// [Pos] Provider-free technical validation; changes only fixture configuration and component state.
// [Sync] 2026-11-13: native scene return refreshes preferences saved through the existing HTTP boundary.
// Impact: Chat menu/presentation changes. Thread/send callback semantics remain. Project/Episode/canonical
// Artifact/Run-private publication/after-turn Hook/PostgreSQL/API materialization are outside this fixture.
import {test,expect,type Page} from '@playwright/test';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {installComposerApi,type ComposerApiOptions} from './fixtures/chatComposerApi';
let server:Awaited<ReturnType<typeof createServer>>,base:string;
const errors=new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
  server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,cacheDir:fileURLToPath(new URL('../output/chat-tools-20261113/vite',import.meta.url)),logLevel:'silent',define:{__DEV__:'false'},resolve:{alias:[{find:/^react-native$/,replacement:fileURLToPath(new URL('./native/reflections-platform-web-boundary.ts',import.meta.url))},{find:/^react-native-svg$/,replacement:fileURLToPath(new URL('./native/svg-web-boundary.tsx',import.meta.url))}]},server:{host:'127.0.0.1',port:0},plugins:[{name:'chat-tools-fixture',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!='/chat-tools')return next();res.setHeader('content-type','text/html; charset=utf-8');res.end(await vite.transformIndexHtml('/chat-tools','<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/chat-tools-harness.tsx"></script></body></html>'));});}}]});
  await server.listen();base=server.resolvedUrls!.local[0];
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
  const messages:string[]=[];errors.set(page,messages);page.on('pageerror',error=>messages.push(error.message));
  page.on('requestfailed',request=>{if(request.failure()?.errorText!=='net::ERR_ABORTED')messages.push(request.url());});
});
test.afterEach(async({page})=>{expect(errors.get(page)).toEqual([]);});
async function open(page:Page,options:ComposerApiOptions={}){
  const api=await installComposerApi(page,options);
  await page.goto(base+'chat-tools');await expect(page.getByRole('textbox',{name:'Chat input'})).toBeVisible();
  await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Alpha');
  return api;
}
test('Agent, tool mode and draft use the original send boundary',async({page})=>{
  await open(page);const input=page.getByRole('textbox',{name:'Chat input'});await input.fill('Keep this draft');
  await expect(page.getByRole('button',{name:'Tools',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Select an Agent for this conversation'})).toHaveCount(0);await page.getByRole('button',{name:/^Agent and tools:/}).click();await page.getByRole('button',{name:'Select Agent',exact:true}).click();await page.getByPlaceholder('Filter Kastention or Agents…').fill('Wri');await page.getByRole('option',{name:'Writer',exact:false}).click();
  await page.getByRole('button',{name:/^Agent and tools:/}).click();const panel=page.getByRole('dialog',{name:'Agent & tools'});await expect(panel.getByRole('switch',{name:'Research library'})).not.toBeChecked();
  await panel.getByRole('radio',{name:'Confirm each step',exact:true}).check();await page.keyboard.press('Escape');await expect(panel).toHaveCount(0);await expect(input).toHaveText('Keep this draft');
  await page.getByRole('button',{name:'Send message',exact:true}).click();await expect(page.getByTestId('sent')).toHaveText(JSON.stringify({message:'Keep this draft',mode:'manual',agent:'fixture-agent'}));
  await page.getByRole('button',{name:'Toggle running'}).click();await expect(page.getByRole('button',{name:'Stop generating'})).toBeVisible();await input.fill('Next message');await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeVisible();
});
test('MCP switches belong to the Thread, enter Chat tools, and never PATCH the resource connection',async({page})=>{
  const {mcpPatches}=await open(page);const trigger=()=>page.getByRole('button',{name:/^Agent and tools:/}),toggle=()=>page.getByRole('switch',{name:'Research library'});
  await trigger().click();await expect(toggle()).not.toBeChecked();await toggle().click();await expect(toggle()).toBeChecked();await page.keyboard.press('Escape');
  await page.getByRole('textbox',{name:'Chat input'}).fill('Use the selected tools');await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect.poll(async()=>JSON.parse(await page.getByTestId('request').innerText()).tools).toEqual([{type:'mcp',server_name:'research'}]);
  await page.getByRole('button',{name:'Thread B',exact:true}).click();await trigger().click();await expect(toggle()).not.toBeChecked();await page.keyboard.press('Escape');
  await page.getByRole('textbox',{name:'Chat input'}).fill('This conversation has no selected tools');await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect.poll(async()=>JSON.parse(await page.getByTestId('request').innerText()).tools).toEqual([]);
  await page.getByRole('button',{name:'Thread A',exact:true}).click();await trigger().click();await expect(toggle()).toBeChecked();await toggle().click();await page.keyboard.press('Escape');
  await trigger().click();await expect(toggle()).not.toBeChecked();await page.keyboard.press('Escape');
  await page.getByRole('button',{name:'Toggle resources',exact:true}).click();await expect(page.getByRole('switch',{name:'启用 Research library'})).toBeChecked();expect(mcpPatches).toEqual([]);
});
test('desktop Agent submenu opens beside the grouped menu by pointer and keyboard',async({page},info)=>{
  await page.setViewportSize({width:1200,height:850});await open(page);await page.getByRole('button',{name:/^Agent and tools:/}).click();
  const row=page.getByRole('button',{name:'Select Agent',exact:true});await row.hover();const submenu=page.locator('.composer-agent-flyout');await expect(submenu.getByRole('option',{name:/Writer/})).toBeVisible();
  const a=await row.boundingBox(),b=await submenu.boundingBox();expect(b!.x).toBeGreaterThan(a!.x+a!.width);expect(b!.x+b!.width).toBeLessThanOrEqual(1200);expect(b!.y+b!.height).toBeLessThanOrEqual(850);
  await page.screenshot({path:info.outputPath('agent-cascade.png'),fullPage:true});
  await page.keyboard.press('ArrowLeft');await expect(submenu).toHaveCount(0);await expect(row).toBeFocused();
  await page.keyboard.press('ArrowRight');await expect(submenu).toBeVisible();await submenu.getByRole('option',{name:/Writer/}).click();await expect(page.getByRole('button',{name:'Agent and tools: Writer',exact:true})).toBeVisible();
});
test('a disabled managed connection cannot be enabled from Chat',async({page})=>{
  const {mcpPatches}=await open(page,{connectionEnabled:false});await page.getByRole('button',{name:/^Agent and tools:/}).click();await expect(page.getByRole('switch',{name:'Research library'})).toBeDisabled();expect(mcpPatches).toEqual([]);
});
test('failed list recovers without clearing the input',async({page})=>{
  await open(page,{readFailure:true});const input=page.getByRole('textbox',{name:'Chat input'});await input.fill('Retained text');await page.getByRole('button',{name:/^Agent and tools:/}).click();const panel=page.getByRole('dialog',{name:'Agent & tools'});
  await expect(panel.getByRole('alert')).toBeVisible();await expect(panel.getByText('No services configured')).toHaveCount(0);await panel.getByRole('button',{name:'Retry',exact:true}).click();await expect(panel.getByRole('switch',{name:'Research library'})).toBeVisible();await page.keyboard.press('Escape');await expect(input).toHaveText('Retained text');
});
for(const width of [390,1200])for(const dark of [false,true])test(`tools and cards fit ${width}px ${dark?'dark':'light'}`,async({page},info)=>{
  await page.setViewportSize({width,height:850});await open(page);if(dark)await page.getByRole('button',{name:'Dark',exact:true}).click();
  await page.getByRole('button',{name:/^Agent and tools:/}).click();const panel=page.getByRole('dialog',{name:'Agent & tools'});await expect(panel.getByRole('switch',{name:'Research library'})).toBeVisible();
  const bounds=await panel.boundingBox();expect(bounds!.x).toBeGreaterThanOrEqual(0);expect(bounds!.y).toBeGreaterThanOrEqual(0);expect(bounds!.x+bounds!.width).toBeLessThanOrEqual(width);await expect(panel.getByText('Available in the App')).toBeVisible();
  await page.screenshot({path:info.outputPath('chat-tools.png'),fullPage:true});await page.keyboard.press('Escape');await page.getByRole('button',{name:'Toggle resources'}).click();
  await expect(page.getByRole('switch',{name:'启用 Research library'})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath('resource-cards.png'),fullPage:true});
});

test('migrated model picker searches IM catalog, disables unavailable entries and saves only the existing model field',async({page})=>{
  const api=await open(page);const input=page.getByRole('textbox',{name:'Chat input'});await input.fill('Keep model draft');
  await page.getByTestId('model-selector-button').click();const menu=page.getByRole('dialog',{name:'Select model',exact:true});
  await expect(menu.getByRole('option',{name:/IM Unavailable Model/})).toBeDisabled();
  await menu.getByRole('combobox').fill('Beta');await expect(menu.getByRole('option')).toHaveCount(1);await page.keyboard.press('Enter');
  await expect(menu).toHaveCount(0);await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Beta');
  await expect.poll(()=>api.modelPatches).toEqual([{model:'fixture-model-b'}]);await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeEnabled();
  await expect(input).toHaveText('Keep model draft');await page.getByRole('button',{name:'Send message',exact:true}).click();
  await expect(page.getByTestId('sent')).toHaveText(JSON.stringify({message:'Keep model draft',mode:'auto'}));
});

test('unconfirmed IM model save blocks send until explicit config reread without resubmitting the save',async({page})=>{
  const api=await open(page,{modelFailure:503,modelAppliedOnFailure:true});const input=page.getByRole('textbox',{name:'Chat input'});await input.fill('Retain on uncertain save');
  await page.getByTestId('model-selector-button').click();await page.getByRole('dialog',{name:'Select model',exact:true}).getByRole('option',{name:/IM Model Beta/}).click();
  await expect(page.getByRole('alert')).toContainText('未确认');await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeDisabled();await expect(input).toHaveText('Retain on uncertain save');
  await page.getByRole('button',{name:'Reload models',exact:true}).click();await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Beta');await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeEnabled();expect(api.modelPatches).toEqual([{model:'fixture-model-b'}]);
});

test('model catalog error offers reread while preserving ordinary Chat editing and sending',async({page})=>{
  await installComposerApi(page,{catalogFailure:true});await page.goto(base+'chat-tools');await expect(page.getByRole('alert')).toBeVisible();
  const input=page.getByRole('textbox',{name:'Chat input'});await input.fill('Catalog recovery draft');await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Reload models',exact:true}).click();await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Alpha');await expect(input).toHaveText('Catalog recovery draft');
});

for(const width of [390,1200])test(`migrated model popover or sheet fits ${width}px with a long model label`,async({page},info)=>{
  await page.setViewportSize({width,height:850});await open(page);await page.getByTestId('model-selector-button').click();const menu=page.getByRole('dialog',{name:'Select model',exact:true});
  await expect(menu.getByRole('option',{name:/IM Model Alpha/})).toBeVisible();const box=await menu.boundingBox();expect(box!.x).toBeGreaterThanOrEqual(0);expect(box!.y).toBeGreaterThanOrEqual(0);expect(box!.x+box!.width).toBeLessThanOrEqual(width);
  if(width===390)await expect(menu).toHaveAttribute('aria-modal','true');await page.screenshot({path:info.outputPath('model-menu.png'),fullPage:true});
  await menu.getByRole('option',{name:/IM Model Beta/}).click();await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Beta');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('native action row uses one current-Agent menu and saves the model through original IM HTTP',async({page},info)=>{
  await page.setViewportSize({width:390,height:850});const api=await installComposerApi(page);await page.goto(base+'chat-tools?native=1');await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Alpha');
  await expect(page.getByRole('button',{name:'Tools',exact:true})).toHaveCount(0);await page.getByRole('button',{name:/^Agent and tools:/}).click();await page.getByRole('button',{name:'Select Agent ›',exact:true}).click();await page.getByRole('radio',{name:'Writer',exact:true}).click();
  await expect(page.getByRole('button',{name:'Agent and tools: Writer',exact:true})).toBeVisible();await page.getByTestId('model-selector-button').click();await expect(page.getByRole('radio',{name:'IM Unavailable Model',exact:true})).toBeDisabled();await page.getByRole('radio',{name:'IM Model Beta with a longer label',exact:true}).click();
  await expect.poll(()=>api.modelPatches).toEqual([{model:'fixture-model-b'}]);await expect(page.getByTestId('native-model-saves')).toHaveText('1');await expect(page.getByRole('radio',{name:'IM Model Alpha',exact:true})).toHaveCount(0);await expect(page.getByRole('button',{name:'Send message',exact:true})).toBeEnabled();await expect(page.getByRole('textbox',{name:'Native draft'})).toHaveValue('Retained native draft');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:info.outputPath('native-agent-model.png'),fullPage:true});
});

test('native model selection closes when the owning scene becomes inactive',async({page})=>{
  await installComposerApi(page);await page.goto(base+'chat-tools?native=1');await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Alpha');await page.getByTestId('model-selector-button').click();await expect(page.getByRole('radio',{name:'IM Model Alpha',exact:true})).toBeVisible();
  await page.evaluate(()=>document.querySelector<HTMLButtonElement>('main>button')!.click());await expect(page.getByRole('radio',{name:'IM Model Alpha',exact:true})).toHaveCount(0);
  // Stage a preference saved in another surface through the existing intercepted HTTP contract.
  await page.evaluate(()=>fetch('/api/system-config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'fixture-model-b'})}));
  await page.getByRole('button',{name:'Toggle native scene',exact:true}).click();
  await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Beta');
  await expect(page.getByRole('textbox',{name:'Native draft'})).toHaveValue('Retained native draft');
});

test('an empty running turn retains the original Stop action while model save is unconfirmed',async({page})=>{
  await open(page,{modelFailure:503});await page.getByRole('button',{name:'Toggle running',exact:true}).click();await page.getByTestId('model-selector-button').click();await page.getByRole('dialog',{name:'Select model',exact:true}).getByRole('option',{name:/IM Model Beta/}).click();
  await expect(page.getByRole('alert')).toContainText('未确认');await expect(page.getByRole('button',{name:'Stop generating',exact:true})).toBeEnabled();await page.getByRole('button',{name:'Stop generating',exact:true}).click();await expect(page.getByRole('button',{name:'Stop generating',exact:true})).toHaveCount(0);
});

test('model permission rejection retains the saved choice and permits another explicit selection',async({page})=>{
  const api=await open(page,{modelFailure:403});await page.getByTestId('model-selector-button').click();await page.getByRole('dialog',{name:'Select model',exact:true}).getByRole('option',{name:/IM Model Beta/}).click();await expect(page.locator('.model-selector [role=status]')).toContainText('没有此模型');await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Alpha');
  await page.getByTestId('model-selector-button').click();await page.getByRole('dialog',{name:'Select model',exact:true}).getByRole('option',{name:/IM Model Beta/}).click();await expect(page.getByTestId('model-selector-button')).toBeEnabled();await expect(page.getByTestId('model-selector-button')).toContainText('IM Model Beta');expect(api.modelPatches).toEqual([{model:'fixture-model-b'},{model:'fixture-model-b'}]);
});
