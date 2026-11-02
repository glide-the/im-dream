// [Sync] 2026-10-29: follow the persisted native appearance and original explicit/system token palettes.
// [Input] Original Chat search query/results, grouped history and selection/close callbacks.
// [Output] Native search dialog with original title/excerpt/date presentation and retryable read feedback.
// [Pos] Native counterpart of ChatView's search dialog; reads stay in the canonical history coordinator.
import {useRef} from 'react';
import {ActivityIndicator,KeyboardAvoidingView,Modal,Platform,Pressable,SafeAreaView,ScrollView,StyleSheet,TextInput,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {formatThreadDateLabel,groupChatThreadsByDate} from './chatHistoryPresentation';
import {IconMessageCircle,IconX} from './Icons';
import type useNativeChatHistory from './useNativeChatHistory.native';
export type NativeChatHistory=ReturnType<typeof useNativeChatHistory>;
export default function ChatHistorySearch({history,activeThreadId,onSelect}:{history:NativeChatHistory;activeThreadId?:string|null;onSelect:(id:string)=>void}) {
  const {t,i18n}=useTranslation(),colors=useInkColors(),input=useRef<TextInput>(null);
  const query=history.query.trim(),groups=groupChatThreadsByDate(history.threads,t);
  function select(id:string){history.closeSearch();onSelect(id);}
  return <Modal transparent visible={history.searchOpen} animationType="fade" presentationStyle="overFullScreen" onShow={()=>input.current?.focus()} onRequestClose={history.closeSearch} supportedOrientations={['portrait','landscape']}>
    {/* This modal owns a separate native controller; its keyboard avoidance does not duplicate the SwiftUI main scene. */}
    <KeyboardAvoidingView style={styles.fill} behavior={Platform.OS==='ios'?'padding':undefined}>
      <SafeAreaView style={[styles.fill,{backgroundColor:colors['color-bg-surface']}]} onAccessibilityEscape={history.closeSearch}>
        <Pressable accessible={false} style={StyleSheet.absoluteFill} onPress={history.closeSearch} />
        <View accessibilityViewIsModal accessibilityLabel={t('chat.search.ariaLabel')} style={[styles.panel,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}>
          <View style={[styles.header,{borderColor:colors['color-border-paper']}]}>
            <TextInput ref={input} autoFocus value={history.query} onChangeText={history.setQuery} placeholder={t('chat.search.placeholder')} accessibilityLabel={t('chat.search.ariaLabel')}
              placeholderTextColor={colors['color-text-muted']} autoCapitalize="none" autoCorrect={false} style={[styles.input,{color:colors['color-text-primary']}]} />
            <Pressable accessibilityRole="button" accessibilityLabel={t('chat.search.closeAria')} onPress={history.closeSearch} style={styles.close}><IconX width={16.8} height={16.8} color={colors['color-text-muted']} /></Pressable>
          </View>
          <ScrollView style={styles.fill} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
            {history.searching && query?<View accessibilityRole="progressbar" accessibilityLabel={t('chat.search.searching')} style={styles.feedback}><ActivityIndicator color={colors['color-text-muted']} /><InkLabel style={{color:colors['color-text-muted']}}>{t('chat.search.searching')}</InkLabel></View>:null}
            {history.searchError && query?<InkLabel accessibilityRole="alert" style={[styles.feedback,{color:colors['color-state-error']}]}>{t('chat.activity.historyFailed')}</InkLabel>:null}
            {query && !history.searching && !history.searchError && !history.results.length?<InkLabel style={[styles.feedback,{color:colors['color-text-muted']}]}>{t('chat.search.noResults')}</InkLabel>:null}
            {!query && !groups.length?<InkLabel style={[styles.feedback,{color:colors['color-text-muted']}]}>{t('chat.history.empty')}</InkLabel>:null}
            {(query?[{label:'',threads:history.results}]:groups).map(group=><View key={group.label}>
              {group.label?<InkLabel accessibilityRole="header" style={[styles.group,{color:colors['color-text-muted']}]}>{group.label}</InkLabel>:null}
              {group.threads.map(thread=><Pressable key={thread.id} accessibilityRole="button" accessibilityLabel={thread.title ?? t('chat.history.fallbackTitle')} accessibilityState={{selected:thread.id===activeThreadId}}
                onPress={()=>select(thread.id)} style={({pressed})=>[styles.row,{backgroundColor:thread.id===activeThreadId || pressed?colors['color-bg-hover']:'transparent'}]}>
                <IconMessageCircle width={20.48} height={20.48} color={colors['color-text-primary']} />
                <View style={styles.titles}><InkLabel numberOfLines={1} style={[styles.title,{color:colors['color-text-primary']}]}>{thread.title ?? t('chat.history.fallbackTitle')}</InkLabel>
                  {query && thread.match?.excerpt?.trim()?<InkLabel numberOfLines={1} style={[styles.excerpt,{color:colors['color-text-secondary']}]}>{thread.match.excerpt.trim()}</InkLabel>:null}
                </View>
                {query?<InkLabel style={{fontSize:13.12,color:colors['color-text-muted']}}>{formatThreadDateLabel(thread.updated_at,t,i18n.language)}</InkLabel>:null}
              </Pressable>)}
            </View>)}
          </ScrollView>
        </View>
      </SafeAreaView>
    </KeyboardAvoidingView>
  </Modal>;
}
const styles=StyleSheet.create({fill:{flex:1},panel:{flex:1,margin:16,borderWidth:1,borderRadius:16,overflow:'hidden'},header:{minHeight:66.4,flexDirection:'row',alignItems:'center',gap:12,paddingHorizontal:16,borderBottomWidth:1},input:{flex:1,minWidth:0,minHeight:48,fontSize:18.88,fontWeight:'600',fontFamily:'Excalifont'},close:{width:44,height:44,alignItems:'center',justifyContent:'center'},content:{padding:12},feedback:{paddingVertical:12.8,paddingHorizontal:16,gap:8},group:{paddingTop:16,paddingHorizontal:16,paddingBottom:7.2,fontSize:13.12,fontWeight:'600'},row:{minHeight:52.8,flexDirection:'row',alignItems:'center',gap:12,paddingVertical:10.88,paddingHorizontal:14.4,borderRadius:12},titles:{flex:1,minWidth:0,gap:2.88},title:{fontSize:16,fontWeight:'600'},excerpt:{fontSize:13.76,lineHeight:18.58}});
