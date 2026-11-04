// [Input] Existing composer document source and installed Vite/React dependencies.
// [Output] One named loopback document server for the isolated APP-06 Simulator fixture.
// [Pos] Technical harness only; public production component owns editing and document protocol.
import {createServer,transformWithEsbuild} from 'vite';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../',import.meta.url));
const entry=`import {createRoot} from 'react-dom/client';import Document from '/app/_dream/components/chat/MarkdownInputDocument.tsx';import '/app/_dream/index.css';createRoot(document.getElementById('root')).render(<Document/>);`;
const server=await createServer({root,configFile:false,cacheDir:root+'output/playwright/app06-20261103/vite-document',logLevel:'warn',server:{host:'127.0.0.1',port:0,hmr:false},optimizeDeps:{include:['react','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','@tiptap/react','@tiptap/extension-placeholder','@tiptap/markdown','@tiptap/starter-kit']},plugins:[{
  name:'app06-composer-document',enforce:'pre',resolveId(id){if(id==='/app06-document.tsx')return '\0app06-document';},async load(id){if(id==='\0app06-document')return (await transformWithEsbuild(entry,'fixture.tsx',{loader:'tsx',jsx:'automatic'})).code;},configureServer(vite){vite.middlewares.use(async(req,res,next)=>{if(req.url?.split('?')[0]!=='/native/composer')return next();res.setHeader('Content-Type','text/html');res.end(await vite.transformIndexHtml('/native/composer','<html><head><meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"><link rel="icon" href="data:,"></head><body><div id="root"></div><script type="module" src="/app06-document.tsx"></script></body></html>'));});}
}]});
await server.listen();const address=server.httpServer.address();process.stdout.write(JSON.stringify({origin:`http://127.0.0.1:${address.port}`,pid:process.pid})+'\n');
for(const signal of ['SIGTERM','SIGINT'])process.on(signal,async()=>{await server.close();process.exit(0);});
