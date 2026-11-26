// [Input] Production Chat/public/image components with identical synthetic message content and installed Chrome.
// [Output] Desktop/narrow and light/dark style parity, bounded content and settled diagram capture evidence.
// [Pos] Technical isolation: only fixture DOM and owned Vite/PNG files change; no model/account/database/Run/Hook.
import {test,expect,type Page} from '@playwright/test';
import {createServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {writeFile} from 'node:fs/promises';
let server: Awaited<ReturnType<typeof createServer>>, base: string;
const errors = new WeakMap<Page,string[]>();
test.beforeAll(async()=>{
  server=await createServer({root:fileURLToPath(new URL('../',import.meta.url)),configFile:false,cacheDir:fileURLToPath(new URL('../test-results/chat-share-layout/cache',import.meta.url)),logLevel:'silent',server:{host:'127.0.0.1',port:0},optimizeDeps:{entries:['e2e/fixtures/chat-share-layout-harness.tsx'],include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-markdown','remark-gfm','ai','zod','i18next','react-i18next','html-to-image','ajv','ajv-formats','mermaid']},plugins:[{name:'chat-share-layout',configureServer(vite){vite.middlewares.use(async(req,res,next)=>{
    if(req.url!='/chat-share-layout')return next();res.setHeader('content-type','text/html; charset=utf-8');res.end(await vite.transformIndexHtml('/chat-share-layout','<html><head><meta charset="UTF-8"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/e2e/fixtures/chat-share-layout-harness.tsx"></script></body></html>'));
  });}}]});await server.listen();base=server.resolvedUrls!.local[0];
});
test.afterAll(async()=>{await server?.close();});
test.beforeEach(async({page})=>{
  const collected:string[]=[];errors.set(page,collected);page.on('pageerror',error=>collected.push(error.message));page.on('console',message=>{if(message.type()==='error')collected.push(message.text());});
  page.on('requestfailed',request=>{if(request.failure()?.errorText!=='net::ERR_ABORTED')collected.push(request.url());});
  await page.goto(base+'chat-share-layout');await expect(page.getByTestId('reference').locator('.prose')).toHaveCount(2);
});
test.afterEach(async({page})=>{expect(errors.get(page)).toEqual([]);});
async function appearance(page:Page,scope:string,index:number){return page.getByTestId(scope).locator('.prose').nth(index).evaluate(node=>{
  const prose=getComputedStyle(node),frame=getComputedStyle(node.parentElement!),outer=getComputedStyle(node.parentElement!.parentElement!);
  return {font:prose.fontFamily,fontSize:prose.fontSize,lineHeight:prose.lineHeight,color:prose.color,background:frame.backgroundColor,padding:frame.padding,borderRadius:frame.borderRadius,maxWidth:frame.maxWidth,align:outer.alignItems};
});}
for(const width of [1200,390])for(const theme of ['Light','Dark'])test(`Chat message parity at ${width}px ${theme}`,async({page},testInfo)=>{
  await page.setViewportSize({width,height:900});await page.getByRole('button',{name:theme,exact:true}).click();
  for(const scope of ['reference','public','image'])await expect(page.getByTestId(scope).locator('.katex')).toHaveCount(1);
  for(const index of [0,1])for(const scope of ['public','image'])expect(await appearance(page,scope,index)).toEqual(await appearance(page,'reference',index));
  await expect(page.getByTestId('public').getByRole('button',{name:'Delete',exact:true})).toHaveCount(0);
  await expect(page.getByTestId('public').getByRole('button',{name:'Regenerate',exact:true})).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  expect(await page.getByTestId('image').locator('.prose pre').evaluate(node=>node.scrollWidth<=node.clientWidth&&node.scrollHeight<=node.clientHeight&&getComputedStyle(node).overflow==='hidden')).toBe(true);
  await page.screenshot({path:testInfo.outputPath('chat-share-layout.png'),fullPage:true});
});
for(const invalid of [false,true])test(`PNG capture waits for Mermaid ${invalid?'source fallback':'render'}`,async({page},testInfo)=>{
  await page.getByRole('button',{name:invalid?'Capture invalid diagram':'Capture PNG',exact:true}).click();
  const preview=page.getByTestId('png').getByRole('img');await expect(preview).toBeVisible({timeout:60_000});
  const size=await preview.evaluate(async node=>{const image=node as HTMLImageElement;await image.decode();return {width:image.naturalWidth,height:image.naturalHeight};});expect(size.width).toBe(2160);expect(size.height).toBeGreaterThan(100);
  await expect(page.getByTestId('capture-state')).toHaveText(invalid?'failed:false':'ready:true');
  expect(await page.locator('.chat-share-image [data-render-state="pending"]').count()).toBe(0);
  const bytes=await preview.evaluate(async node=>Array.from(new Uint8Array(await(await fetch((node as HTMLImageElement).src)).arrayBuffer())));
  await writeFile(testInfo.outputPath('chat-share.png'),Buffer.from(bytes));
});
