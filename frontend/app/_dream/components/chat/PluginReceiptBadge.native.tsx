// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original bound Deck, selected Agent, plugin receipt and platform HTTP/clipboard adapters.
// [Output] Native counterpart of the original Deck metadata popup and current Agent badge.
// [Pos] Chat toolbar presentation; selecting an Agent changes only the caller's next-turn choice.
import {useEffect,useMemo,useRef,useState} from 'react';
import {AccessibilityInfo,AppState,findNodeHandle,Modal,Pressable,ScrollView,StyleSheet,View,useWindowDimensions} from 'react-native';
import {useTranslation} from 'react-i18next';
import type {Deck,Voice} from '../../api/voiceApi';
import {shortDigest} from '../../api/claudePluginAdminApi';
import {useCopy} from '../../hooks/useCopy.native';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport.native';
import DeckAgentIcon,{deckAgentColor} from '../deck/DeckAgentIcon.native';
import {agentLabel,deckLabel,enabledAgentsOf} from '../deck/deckAgentSelection';
import usePluginReceiptBadgeData from './usePluginReceiptBadgeData';

type Anchor={x:number;y:number;width:number;height:number};
interface Props {
  activeVoiceId?:string;activeVoiceName?:string;deck?:Deck;threadId:string|null;
  onSelectAgent?:(voiceId:string)=>void;onSessionExpired?:()=>void;transport?:typeof fetch;
}
function CopyDigestButton({value}:{value:string}) {
  const {t}=useTranslation(),{copied,copy}=useCopy(1500);
  const colors=useInkColors();
  return <Pressable accessibilityRole="button" accessibilityLabel={t('chat.deck.metadataCopyDigest')}
    accessibilityHint={copied?t('chat.deck.metadataCopied'):undefined} onPress={()=>copy(value)}
    style={[styles.copy,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface']}]}>
    <InkLabel style={{fontSize:10,color:colors['color-text-secondary']}}>{copied?`✓ ${t('chat.deck.metadataCopied')}`:t('chat.deck.metadataCopyDigest')}</InkLabel>
  </Pressable>;
}
export function ChatAgentBadge({voice}:{voice:Pick<Voice,'name'|'icon'|'color'>}) {
  const colors=useInkColors(),color=deckAgentColor(voice.color,colors);
  return <View style={[styles.voiceBadge,{backgroundColor:color+'14',borderColor:color+'55'}]}>
    <DeckAgentIcon name={voice.icon || 'brain'} size={13.6} color={color}/>
    <InkLabel numberOfLines={1} style={{fontSize:13.12,fontWeight:'600',color,flexShrink:1}}>{voice.name}</InkLabel>
  </View>;
}
export default function PluginReceiptBadge({activeVoiceId,activeVoiceName,deck,threadId,onSelectAgent,onSessionExpired,transport=clientFetch}:Props) {
  const {t,i18n}=useTranslation(),language=(i18n.language || 'en').split('-')[0];
  const colors=useInkColors(),window=useWindowDimensions();
  const [anchor,setAnchor]=useState<Anchor|null>(null),[foreground,setForeground]=useState(AppState.currentState==='active');
  const trigger=useRef<View>(null),expired=useRef(onSessionExpired);expired.current=onSessionExpired;
  const read=useMemo<typeof fetch>(()=>async(input,init)=>{const response=await transport(input,init);if(response.status===401)expired.current?.();return response;},[transport]);
  const {receipt,configuredPlugins}=usePluginReceiptBadgeData({threadId,deck,transport:read,enabled:foreground,abortReads:true});
  useEffect(()=>{setAnchor(null);},[threadId]);
  useEffect(()=>{const listener=AppState.addEventListener('change',state=>{setForeground(state==='active');if(state!=='active')setAnchor(null);});return()=>listener.remove();},[]);
  const plugins=receipt?.receipt?.plugins ?? receipt?.launch_manifest?.plugins ?? [],hasReceiptPlugins=plugins.length>0;
  const frozen=receipt?.receipt?.frozen===true,name=deck?deckLabel(deck,language):null;
  const agents=deck?enabledAgentsOf(deck):[],agentCount=deck?(deck.voices?agents.length:(deck.voice_count ?? 0)):0;
  function close(){setAnchor(null);requestAnimationFrame(()=>{const tag=findNodeHandle(trigger.current);if(tag)AccessibilityInfo.setAccessibilityFocus(tag);});}
  function open(){trigger.current?.measureInWindow((x,y,width,height)=>setAnchor({x,y,width,height}));}
  if(!deck && !hasReceiptPlugins)return null;
  const width=Math.min(300,window.width-24),maxHeight=Math.min(380,window.height-24);
  const left=anchor?Math.max(12,Math.min(window.width-width-12,anchor.x+anchor.width-width)):12;
  const top=anchor?Math.max(12,Math.min(anchor.y+anchor.height+6,window.height-maxHeight-12)):12;
  const text={color:colors['color-text-body'],fontSize:12},muted={color:colors['color-text-muted'],fontSize:11};
  const heading=(label:string)=><InkLabel accessibilityRole="header" style={[styles.sectionLabel,muted]}>{label}</InkLabel>;
  return <View ref={trigger} collapsable={false} style={styles.root}>
    <Pressable accessibilityRole="button" accessibilityLabel={t('chat.deck.metadataTitle')} accessibilityState={{expanded:anchor!==null}}
      onPress={open} style={[styles.trigger,{backgroundColor:anchor?'#9b7ff52e':'#9b7ff518'}]}>
      <InkLabel style={{fontSize:12.48}}>🧩</InkLabel>
      <InkLabel numberOfLines={1} style={{fontSize:12.48,fontWeight:'600',color:'#7a63d8',flexShrink:1}}>{name ?? plugins.map(plugin=>`${plugin.package_spec.split('@')[0]} v${plugin.resolved_version ?? '?'} · ${shortDigest(plugin.artifact_digest)}`).join(' ')}</InkLabel>
      {frozen?<InkLabel style={{fontSize:12}}>🔒</InkLabel>:null}
    </Pressable>
    <Modal transparent visible={anchor!==null} animationType="none" onRequestClose={close} supportedOrientations={['portrait','landscape-left','landscape-right']}>
      <View style={styles.overlay} onAccessibilityEscape={close}>
        <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={close}/>
        {anchor?<View role="dialog" accessibilityViewIsModal accessibilityLabel={t('chat.deck.metadataTitle')}
          style={[styles.popup,{left,top,width,maxHeight,borderColor:colors['color-border-neutral'],backgroundColor:colors['color-bg-surface-solid'],shadowColor:colors['color-shadow-medium']}]}>
          <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
            <View style={styles.titleRow}><InkLabel accessibilityRole="header" style={{fontSize:14,fontWeight:'600',color:colors['color-text-primary']}}>{t('chat.deck.metadataTitle')}</InkLabel>
              {frozen?<InkLabel style={muted}>{`🔒 ${t('chat.deck.metadataFrozen')}`}</InkLabel>:null}</View>
            <View style={styles.section}>{heading(t('chat.deck.metadataDeckName'))}
              <InkLabel style={{fontSize:13,fontWeight:name?'600':'400',color:colors[name?'color-text-primary':'color-text-muted']}}>{name ?? t('chat.deck.metadataNoDeck')}</InkLabel>
            </View>
            {deck?<View style={styles.section}>{heading(`${t('chat.deck.metadataAgents')}（${agentCount}）`)}
              {agents.length?<View style={styles.agents}>{agents.map(voice=>{
                const label=agentLabel(voice,language),color=deckAgentColor(voice.color,colors);
                const current=activeVoiceId?voice.id===activeVoiceId:activeVoiceName!==undefined && label===activeVoiceName;
                const canSelect=Boolean(threadId && onSelectAgent && !current);
                return <Pressable key={voice.id} accessibilityRole="button" accessibilityLabel={t(current?'chat.deck.currentAgent':'chat.deck.switchAgent',{agent:label})}
                  accessibilityState={{selected:current,disabled:!canSelect}} disabled={!canSelect}
                  onPress={()=>{if(canSelect){onSelectAgent?.(voice.id);close();}}}
                  style={[styles.agent,{borderColor:current?color:color+'55',backgroundColor:color+(current?'2e':'14')}]}>
                  <DeckAgentIcon name={voice.icon || 'brain'} size={11} color={color}/><InkLabel style={[text,{fontSize:11,fontWeight:current?'700':'400',flexShrink:1}]}>{label}</InkLabel>
                  {current?<InkLabel style={[styles.current,{backgroundColor:color,color:colors['color-text-on-action']}]}>{t('chat.deck.metadataCurrentAgent')}</InkLabel>:null}
                </Pressable>;
              })}</View>:<InkLabel style={text}>{t('chat.deck.agentCount',{count:agentCount})}</InkLabel>}
            </View>:null}
            <View>{heading(`${t('chat.deck.metadataPlugins')}（${hasReceiptPlugins?plugins.length:(configuredPlugins?.length ?? 0)}）`)}
              {hasReceiptPlugins?<View style={styles.plugins}>{plugins.map(plugin=><View key={`${plugin.package_spec}-${plugin.artifact_digest}`} style={[styles.plugin,{borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface']}]}>
                <View style={styles.pluginTitle}><InkLabel style={[text,{fontWeight:'600',color:colors['color-text-primary']}]}>{plugin.package_spec}</InkLabel><InkLabel style={[text,{color:colors['color-text-secondary']}]}>{`v${plugin.resolved_version ?? '?'}`}</InkLabel></View>
                <View style={styles.digestRow}><InkLabel selectable style={[muted,{fontSize:10,flex:1}]}>{`sha256:${shortDigest(plugin.artifact_digest)}`}</InkLabel><CopyDigestButton value={plugin.artifact_digest}/></View>
              </View>)}</View>:configuredPlugins===null?<InkLabel style={muted}>{t('chat.deck.metadataPacking')}</InkLabel>:configuredPlugins.length===0?<InkLabel style={text}>{t('chat.deck.metadataNoPlugins')}</InkLabel>:<View style={styles.plugins}>
                {configuredPlugins.map(installation=><View key={installation.id} style={[styles.plugin,{borderStyle:'dashed',borderColor:colors['color-border-paper'],backgroundColor:colors['color-bg-surface']}]}>
                  <View style={styles.pluginTitle}><InkLabel style={[text,{fontWeight:'600',color:colors['color-text-primary']}]}>{installation.package_name}</InkLabel><InkLabel style={[text,{color:colors['color-text-secondary']}]}>{`v${installation.resolved_version}`}</InkLabel></View>
                </View>)}<InkLabel style={muted}>{t('chat.deck.metadataPacking')}</InkLabel>
              </View>}
            </View>
          </ScrollView>
        </View>:null}
      </View>
    </Modal>
  </View>;
}
const styles=StyleSheet.create({
  root:{flexShrink:1,minWidth:44,maxWidth:176},voiceBadge:{flexDirection:'row',alignItems:'center',gap:4.8,paddingHorizontal:8,paddingVertical:4.8,borderWidth:1,borderRadius:8.8,maxWidth:144,minWidth:0,flexShrink:1},
  trigger:{minHeight:44,minWidth:44,flexDirection:'row',alignItems:'center',gap:5.6,paddingHorizontal:9.6,borderWidth:1,borderColor:'#9b7ff555',borderRadius:8.8},
  overlay:{flex:1},popup:{position:'absolute',borderWidth:1,borderRadius:10,shadowOpacity:1,shadowRadius:15,shadowOffset:{width:0,height:10}},content:{paddingVertical:12,paddingHorizontal:14},
  titleRow:{gap:4,marginBottom:10},section:{marginBottom:12},sectionLabel:{marginBottom:5,fontSize:10,fontWeight:'700',letterSpacing:.6,textTransform:'uppercase'},
  agents:{flexDirection:'row',flexWrap:'wrap',gap:5},agent:{minHeight:44,maxWidth:'100%',flexDirection:'row',alignItems:'center',gap:4,paddingVertical:2,paddingHorizontal:8,borderRadius:999,borderWidth:1},
  current:{marginLeft:2,paddingHorizontal:5,borderRadius:999,fontSize:9,fontWeight:'700',letterSpacing:.4},plugins:{gap:7},pluginTitle:{flexDirection:'row',flexWrap:'wrap',gap:4},plugin:{paddingVertical:7,paddingHorizontal:9,borderRadius:7,borderWidth:1},
  digestRow:{flexDirection:'row',alignItems:'center',gap:6,marginTop:2},copy:{minWidth:44,minHeight:44,paddingHorizontal:6,borderWidth:1,borderRadius:5,justifyContent:'center',alignItems:'center'},
});
