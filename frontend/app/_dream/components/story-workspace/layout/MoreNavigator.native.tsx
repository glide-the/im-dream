// [Input] Authenticated public owner, App-owned origin/catalog and existing Settings/Chat callbacks.
// [Output] One native five-item More page and persistent Writing/Timeline/Reflections/Settings destinations.
// [Pos] Navigation composition only; normal login, permissions, task execution and backend lifecycle remain App/server owned.
// [Sync] 2026-10-29: adopt the existing five-item menu; account-scoped Reflections observer is disposed only with its owner.
import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {ActivityIndicator,BackHandler,Keyboard,Platform,Pressable,StyleSheet,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {Deck,VoiceConfig} from '../../../api/voiceApi';
import {getPreferences} from '../../../api/voiceApi';
import {createNativeReflections} from '../../../../../src/platform/reflections.native';
import {clientFetch} from '../../../../../src/platform/transport';
import InkLabel from '../../../../../src/components/InkLabel.native';
import useInkColors from '../../../../../src/components/useInkColors.native';
import {toggleTheme} from '../../../utils/theme.native';
import AnalysisView from '../../AnalysisView.native';
import CollectionsView from '../../CollectionsView.native';
import WritingView from '../../WritingView.native';
import MoreNavigationPage from './MoreNavigationPage.native';
import type {MoreNavigationDestination} from './moreNavigation';
interface Props {ownerId:string;origin:string;decks:Deck[];active:boolean;resetNonce:number;onClose:()=>void;onSessionExpired:()=>void;onOpenThread:(id:string)=>void;onPrepareChat:(input:string)=>void;renderSettings:(onBack:()=>void,active:boolean)=>ReactNode;onSettingsOpen:()=>void;onResources:()=>void}
export default function MoreNavigator({ownerId,origin,decks,active,resetNonce,onClose,onSessionExpired,onOpenThread,onPrepareChat,renderSettings,onSettingsOpen,onResources}:Props){
 const {t,i18n}=useTranslation(),c=useInkColors(),callbacks=useRef({onSessionExpired,onClose});callbacks.current={onSessionExpired,onClose};
 const [page,setPage]=useState<MoreNavigationDestination|'menu'>('menu'),[visited,setVisited]=useState<Set<MoreNavigationDestination>>(()=>new Set());
 const [timezone,setTimezone]=useState(()=>{try{return Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';}catch{return 'UTC';}}),[timezoneError,setTimezoneError]=useState(false),[prefsRevision,setPrefsRevision]=useState(0);
 const [resource]=useState(()=>createNativeReflections(ownerId,()=>callbacks.current.onSessionExpired()));
 useEffect(()=>()=>resource.dispose(),[resource]);
 useEffect(()=>{setPage('menu');},[resetNonce]);
 useEffect(()=>{const abort=new AbortController();const read:typeof fetch=async(input,init)=>{const response=await clientFetch(input,{...init,signal:abort.signal});if(response.status===401)callbacks.current.onSessionExpired();return response;};
  void getPreferences(read).then(preferences=>{if(abort.signal.aborted)return;if(preferences.timezone){new Intl.DateTimeFormat('en',{timeZone:preferences.timezone});setTimezone(preferences.timezone);}setTimezoneError(false);}).catch(()=>{if(!abort.signal.aborted)setTimezoneError(true);});return()=>abort.abort();
 },[prefsRevision]);
 const root=()=>{Keyboard.dismiss();setPage('menu');};
 const navigate=(destination:MoreNavigationDestination)=>{Keyboard.dismiss();setVisited(previous=>new Set(previous).add(destination));if(destination==='settings')onSettingsOpen();setPage(destination);};
 useEffect(()=>{if(!active||page==='settings'||Platform.OS!=='android')return;const listener=BackHandler.addEventListener('hardwareBackPress',()=>{if(page==='menu')callbacks.current.onClose();else root();return true;});return()=>listener.remove();},[active,page]);
 const voices=useMemo<Record<string,VoiceConfig>>(()=>Object.fromEntries(decks.flatMap(deck=>(deck.voices??[]).map(voice=>[voice.name,{name:voice.name,systemPrompt:voice.system_prompt,enabled:voice.enabled,icon:voice.icon,color:voice.color}]))),[decks]);
 const show=(destination:MoreNavigationDestination)=>active&&page===destination;
 const scene=(destination:MoreNavigationDestination,content:ReactNode)=>visited.has(destination)?<View key={destination} style={[s.fill,page!==destination?s.hidden:undefined]} accessibilityElementsHidden={!show(destination)} importantForAccessibility={show(destination)?'auto':'no-hide-descendants'}>{content}</View>:null;
 return <View style={s.fill}>
  <View style={[s.fill,page!=='menu'?s.hidden:undefined]} accessibilityElementsHidden={page!=='menu'||!active} importantForAccessibility={page==='menu'&&active?'auto':'no-hide-descendants'}><MoreNavigationPage onNavigate={navigate} onToggleTheme={()=>{toggleTheme();}} onClose={onClose}/></View>
  {timezoneError&&['timeline','analysis'].includes(page)?<View style={s.notice}><InkLabel accessibilityRole="alert" style={{color:c['color-state-error']}}>{i18n.language.startsWith('zh')?'无法读取时区设置。':'Timezone settings could not be loaded.'}</InkLabel><Pressable accessibilityRole="button" onPress={()=>setPrefsRevision(value=>value+1)} style={s.retry}><InkLabel style={{color:c['color-text-primary']}}>{t('analysis.history.retry')}</InkLabel></Pressable></View>:null}
  {scene('writing',origin?<WritingView origin={origin} active={show('writing')} onBack={root} onOpenThread={onOpenThread} onPrepareChat={onPrepareChat} onOpenResources={()=>{navigate('settings');onResources();}} onSessionExpired={onSessionExpired}/>:<ActivityIndicator color={c['color-text-primary']}/>)}
  {scene('timeline',<CollectionsView timezone={timezone} authenticated api={resource.api} voiceConfigs={voices} active={show('timeline')} onBack={root}/>)}
  {scene('analysis',<AnalysisView timezone={timezone} authenticated api={resource.api} storage={resource.storage} active={show('analysis')} onBack={root} onTimeline={()=>navigate('timeline')}/>)}
  {scene('settings',renderSettings(root,show('settings')))}
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},hidden:{display:'none'},notice:{padding:12,gap:8},retry:{padding:10,minHeight:44}});
