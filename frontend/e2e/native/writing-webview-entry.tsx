// [Input] Production WritingView, its real WKWebView and an explicit loopback DTO fixture origin from Simulator Settings.
// [Output] Isolated native Writing navigation/chooser/keyboard journey against packaged original Next resources.
// [Pos] Simulator-only technical composition; original editor/DTO/protocol own all behavior, no real account/database/model.
import '../../src/platform/sdkWebApis.native';
import React,{useEffect,useState} from 'react';
import {AppRegistry,Pressable,Settings,Text,View} from 'react-native';
import WritingView from '../../app/_dream/components/WritingView.native';
import i18n from '../../app/_dream/i18n';

const origin=Settings.get('ink-writing-fixture-origin') as string|undefined;
function Harness(){
 const [ready,setReady]=useState(false),[active,setActive]=useState(true),[version,setVersion]=useState(0),[error,setError]=useState('');
 useEffect(()=>{void i18n.changeLanguage('zh').then(()=>setReady(true));},[]);
 if(!origin||!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(origin))return <Text>Writing fixture origin is required</Text>;
 if(!ready)return <Text>Preparing Writing fixture</Text>;
 return <View style={{flex:1}}>
  <View style={{flexDirection:'row',padding:4,gap:8}}>
   <Pressable accessibilityRole="button" accessibilityLabel="首次心情夹具" style={{minHeight:44,padding:8}} onPress={()=>{
    void fetch(origin+'/_writing-fixture/reset',{method:'POST'}).then(response=>{if(!response.ok)throw Error('reset');setVersion(value=>value+1);setActive(true);}).catch(()=>setError('Fixture reset failed'));
   }}><Text>首次心情夹具</Text></Pressable>
  </View>
  {error?<Text accessibilityRole="alert">{error}</Text>:null}
  {!active?<Pressable accessibilityRole="button" accessibilityLabel="返回写作" style={{minHeight:44,padding:12}} onPress={()=>setActive(true)}><Text>返回写作</Text></Pressable>:null}
  <View style={{flex:1,display:active?'flex':'none'}}>
   <WritingView key={version} origin={origin} active={active} onBack={()=>setActive(false)} onOpenThread={()=>{}} onPrepareChat={()=>{}} onOpenResources={()=>{}} onSessionExpired={()=>setError('Unexpected fixture session expiry')}/>
  </View>
 </View>;
}
AppRegistry.registerComponent('InkMemory',()=>Harness);
