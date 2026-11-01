// [Sync] 2026-10-31: cover inactive blur, retained draft/document and explicit refocus through original production components.
// [Input] Production Native editor, its original DOM document and an isolated WebView transport facade.
// [Output] Focus-release and retained-draft regression; no account, backend, model or persistent business writes.
// [Pos] Platform focus contract; actual UIKit keyboard dismissal requires separate Simulator validation.
import {test,expect} from '@playwright/test';
import {createServer,transformWithEsbuild,type ViteDevServer} from 'vite';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../',import.meta.url));
let server:ViteDevServer,origin:string;
const entry=`
import {createRoot} from 'react-dom/client';
import {useState} from 'react';
import Editor from '/app/_dream/components/chat/MarkdownInputEditor.native.tsx';
function Fixture(){
 const [active,setActive]=useState(true),[value,setValue]=useState('Original unsent draft');
 const f=window.__focusFixture??=(window.__focusFixture={submits:0,blurs:0,mounts:0,identities:[]});
 f.setActive=setActive;f.value=value;
 return <><output aria-label="Native draft">{value}</output><output aria-label="Active scene">{String(active)}</output>
 <Editor origin={location.origin} value={value} onChange={setValue} active={active} ariaLabel="Focus draft" placeholder="Draft" onSubmit={()=>f.submits++} onBlur={()=>f.blurs++}/></>;
}
createRoot(document.getElementById('root')).render(<Fixture/>);`;
const documentEntry=`
import {createRoot} from 'react-dom/client';
import Document from '/app/_dream/components/chat/MarkdownInputDocument.tsx';
window.ReactNativeWebView={postMessage:raw=>parent.postMessage({source:'focus-fixture-document',raw},location.origin)};
createRoot(document.getElementById('root')).render(<Document/>);`;
const webview=`
import {forwardRef,useEffect,useImperativeHandle,useRef} from 'react';
export const WebView=forwardRef(function FixtureWebView(props,ref){
 const frame=useRef(null),latest=useRef(props);latest.current=props;
 useEffect(()=>{window.__focusFixture.mounts++;latest.current.onLoadStart?.();
  const receive=event=>{if(event.source!==frame.current?.contentWindow||event.data?.source!=='focus-fixture-document')return;
   const message=JSON.parse(event.data.raw);if(message.type==='ready')window.__focusFixture.identities.push(message.documentId);
   latest.current.onMessage?.({nativeEvent:{url:latest.current.source.uri,data:event.data.raw}});
  };window.addEventListener('message',receive);return()=>window.removeEventListener('message',receive);
 },[props.source.uri]);
 useImperativeHandle(ref,()=>({injectJavaScript:script=>frame.current?.contentWindow.eval(script),reload:()=>frame.current?.contentWindow.location.reload()}),[]);
 return <iframe ref={frame} title="Production composer document" src={props.source.uri} style={{width:'100%',height:320,border:0}}/>;
});`;

test.beforeAll(async()=>{
 server=await createServer({root,configFile:false,logLevel:'silent',cacheDir:'/tmp/ink-ios-keyboard-navigation-20261031/vite-focus',define:{__DEV__:'false'},
  optimizeDeps:{noDiscovery:true,include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','react-native-web','i18next','react-i18next','@tiptap/react','@tiptap/extension-placeholder','@tiptap/markdown','@tiptap/starter-kit']},
  resolve:{alias:[{find:/^react-native$/,replacement:root+'e2e/native/appearance-platform-web-boundary.ts'}]},server:{host:'127.0.0.1',port:0,hmr:false},plugins:[{
   name:'composer-focus-boundary',enforce:'pre',resolveId(id,importer){
    if(['/focus-entry.tsx','/focus-document.tsx','react-native-webview'].includes(id))return '\0'+id;
    if(id.endsWith('/interfaceSettings')&&importer&&!importer.endsWith('interfaceSettings.ios.ts'))return root+'src/platform/interfaceSettings.ios.ts';
   },async load(id){const code=id==='\0/focus-entry.tsx'?entry:id==='\0/focus-document.tsx'?documentEntry:id==='\0react-native-webview'?webview:null;return code?(await transformWithEsbuild(code,'fixture.tsx',{loader:'tsx',jsx:'automatic'})).code:null;},
   configureServer(vite){vite.middlewares.use(async(req,res,next)=>{
    const path=req.url?.split('?')[0];if(!['/focus-fixture','/native/composer'].includes(path??''))return next();
    res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml(path!,'<html><head><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="'+(path==='/native/composer'?'/focus-document.tsx':'/focus-entry.tsx')+'"></script></body></html>'));
   });},
  }]});await server.listen();const address=server.httpServer!.address();if(!address||typeof address==='string')throw Error('FOCUS_FIXTURE_LISTENER');origin='http://127.0.0.1:'+address.port;
});
test.afterAll(async()=>{await server?.close();});

test('inactive Native editor blurs the real retained document without submitting or losing its draft',async({page})=>{
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/*',route=>{const url=new URL(route.request().url());if(url.origin!==origin||url.pathname.startsWith('/api/')||url.pathname.startsWith('/auth/')){errors.push('Unexpected request '+url.pathname);return route.abort();}return route.continue();});
 await page.goto(origin+'/focus-fixture');
 const editor=page.frameLocator('iframe').getByRole('textbox',{name:'Focus draft'});
 await expect(editor).toHaveText('Original unsent draft');await editor.fill('Retained unsent draft after native navigation');
 await expect(page.getByLabel('Native draft')).toHaveText('Retained unsent draft after native navigation');
 await expect(editor).toBeFocused();
 // Native navigation changes scene ownership without a browser focus transfer.
 await page.evaluate(()=>{(window as any).__focusFixture.setActive(false);});
 await expect(page.getByLabel('Active scene')).toHaveText('false');await expect(editor).not.toBeFocused();
 await expect.poll(()=>page.evaluate(()=>(window as any).__focusFixture.blurs)).toBe(1);
 await page.evaluate(()=>{(window as any).__focusFixture.setActive(true);});
 await expect(page.getByLabel('Active scene')).toHaveText('true');await expect(editor).not.toBeFocused();
 await expect(editor).toHaveText('Retained unsent draft after native navigation');
 await editor.click();await expect(editor).toBeFocused();
 expect(await page.evaluate(()=>{const f=(window as any).__focusFixture;return {submits:f.submits,mounts:f.mounts,identities:f.identities.length};})).toEqual({submits:0,mounts:1,identities:1});
 expect(errors).toEqual([]);
});
