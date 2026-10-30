// [Input] Original General settings fields, theme preference and authenticated HTTP.
// [Output] Native language, appearance and Energy Bar controls with the original persistence scopes.
// [Pos] Native General settings content; caller retains navigation, runtime and conversation ownership.
import {useState} from 'react';
import {Pressable,ScrollView,StyleSheet,Switch,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors,{useNativeThemeMode} from '../../../../src/components/useInkColors.native';
import {getShowEnergyBar,INTERFACE_LANGUAGE_CODES,setInterfaceLanguage,setShowEnergyBar} from '../../../../src/platform/interfacePreferences.native';
import {clientFetch} from '../../../../src/platform/transport';
import {browserRequestHeaders} from '../../lib/browserSession';
import {API_BASE} from '../../lib/apiBase';
import {setThemeMode,type ThemeMode} from '../../utils/theme.native';
const THEME_OPTIONS=['light','system','dark'] as const;
export default function GeneralSettings({onBack,transport=clientFetch,onSessionExpired}:{onBack:()=>void;transport?:typeof fetch;onSessionExpired?:()=>void}) {
  const {t,i18n}=useTranslation(),colors=useInkColors(),theme=useNativeThemeMode();
  const [showEnergy,setEnergy]=useState(getShowEnergyBar),[error,setError]=useState('');
  const text={color:colors['color-text-primary']},secondary={color:colors['color-text-secondary']};
  const language=(i18n.resolvedLanguage??i18n.language??'en').split('-')[0];
  async function selectTheme(mode:ThemeMode) {
    setError('');
    try{setThemeMode(mode);}catch{setError(t('settings.workspace.preferences.localSaveFailed'));return;}
    try {
      // The existing General action applies locally before its original config PUT.
      const response=await transport(`${API_BASE}/api/system-config`,{method:'PUT',headers:{'Content-Type':'application/json',...browserRequestHeaders()},body:JSON.stringify({theme:mode})});
      if(response.status===401)onSessionExpired?.();
      if(!response.ok)setError(t('settings.workspace.preferences.saveUnconfirmed'));
    }catch{setError(t('settings.workspace.preferences.saveUnconfirmed'));}
  }
  async function selectLanguage(code:string) {
    setError('');try{await setInterfaceLanguage(code);}catch{setError(t('settings.workspace.preferences.localSaveFailed'));}
  }
  function toggleEnergy(value:boolean) {
    setError('');try{setShowEnergyBar(value);setEnergy(value);}catch{setError(t('settings.workspace.preferences.localSaveFailed'));}
  }
  return <View style={[styles.fill,{backgroundColor:colors['color-bg-app']}]}>
    <View style={styles.header}><Pressable accessibilityRole="button" onPress={onBack} style={styles.button}><InkLabel style={text}>{t('settings.workspace.preferences.back')}</InkLabel></Pressable><InkLabel accessibilityRole="header" style={[text,{fontSize:22}]}>{t('settings.workspace.navigation.general')}</InkLabel></View>
    <ScrollView contentContainerStyle={styles.content}>
      <InkLabel style={secondary}>{t('settings.workspace.general.description')}</InkLabel>
      {error?<InkLabel accessibilityRole="alert" style={{color:colors['color-state-error']}}>{error}</InkLabel>:null}
      <View style={[styles.card,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}>
        <InkLabel style={[text,styles.label]}>{t('settings.workspace.languageLabel')}</InkLabel><InkLabel style={secondary}>{t('settings.language.description')}</InkLabel>
        <View accessibilityRole="radiogroup" accessibilityLabel={t('settings.workspace.languageLabel')} style={styles.options}>{INTERFACE_LANGUAGE_CODES.map(code=><Pressable key={code} accessibilityRole="radio" accessibilityState={{checked:language===code}} aria-checked={language===code} onPress={()=>void selectLanguage(code)} style={[styles.button,language===code?{backgroundColor:colors['color-bg-hover']}:undefined]}><InkLabel style={text}>{t(`settings.language.options.${code}`)}</InkLabel></Pressable>)}</View>
        <InkLabel style={secondary}>{t('settings.language.preview')}</InkLabel>
      </View>
      <View style={[styles.card,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}>
        <InkLabel style={[text,styles.label]}>{t('settings.workspace.theme.label')}</InkLabel><InkLabel style={secondary}>{t('settings.workspace.theme.description')}</InkLabel>
        <View accessibilityRole="radiogroup" accessibilityLabel={t('settings.workspace.theme.label')} style={styles.options}>{THEME_OPTIONS.map(mode=><Pressable key={mode} accessibilityRole="radio" accessibilityState={{checked:theme===mode}} aria-checked={theme===mode} onPress={()=>void selectTheme(mode)} style={[styles.button,theme===mode?{backgroundColor:colors['color-bg-hover']}:undefined]}><InkLabel style={text}>{t(`settings.workspace.theme.options.${mode}`)}</InkLabel></Pressable>)}</View>
      </View>
      <View style={[styles.card,{backgroundColor:colors['color-bg-paper'],borderColor:colors['color-border-paper']}]}>
        <InkLabel style={[text,styles.label]}>{t('settings.workspace.energy.label')}</InkLabel><InkLabel style={secondary}>{t('settings.workspace.energy.description')}</InkLabel>
        <Switch accessibilityLabel={t('settings.workspace.energy.toggleLabel')} value={showEnergy} onValueChange={toggleEnergy}/>
      </View>
    </ScrollView>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:12,paddingHorizontal:12},content:{padding:20,gap:16,paddingBottom:32},card:{gap:10,padding:16,borderWidth:1,borderRadius:16},label:{fontSize:18},options:{flexDirection:'row',flexWrap:'wrap',gap:8},button:{minHeight:44,padding:12,justifyContent:'center',borderRadius:12}});
