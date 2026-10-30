// [Input] Original Settings categories/search, App catalog/config callbacks and normal account actions.
// [Output] Native six-category Settings, Work tabs and original resource destinations with retained drafts.
// [Pos] Settings navigation composition; BackendRuntimeManager, authentication and business APIs retain their owners.
// [Sync] 2026-10-29: adopt existing native content and one account-scoped resource owner, without ordinary Settings WebViews.
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {BackHandler,Keyboard,Platform,Pressable,ScrollView,StyleSheet,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {Deck,Voice} from '../../api/voiceApi';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport';
import {createNativeSettingsResources} from '../../../../src/platform/settingsResources.native';
import GeneralSettings from './GeneralSettings.native';
import MemoryBehaviorSettings from './MemoryBehaviorSettings.native';
import StoryWorkspaceSubscriptionPage from './StoryWorkspaceSubscriptionPage.native';
import AboutView from '../../components/AboutView.native';
import ModelConfigSection from '../../components/dashboard/ModelConfigSection.native';
import DeckManager from '../../components/DeckManager.native';
import ClaudePluginAdminPage from '../../components/claude-plugin-admin/ClaudePluginAdminPage.native';
import ConnectorSettingsSection from '../../components/dashboard/ConnectorSettingsSection.native';
import {filterStoryWorkspaceSettingsNavigation,STORY_WORKSPACE_SETTINGS_STATIC_SEARCH_KEYS as SEARCH} from './storyWorkspaceSettingsSearch';
type Category='general'|'subscription'|'work'|'behavior'|'model'|'about';
type WorkTab='deck'|'resources'|'plugins';
export interface NativeSettingsNavigation {nonce:number;target:'menu'|'resources'}
interface Props {ownerId:string;origin:string;active:boolean;navigation:NativeSettingsNavigation;decks:Deck[];loading:boolean;error?:string;onRefreshDecks:()=>Promise<Deck[]>;onTryDeck:(deck:Deck,voice:Voice,input?:string)=>void;onBack:()=>void;onSessionExpired:()=>void;onConfigSaved:()=>void;logout:()=>Promise<void>;transport?:typeof fetch}
export default function StoryWorkspaceSettingsPage({ownerId,origin,active,navigation,decks,loading,error,onRefreshDecks,onTryDeck,onBack,onSessionExpired,onConfigSaved,logout,transport=clientFetch}:Props){
 const {t,i18n}=useTranslation(),c=useInkColors(),sessionExpired=useRef(onSessionExpired);sessionExpired.current=onSessionExpired;
 const [resources]=useState(()=>createNativeSettingsResources(ownerId,()=>sessionExpired.current(),transport));
 const [category,setCategory]=useState<Category|'menu'>(navigation.target==='resources'?'work':'menu'),[visited,setVisited]=useState<Set<Category>>(()=>new Set(navigation.target==='resources'?['work']:[]));
 const [workTab,setWorkTab]=useState<WorkTab>('resources'),[visitedTabs,setVisitedTabs]=useState<Set<WorkTab>>(()=>new Set(navigation.target==='resources'?['resources']:[])),[resourceNonce,setResourceNonce]=useState(navigation.nonce),[resourceDetail,setResourceDetail]=useState(false);
 const [query,setQuery]=useState(''),[logoutError,setLogoutError]=useState(false);
 useEffect(()=>()=>resources.dispose(),[resources]);
 useEffect(()=>{resources.setVisible(active&&category==='work'&&workTab==='resources');},[resources,active,category,workTab]);
 function open(id:Category,tab:WorkTab='deck') {Keyboard.dismiss();setVisited(current=>new Set(current).add(id));setCategory(id);if(id==='work'){setWorkTab(tab);setVisitedTabs(current=>new Set(current).add(tab));if(tab==='resources')setResourceNonce(value=>value+1);}}
 useEffect(()=>{if(navigation.target==='resources')open('work','resources');else {Keyboard.dismiss();setCategory('menu');}},[navigation.nonce]);
 const root=()=>{Keyboard.dismiss();setCategory('menu');};
 useEffect(()=>{if(!active||Platform.OS!=='android'||category==='model'||(category==='work'&&workTab==='resources'&&resourceDetail))return;const listener=BackHandler.addEventListener('hardwareBackPress',()=>{if(category==='menu')onBack();else root();return true;});return()=>listener.remove();},[active,category,workTab,resourceDetail,onBack]);
 const text={color:c['color-text-primary']};
 const items=[
  {id:'general' as const,label:t('settings.workspace.navigation.general'),searchKeys:SEARCH.settings},
  {id:'subscription' as const,label:t('settings.workspace.navigation.subscription'),searchKeys:SEARCH['settings-subscription']},
  {id:'work' as const,label:t('settings.workspace.navigation.work'),searchKeys:SEARCH['settings-work']},
  {id:'behavior' as const,label:t('settings.workspace.navigation.behavior',{defaultValue:i18n.language.startsWith('zh')?'记忆回应':'Memory responses'}),searchKeys:SEARCH['settings-behavior']},
  {id:'model' as const,label:t('settings.workspace.navigation.model'),searchKeys:SEARCH['settings-model']},
  {id:'about' as const,label:t('settings.workspace.navigation.about'),searchKeys:SEARCH['settings-about']},
 ];
 const searched=query.trim()?filterStoryWorkspaceSettingsNavigation([...items,{id:'work' as const,tab:'resources' as WorkTab,label:t('settings.workspace.work.tabs.resources'),searchKeys:SEARCH['settings-resources']},{id:'work' as const,tab:'plugins' as WorkTab,label:t('settings.workspace.work.tabs.plugins'),searchKeys:SEARCH['settings-plugins']}].map(item=>({...item,searchKeys:[...item.searchKeys,item.label]})),query):items;
 const button=(label:string,onPress:()=>void)=><Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={[s.button,{borderColor:c['color-border-paper']}]}><InkLabel style={text}>{label}</InkLabel></Pressable>;
 const show=(id:Category)=>active&&category===id;
 const scene=(id:Category,content:ReactNode)=>visited.has(id)?<View key={id} style={[s.fill,category!==id?s.hidden:undefined]} accessibilityElementsHidden={!show(id)} importantForAccessibility={show(id)?'auto':'no-hide-descendants'}>{content}</View>:null;
 return <View style={[s.fill,{backgroundColor:c['color-bg-app']}]}>
  <View style={[s.fill,category!=='menu'?s.hidden:undefined]} accessibilityElementsHidden={!active||category!=='menu'} importantForAccessibility={active&&category==='menu'?'auto':'no-hide-descendants'}>
   <View style={s.header}>{button(`← ${t('nav.more')}`,onBack)}<InkLabel accessibilityRole="header" style={[text,s.title]}>{t('nav.settings')}</InkLabel></View>
   <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={s.content}>
    <TextInput accessibilityLabel={t('settings.workspace.search.label')} placeholder={t('settings.workspace.search.placeholder')} placeholderTextColor={c['color-text-secondary']} value={query} onChangeText={setQuery} style={[s.input,text,{borderColor:c['color-border-paper']}]}/>
    {searched.map((item,index)=><View key={`${item.id}-${index}`}>{button(item.label,()=>open(item.id,'tab' in item?item.tab as WorkTab:'deck'))}</View>)}
    {searched.length===0?<InkLabel style={{color:c['color-text-secondary']}}>{t('settings.workspace.search.noResults')}</InkLabel>:null}
    {button(i18n.language.startsWith('zh')?'退出登录':'Logout',()=>{setLogoutError(false);void logout().catch(()=>setLogoutError(true));})}{logoutError?<InkLabel accessibilityRole="alert" style={{color:c['color-state-error']}}>退出失败，请重试。</InkLabel>:null}
   </ScrollView>
  </View>
  {scene('general',<GeneralSettings onBack={root} transport={transport} onSessionExpired={onSessionExpired}/>)}
  {scene('subscription',<StoryWorkspaceSubscriptionPage onBack={root} transport={transport} onSessionExpired={onSessionExpired}/>)}
  {scene('behavior',<MemoryBehaviorSettings active={show('behavior')} onBack={root} transport={transport} onSessionExpired={onSessionExpired}/>)}
  {scene('model',<ModelConfigSection active={show('model')} onBack={root} transport={transport} onSessionExpired={onSessionExpired} onConfigSaved={onConfigSaved}/>)}
  {scene('about',<AboutView onBack={root}/>)}
  {scene('work',<>
   <View style={workTab==='resources'&&resourceDetail?s.hidden:undefined}>
    <View style={s.header}>{button(t('settings.workspace.preferences.back'),root)}<InkLabel accessibilityRole="header" style={[text,s.title]}>{t('settings.workspace.work.title')}</InkLabel></View>
    <View style={s.tabs} accessibilityRole="tablist" accessibilityLabel={t('settings.workspace.work.tabsLabel')}>{(['deck','resources','plugins'] as const).map(tab=><Pressable key={tab} accessibilityRole="tab" accessibilityLabel={t(`settings.workspace.work.tabs.${tab}`)} accessibilityState={{selected:workTab===tab}} onPress={()=>open('work',tab)} style={[s.button,{borderColor:c['color-border-paper'],backgroundColor:workTab===tab?c['color-bg-hover']:'transparent'}]}><InkLabel style={text}>{t(`settings.workspace.work.tabs.${tab}`)}</InkLabel></Pressable>)}</View>
   </View>
   {visitedTabs.has('deck')?<View style={[s.fill,workTab!=='deck'?s.hidden:undefined]} accessibilityElementsHidden={!show('work')||workTab!=='deck'} importantForAccessibility={show('work')&&workTab==='deck'?'auto':'no-hide-descendants'}><DeckManager managementOnly decks={decks} active={show('work')&&workTab==='deck'} loading={loading} error={error} transport={transport} onRefresh={onRefreshDecks} onSessionExpired={onSessionExpired} onTryDeck={onTryDeck}/></View>:null}
   {visitedTabs.has('resources')?<View style={[s.fill,workTab!=='resources'?s.hidden:undefined]} accessibilityElementsHidden={!show('work')||workTab!=='resources'} importantForAccessibility={show('work')&&workTab==='resources'?'auto':'no-hide-descendants'}><ConnectorSettingsSection ownerId={ownerId} origin={origin} resources={resources} active={show('work')&&workTab==='resources'} focusNonce={resourceNonce} onDetailChange={setResourceDetail}/></View>:null}
   {visitedTabs.has('plugins')?<View style={[s.fill,workTab!=='plugins'?s.hidden:undefined]} accessibilityElementsHidden={!show('work')||workTab!=='plugins'} importantForAccessibility={show('work')&&workTab==='plugins'?'auto':'no-hide-descendants'}><ClaudePluginAdminPage active={show('work')&&workTab==='plugins'} transport={transport} onSessionExpired={onSessionExpired}/></View>:null}
  </>)}
 </View>;
}
const s=StyleSheet.create({fill:{flex:1,minHeight:0},hidden:{display:'none'},header:{flexDirection:'row',alignItems:'center',gap:12,padding:12},title:{fontSize:22},content:{padding:20,gap:12,paddingBottom:32},button:{minHeight:44,padding:12,borderWidth:StyleSheet.hairlineWidth,borderRadius:10,justifyContent:'center'},input:{minHeight:44,padding:12,borderWidth:1,borderRadius:10},tabs:{flexDirection:'row',flexWrap:'wrap',gap:8,paddingHorizontal:16,paddingBottom:12}});
