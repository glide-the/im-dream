// [Input] Original About content and explicit repository link action.
// [Output] Native project/team/timeline/links page with the original serif headings and system body font.
// [Pos] Settings About destination; no backend or model lifecycle changes.
import {useState} from 'react';
import {Linking,Platform,Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import Svg,{Path} from 'react-native-svg';
import InkLabel from '../../../src/components/InkLabel.native';
import useInkColors from '../../../src/components/useInkColors.native';
import {teamMembers,developmentTimeline,ABOUT_REPOSITORY_URL,ABOUT_SUMMARY,ABOUT_DESCRIPTION} from './aboutPresentation';
export default function AboutView({onBack,openLink=Linking.openURL}:{onBack:()=>void;openLink?:(url:string)=>Promise<unknown>}) {
  const {t,i18n}=useTranslation(),c=useInkColors(),[error,setError]=useState(false),text={color:c['color-text-primary']},secondary={color:c['color-text-secondary']};
  const heading=(label:string)=><Text accessibilityRole="header" style={[styles.heading,text]}>{label}</Text>;
  return <View style={[styles.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={styles.header}><Pressable accessibilityRole="button" onPress={onBack} style={styles.button}><InkLabel style={text}>{t('settings.workspace.preferences.back')}</InkLabel></Pressable><InkLabel accessibilityRole="header" style={[text,{fontSize:22}]}>{t('settings.workspace.navigation.about')}</InkLabel></View>
    <ScrollView contentContainerStyle={styles.content}>
      <View style={styles.intro}><Text accessibilityRole="header" style={[styles.brand,text]}><Text style={{fontStyle:'italic'}}>I</Text>nk &amp; <Text style={{fontStyle:'italic'}}>M</Text>emory</Text><Text style={[styles.summary,secondary]}>{ABOUT_SUMMARY}</Text></View>
      <View style={styles.section}>{heading('About the Project')}{ABOUT_DESCRIPTION.map(paragraph=><Text key={paragraph} style={[styles.body,secondary]}>{paragraph}</Text>)}</View>
      <View style={styles.section}>{heading('The Team')}{teamMembers.map(member=><View key={member.name} style={[styles.card,{backgroundColor:c['color-bg-paper'],borderColor:c['color-border-paper']}]}><Text style={[styles.member,text]}>{member.name}</Text><Text style={[styles.role,secondary]}>{member.role}</Text><Text style={[styles.body,secondary]}>{member.description}</Text></View>)}</View>
      <View style={styles.section}>{heading('Development Timeline')}<View style={[styles.timeline,{borderLeftColor:c['color-border-paper']}]}>{developmentTimeline.map(item=><View key={item.version} style={styles.release}><View style={[styles.dot,{backgroundColor:c['color-text-primary'],borderColor:c['color-bg-app']}]}/><Text style={[styles.date,secondary]}>{item.date} • {item.version}</Text><Text style={[styles.member,text]}>{item.title}</Text><Text style={[styles.body,secondary]}>{item.description}</Text></View>)}</View></View>
      <View style={styles.section}>{heading('Links')}<Pressable accessibilityRole="link" accessibilityLabel="GitHub Repository" onPress={()=>{setError(false);void openLink(ABOUT_REPOSITORY_URL).catch(()=>setError(true));}} style={[styles.link,{backgroundColor:c['color-bg-paper'],borderColor:c['color-border-paper']}]}>
        <Svg height={18} width={18} viewBox="0 0 16 16" fill={c['color-text-primary']}><Path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></Svg><Text style={[styles.body,text]}>GitHub Repository</Text>
      </Pressable>{error?<Text accessibilityRole="alert" style={[styles.body,{color:c['color-state-error']}]}>{i18n.language.startsWith('zh')?'链接暂时无法打开。':'The link could not be opened. Please retry.'}</Text>:null}</View>
    </ScrollView>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:12,padding:12},button:{minHeight:44,padding:12,justifyContent:'center'},content:{paddingHorizontal:20,paddingTop:28,paddingBottom:120,gap:48},intro:{alignItems:'center',gap:16},brand:{fontFamily:Platform.OS==='ios'?'Georgia':'serif',fontSize:42,fontWeight:'700',letterSpacing:-0.5},summary:{fontSize:18,lineHeight:29,textAlign:'center'},heading:{fontFamily:Platform.OS==='ios'?'Georgia':'serif',fontSize:24,fontWeight:'600'},section:{gap:16},body:{fontSize:16,lineHeight:28},card:{borderWidth:1,borderRadius:8,padding:24,gap:8},member:{fontSize:18,fontWeight:'600'},role:{fontSize:14},timeline:{borderLeftWidth:2,paddingLeft:24,marginLeft:7,gap:32},release:{gap:4},dot:{position:'absolute',left:-30,top:4,width:10,height:10,borderRadius:5,borderWidth:2},date:{fontSize:12},link:{minHeight:44,alignSelf:'flex-start',flexDirection:'row',alignItems:'center',gap:8,paddingVertical:12,paddingHorizontal:20,borderWidth:1,borderRadius:8}});
