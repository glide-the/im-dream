// [Input] Real production Web/Native message components, installed Chrome and a WebView transport facade.
// [Output] Formula, layout, source-copy, stream/history, native document and Markdown regression evidence.
// [Pos] Provider-free browser qualification. All business data, Project/Episode/artifacts/Run/Hook are out of scope.
// [Sync] 2026-11-08: freeze fixture dependency discovery and deduplicate React for clean worktree startup.
// [Sync] 2026-11-08: keep synthetic data and an owned ephemeral Vite server; no existing service changes.
import {test,expect,type Page} from '@playwright/test';
import {createServer,transformWithEsbuild,type ViteDevServer} from 'vite';
import {fileURLToPath} from 'node:url';
import {mkdtemp,rm,mkdir,readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import type {MathViewControl} from './chat-math.harness';

const root=fileURLToPath(new URL('../',import.meta.url));
test.use({channel:'chrome',viewport:{width:1100,height:800}});
let server:ViteDevServer,origin:string,runtime:string;
const native=`export * from ${JSON.stringify(root+'e2e/native/appearance-platform-web-boundary.ts')};export const NativeEventEmitter=class{addListener(){return{remove(){}}}};export const NativeModules={InkRuntime:{}};`;
// Only the platform WebView transport is substituted. Its HTML, CSP, MathML, sizing script and copy projection are production source.
const webview=String.raw`import React,{useEffect,useRef} from 'react';
export function WebView(props){const frame=useRef(null),latest=useRef(props);latest.current=props;
 const html=props.source.html,id=html.match(/nonce="([^"]+)"/)[1];
 const bridge='<script nonce="'+id+'">window.ReactNativeWebView={postMessage:data=>parent.postMessage({mathDocument:data},"*")}</script>';
 useEffect(()=>{const receive=event=>{if(event.source===frame.current?.contentWindow&&event.data?.mathDocument)latest.current.onMessage?.({nativeEvent:{url:'about:blank',data:event.data.mathDocument}});};window.addEventListener('message',receive);const views=window.__mathViews??={};views[id]={props:latest,fail:()=>latest.current.onError?.()};return()=>{window.removeEventListener('message',receive);delete views[id];};},[id]);
 return <iframe title="Native math text" ref={frame} srcDoc={html.replace('<head>','<head>'+bridge)} style={{width:'100%',height:'100%',border:0,background:'transparent'}} onLoad={()=>{const doc=frame.current?.contentDocument;doc?.addEventListener('click',event=>{const link=event.target.closest('a');if(link){event.preventDefault();latest.current.onShouldStartLoadWithRequest?.({url:link.getAttribute('href')});}});}}/>;
}`;
test.beforeAll(async()=>{
  runtime=await mkdtemp(path.join(tmpdir(),'ink-chat-math-'));
  server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:path.join(runtime,'cache'),resolve:{dedupe:['react','react-dom']},optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','i18next','react-i18next','react-markdown','remark-gfm','katex','mermaid']},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[{
    name:'chat-math-platform-boundaries',enforce:'pre',
    resolveId(id,importer){if(id==='react-native')return '\0math-native';if(id==='react-native-webview')return '\0math-webview';if(id.endsWith('/interfaceSettings')&&importer&&!importer.endsWith('interfaceSettings.ios.ts'))return root+'src/platform/interfaceSettings.ios.ts';},
    async load(id){if(id==='\0math-native')return native;if(id==='\0math-webview')return transformWithEsbuild(webview,'math-webview.tsx',{loader:'tsx',jsx:'automatic'});},
    configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url!=='/math-fixture')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/math-fixture','<html><head><link rel="icon" href="data:,"><style>html,body{margin:0;max-width:100%;background:var(--color-bg-app);color:var(--color-text-body)}main{padding:16px;min-width:0}textarea{display:block;width:100%;height:70px;box-sizing:border-box}nav{display:flex;flex-wrap:wrap}section{min-width:0;margin-block:12px}*{box-sizing:border-box}</style></head><body><div id="root"></div><script type="module" src="/e2e/chat-math.harness.tsx"></script></body></html>'));});},
  }]});
  await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('Missing fixture port');origin=`http://127.0.0.1:${address.port}`;
});
test.afterAll(async()=>{await server?.close();if(runtime)await rm(runtime,{recursive:true,force:true});});
const diagnostics=new WeakMap<Page,string[]>();
test.beforeEach(async({page})=>{
  diagnostics.set(page,[]);page.on('pageerror',error=>diagnostics.get(page)!.push(error.message));
  page.on('console',message=>{if(message.type()==='error')diagnostics.get(page)!.push(message.text()+' ['+message.location().url+']');});
  await page.addInitScript(()=>{localStorage.setItem('ink-language','en');Object.defineProperty(navigator,'clipboard',{value:{writeText:async(text:string)=>{window.__mathCopied=text;}}});});
  await page.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
});
test.afterEach(async({page})=>{expect(diagnostics.get(page)).toEqual([]);});
async function open(page:Page,text?:string){await page.goto(origin+'/math-fixture');await expect(page.getByLabel('Message source')).toBeVisible();if(text!==undefined)await page.getByLabel('Message source').fill(text);}
async function source(page:Page,text:string){await page.getByLabel('Message source').fill(text);}
async function copiedSelection(page:Page,partial=false){return page.locator('#web-assistant .chat-markdown').evaluate((element,partial)=>{
  const range=document.createRange();if(partial){const visual=element.querySelector('.katex-html')!;const walker=document.createTreeWalker(visual,NodeFilter.SHOW_TEXT);const text=walker.nextNode()!;range.setStart(text,0);range.setEnd(text,1);}else range.selectNodeContents(element);
  const selection=getSelection()!;selection.removeAllRanges();selection.addRange(range);const data=new DataTransfer();const event=new ClipboardEvent('copy',{bubbles:true,cancelable:true,clipboardData:data});element.dispatchEvent(event);return {text:data.getData('text/plain'),html:data.getData('text/html'),prevented:event.defaultPrevented};
},partial);}

test('user and assistant messages render inline/display math and keep exact whole-message copy',async({page})=>{
  const text=String.raw`Text \(x^2\), then \(y_1\).

\[\frac{1}{2}\]

$$E=mc^2$$`;
  await open(page,text);
  for(const section of ['#web-user','#web-assistant']){
    await expect(page.locator(section+' .katex')).toHaveCount(4);await expect(page.locator(section+' .katex-display')).toHaveCount(2);
    await page.locator(section).getByRole('button',{name:'Copy',exact:true}).click();await expect.poll(()=>page.evaluate(()=>window.__mathCopied)).toBe(text);
  }
  const projection=await copiedSelection(page);expect(projection.prevented).toBe(true);expect(projection.text).toContain('Text \\(x^2\\), then \\(y_1\\).');expect(projection.text).toContain('$$E=mc^2$$');expect(projection.html).not.toContain('katex');
  const partial=await copiedSelection(page,true);expect(partial.text).toBe(String.raw`\(x^2\)`);
});
test('money, escapes, code, tables, links and Mermaid preserve existing behavior',async({page})=>{
  const text='Price $5 and $10; $x$; escaped \\\\(plain\\\\).\n\n`\\(code\\)`\n\n```tex\n\\[literal\\]\n$$literal$$\n```\n\n| Name | Value |\n|---|---|\n| A | \\(x\\) |\n\n[Docs](https://example.test/docs) [Unsafe](javascript:alert%281%29)\n\n```mermaid\nflowchart LR\n A[Start] --> B[Finish]\n```';
  await open(page,text);const assistant=page.locator('#web-assistant');await expect(assistant.locator('.katex')).toHaveCount(1);await expect(assistant.locator('pre code.language-tex')).toContainText('$$literal$$');await expect(assistant.locator('table')).toContainText('A');await expect(assistant.getByRole('link',{name:'Docs'})).toHaveAttribute('href','https://example.test/docs');expect(await assistant.getByRole('link',{name:'Unsafe'}).getAttribute('href')).not.toContain('javascript:');
  await expect(assistant.locator('.markdown-media-block__preview svg')).toBeVisible();await assistant.getByRole('button',{name:'Source',exact:true}).click();await expect(assistant.locator('.markdown-media-block__content code')).toContainText('A[Start]');
});
test('stream, stop, error, corrected syntax and historical remount use the final source snapshot',async({page})=>{
  await open(page,String.raw`Result \(\frac{1}{`);await page.getByRole('button',{name:'Stream',exact:true}).click();await expect(page.locator('#web-assistant .katex')).toHaveCount(0);await expect(page.locator('#web-assistant')).toContainText(String.raw`\(\frac{1}{`);
  await page.getByRole('button',{name:'Stop',exact:true}).click();await expect(page.getByLabel('Message state')).toHaveText('stopped');await expect(page.locator('#web-assistant')).toContainText(String.raw`\(\frac{1}{`);
  await source(page,String.raw`Result \(\frac{1}{2}\)`);await expect(page.locator('#web-assistant .katex')).toHaveCount(1);
  await source(page,String.raw`Result \(\unknown{x}\). Next \(y\)`);await expect(page.locator('#web-assistant .katex')).toHaveCount(1);await expect(page.locator('#web-assistant')).toContainText(String.raw`\unknown{x}`);
  await page.getByRole('button',{name:'Show error',exact:true}).click();await expect(page.getByLabel('Message state')).toHaveText('error');await expect(page.locator('#web-assistant .katex')).toHaveCount(1);
  await source(page,String.raw`Result \(x\). Next \(y\)`);await page.getByRole('button',{name:'Reload history',exact:true}).click();await expect(page.locator('#web-assistant .katex')).toHaveCount(2);await page.getByRole('button',{name:'Toggle message',exact:true}).click();await expect(page.locator('#messages')).toHaveCount(0);await page.getByRole('button',{name:'Toggle message',exact:true}).click();await expect(page.locator('#web-assistant .katex')).toHaveCount(2);
});
test('long formulas remain horizontally reachable on desktop/narrow screens in both themes',async({page})=>{
  const long=Array.from({length:70},(_,index)=>`x_{${index}}`).join('+');await open(page,'Before \\('+long+'\\) after.\n\n\\['+long+'\\]');
  for(const width of [1100,390]){
    await page.setViewportSize({width,height:800});
    for(const theme of ['light','dark']){
      if(theme==='dark')await page.getByRole('button',{name:'Theme: light',exact:true}).click();
      if(theme==='light'&&width===390){await page.getByRole('button',{name:'Theme: dark',exact:true}).click();await page.getByRole('button',{name:'Theme: system',exact:true}).click();}
      await expect(page.locator('#web-assistant .katex')).toHaveCount(2);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
      for(const math of await page.locator('#web-assistant .chat-math').all()){
        expect(await math.evaluate(element=>element.scrollWidth>element.clientWidth)).toBe(true);await math.evaluate(element=>{element.scrollLeft=element.scrollWidth;});expect(await math.evaluate(element=>element.scrollLeft)).toBeGreaterThan(0);
      }
      const colors=await page.locator('#web-assistant .chat-math .katex').first().evaluate(element=>[getComputedStyle(element).color,getComputedStyle(element.closest('#web-assistant')!.querySelector('.prose')!).color]);expect(colors[0]).toBe(colors[1]);
      const background=await page.locator('body').evaluate(element=>getComputedStyle(element).backgroundColor);
      await expect.poll(()=>page.frameLocator('#native iframe').first().locator('body').evaluate(element=>getComputedStyle(element).backgroundColor)).toBe(background);
      await mkdir(path.join(root,'output/playwright/chat-math'),{recursive:true});await page.screenshot({path:path.join(root,`output/playwright/chat-math/${width}-${theme}.png`)});
    }
  }
  const scroll=page.locator('#messages');await scroll.evaluate(element=>{element.scrollTop=30;});expect(await scroll.evaluate(element=>element.scrollTop)).toBeGreaterThan(0);
});
test('native paragraphs use real MathML, bounded local scrolling, safe links and matching height updates',async({page})=>{
  await page.setViewportSize({width:390,height:800});const long=Array.from({length:45},(_,index)=>`x_{${index}}`).join('+');
  await open(page,'Native **bold \\(x^2\\)** and [Docs](https://example.test/docs), [File](workspace://files/note.md), [Bad](javascript:alert%281%29).\nSecond native line.\n\n\\['+long+'\\]');
  await expect(page.locator('#native iframe')).toHaveCount(2);
  const frame=page.frameLocator('#native iframe').first();await expect(frame.locator('math')).toHaveCount(1);await frame.getByRole('link',{name:'Docs'}).click();await expect.poll(()=>page.evaluate(()=>window.__mathLinks)).toEqual(['https://example.test/docs']);await frame.getByRole('link',{name:'File'}).click();await expect.poll(()=>page.evaluate(()=>window.__mathWorkspaceLinks)).toEqual(['workspace://files/note.md']);await frame.getByRole('link',{name:'Bad'}).click();expect(await page.evaluate(()=>window.__mathLinks)).toEqual(['https://example.test/docs']);
  const selection=await frame.locator('#content').evaluate(element=>{const range=document.createRange();range.selectNodeContents(element);const selection=getSelection()!;selection.removeAllRanges();selection.addRange(range);const data=new DataTransfer();element.dispatchEvent(new ClipboardEvent('copy',{bubbles:true,cancelable:true,clipboardData:data}));return data.getData('text/plain');});expect(selection).toContain(String.raw`\(x^2\)`);expect(selection).toContain('Docs');
  const newline=await frame.locator('#content').evaluate(element=>{const walker=document.createTreeWalker(element,NodeFilter.SHOW_TEXT);let node:Node|null;while((node=walker.nextNode())){const value=node.textContent??'',index=value.indexOf('Second native line.');if(index>=0){const line=document.createRange();line.setStart(node,index);line.setEnd(node,index+6);const first=document.createRange();first.setStart(element.firstChild!,0);first.setEnd(element.firstChild!,6);return line.getBoundingClientRect().top>first.getBoundingClientRect().top;}}return false;});expect(newline).toBe(true);
  const display=page.frameLocator('#native iframe').nth(1).locator('.chat-math');expect(await display.evaluate(element=>element.scrollWidth>element.clientWidth)).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  const height=await page.locator('#native [data-testid="native-chat-math"]').first().evaluate(element=>element.getBoundingClientRect().height);expect(height).toBeGreaterThan(26.6);
  await page.evaluate(()=>{for(const view of Object.values(window.__mathViews??{}) as MathViewControl[])view.props.current.onMessage({nativeEvent:{url:'about:blank',data:JSON.stringify({type:'height',id:'stale',height:9999})}});});expect(await page.locator('#native [data-testid="native-chat-math"]').first().evaluate(element=>element.getBoundingClientRect().height)).toBe(height);
  await page.getByRole('button',{name:'Fail native document',exact:true}).click();await expect(page.locator('#native iframe')).toHaveCount(0);await expect(page.locator('#native')).toContainText(String.raw`\(x^2\)`);await source(page,String.raw`Recovered \(y^2\)`);await expect(page.locator('#native iframe')).toHaveCount(1);await expect(page.frameLocator('#native iframe').locator('math')).toHaveCount(1);
});
test('native headings, tasks and table cells keep math in their existing text structures',async({page})=>{
  await open(page,'## Heading \\(h\\)\n\n- [x] Done \\(x\\)\n\n| Value |\n|---|\n| \\(z\\) |');
  await expect(page.locator('#native iframe')).toHaveCount(3);
  await expect(page.frameLocator('#native iframe').nth(1).locator('#content')).toContainText('☑');
  for(let index=0;index<3;index++)await expect(page.frameLocator('#native iframe').nth(index).locator('math')).toHaveCount(1);
});
test('math module failure retains source and message actions',async({page})=>{
  const failed=page.waitForEvent('requestfailed',request=>/katex.*\.(?:m?js)(?:\?|$)/.test(request.url()));
  await page.route(/katex.*\.(?:m?js)(?:\?|$)/,route=>route.abort('failed'));
  await open(page,String.raw`Readable \(x^2\)`);await failed;await expect(page.locator('#web-assistant')).toContainText(String.raw`\(x^2\)`);await expect(page.locator('#web-assistant .katex')).toHaveCount(0);await page.locator('#web-assistant').getByRole('button',{name:'Copy',exact:true}).click();await expect.poll(()=>page.evaluate(()=>window.__mathCopied)).toBe(String.raw`Readable \(x^2\)`);
  diagnostics.set(page,(diagnostics.get(page)??[]).filter(value=>!(value.includes('katex')&&(value.includes('Failed to load resource: net::ERR_FAILED')||value.includes('Failed to fetch dynamically imported module')))));
});
test('the formal interaction sequences and state diagram parse with the installed Mermaid',async({page})=>{
  await open(page);
  const doc=await readFile(path.join(root,'../docs/design/claude-agent/chat-math-messages.md'),'utf8');
  const diagrams=[...doc.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(match=>match[1]);
  expect(diagrams).toHaveLength(4);
  for(const diagram of diagrams)expect(await page.evaluate(source=>window.__mathParseDiagram(source),diagram)).toBeTruthy();
});
