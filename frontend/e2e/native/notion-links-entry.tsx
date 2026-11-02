// [Input] Original native Notion/About components, shared DTO parser and in-memory authorization fixtures.
// [Output] A named Hermes UI harness exercising default external-link callbacks and synchronous failure recovery.
// [Pos] Simulator-only technical entry; no account, credential, backend, database or model is used.
import '../../src/platform/sdkWebApis.native';
import React,{useEffect,useState} from 'react';
import {AppRegistry,Pressable,Text,View} from 'react-native';
import i18n from '../../app/_dream/i18n';
import NativeNotion from '../../app/_dream/components/dashboard/ConnectorNotionDetailPage.native';
import AboutView from '../../app/_dream/components/AboutView.native';
import {createResourceConnectorApi} from '../../app/_dream/api/resourceConnectorApi';
import {loadBrowserSession} from '../../app/_dream/lib/browserSession';

const connector={id:'notion-link-fixture',name:'Notion',platform:'notion',auth_status:'authenticating',
  auth:{status:'authenticating',verification_code:'FIXTURE',verification_url:'https://example.org/ink-notion-authorization'},sources:[]};
const fakeFetch:typeof fetch=async(input)=>{
  const path=String(input).split('?')[0];
  const value=path.endsWith('/auth/session')?{user:{id:'20261101',email:'fixture@example.invalid',display_name:'Link fixture',avatar_url:null,role:'user',created_at:null},csrf_token:'n'.repeat(43)}
    :path.endsWith('/capabilities')?{catalog:{schema_version:5,package_revision:'notion-link-fixture',cli_installation:{status:'installed',required_version:'0.15.1',install_command:'npm install -g ntn@0.15.1'},mcp_inventory:{status:'not_integrated',revision:null,read_status:'not_integrated',write_status:'not_integrated'},skills:[],operations:[]}}
    :path.endsWith('/api/connectors')?{connectors:[connector]}:{connector};
  return new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}});
};
const api=createResourceConnectorApi(fakeFetch,()=>{});
const observation={hidden:()=>false,subscribe:()=>()=>{}};
function Harness(){
  const [ready,setReady]=useState(false),[page,setPage]=useState('notion'),[error,setError]=useState('');
  useEffect(()=>{void Promise.all([loadBrowserSession(fakeFetch),i18n.changeLanguage('zh')]).then(()=>setReady(true)).catch(reason=>setError(reason?.constructor?.name??'FixtureError'));},[]);
  if(error)return <Text>{`Link fixture failed: ${error}`}</Text>;
  if(!ready)return <Text>Preparing link fixture</Text>;
  return <View style={{flex:1}}>
    <View style={{flexDirection:'row',padding:8,gap:16}}>{['notion','about','failure'].map(value=><Pressable key={value} accessibilityRole="button" accessibilityLabel={`Test ${value}`} onPress={()=>setPage(value)}><Text>{`Test ${value}`}</Text></Pressable>)}</View>
    {page==='about'?<AboutView onBack={()=>setPage('notion')}/>:<NativeNotion key={page} ownerId="20261101" active api={api} observation={observation} onBack={()=>{}}
      {...(page==='failure'?{openLink:()=>{throw Error('synchronous fixture link failure');}}:{})}/>}
  </View>;
}
AppRegistry.registerComponent('InkMemory',()=>Harness);
