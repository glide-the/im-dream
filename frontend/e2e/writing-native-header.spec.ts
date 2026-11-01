// [Input] Production WritingView.native and explicit existing RNW/SVG/WebView test boundaries.
// [Output] Header loading/current value, open intent, stale identity/revision rejection and reload reset evidence.
// [Pos] Provider-free native component browser qualification; Hermes, WKWebView, Android WebView and physical touch remain separate.
// Impact: chooser display messages only; original Editor persistence, auth/permissions, Project/Episode/artifacts/Run/Hook and models are out of scope.
import {expect,test} from '@playwright/test';
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const entry=`
import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import Writing from '/app/_dream/components/WritingView.native.tsx';
import i18n from '/app/_dream/i18n.ts';import {initTheme} from '/app/_dream/utils/theme.native.ts';
import '/app/_dream/styles/tokens.css';import '/app/_dream/index.css';
window.__settingsFixture={uuidCalls:[]};await i18n.changeLanguage('en');initTheme();
window.__headerFixture={back:0};
function Harness(){const [active,setActive]=useState(true);return <div style={{height:'100dvh',display:'flex',flexDirection:'column'}}><button onClick={()=>setActive(value=>!value)}>Toggle active</button><Writing origin={location.origin} active={active} onBack={()=>window.__headerFixture.back++} onOpenThread={()=>{}} onPrepareChat={()=>{}} onOpenResources={()=>{}} onSessionExpired={()=>{}}/></div>}
createRoot(document.querySelector('#root')).render(<Harness/>);
`;
let server:Awaited<ReturnType<typeof createServer>>,base:string;
test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-writing-mobile-implementation-20261101/vite-header',define:{__DEV__:'false'},optimizeDeps:{noDiscovery:true,include:['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','react-native-svg','react-native-svg/lib/module/elements.web.js','i18next','react-i18next']},resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/reflections-platform-web-boundary.ts'},{find:/^react-native-svg$/,replacement:root+'e2e/native/svg-web-boundary.tsx'},{find:/^react-native-webview$/,replacement:root+'e2e/native/writing-webview-boundary.tsx'}]},server:{host:'127.0.0.1',port:0,strictPort:true},plugins:[{name:'writing-header-fixture',enforce:'pre',resolveId(id,importer){if(id==='/writing-header-entry.tsx')return '\0writing-header-entry';if(id.endsWith('/interfaceSettings')&&importer&&!importer.endsWith('interfaceSettings.ios.ts'))return root+'src/platform/interfaceSettings.ios.ts';},async load(id){if(id==='\0writing-header-entry')return(await transformWithEsbuild(entry,'writing-header-entry.tsx',{loader:'tsx',jsx:'automatic',target:'esnext'})).code;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/writing-header')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/writing-header','<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"></head><body style="margin:0"><div id="root"></div><script type="module" src="/writing-header-entry.tsx"></script></body></html>'));});}}]});
 await server.listen();const address=server.httpServer?.address();if(!address||typeof address==='string')throw Error('WRITING_HEADER_LISTENER_REQUIRED');base=`http://127.0.0.1:${address.port}/writing-header`;
});
test.afterAll(async()=>{await server?.close();});
test('native header owns one chooser action and rejects old snapshots while preserving its document',async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>{errors.push(error.message);console.error('[writing-header pageerror]',error.message);});page.on('console',message=>{if(message.type()==='error'){errors.push(message.text());console.error('[writing-header console]',message.text());}});
 await page.setViewportSize({width:390,height:844});await page.goto(base);
 await expect(page.getByRole('button',{name:'Loading…',exact:true})).toBeDisabled();
 await page.evaluate(()=>(window as any).__writingFrame.emit({type:'chooser-view',revision:1,loading:false,selectedStateId:'happy',name:'Happy',expanded:false}));
 const action=page.getByRole('button',{name:'Happy',exact:true});await expect(action).toHaveCount(1);await expect(action).toBeEnabled();await action.click();
 await expect.poll(()=>page.evaluate(()=>(window as any).__writingFrame.scripts.at(-1))).toContain('openChooserNonce');
 const before=await page.evaluate(()=>(window as any).__writingFrame.scripts.length);
 await page.evaluate(()=>{const f=(window as any).__writingFrame;f.emit({type:'chooser-view',revision:1,loading:false,selectedStateId:'ok',name:'Old',expanded:false});f.emit({type:'chooser-view',documentId:'another-document',revision:30,loading:false,selectedStateId:'ok',name:'Wrong document',expanded:false});});
 await expect(action).toBeVisible();
 await page.evaluate(()=>(window as any).__writingFrame.emit({type:'chooser-view',revision:2,loading:false,selectedStateId:'ok',name:'OK',expanded:false}));await expect(page.getByRole('button',{name:'OK',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Toggle active',exact:true}).click();await expect(page.getByRole('button',{name:'OK',exact:true})).toBeDisabled();
 await page.getByRole('button',{name:'Toggle active',exact:true}).click();await expect(page.getByRole('button',{name:'OK',exact:true})).toBeEnabled();
 await page.evaluate(()=>{const f=(window as any).__writingFrame;f.documentId='reloaded-writing-document';f.emit({type:'ready'});});await expect(page.getByRole('button',{name:'Loading…',exact:true})).toBeDisabled();
 expect(await page.evaluate(()=>(window as any).__writingFrame.scripts.length)).toBeGreaterThan(before);expect(await page.evaluate(()=>(window as any).__writingFrame.urls.length)).toBe(1);expect(errors).toEqual([]);
});
