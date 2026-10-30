// [Sync] 2026-10-29: use the supported ARIA value aliases across native and RNW accessibility hosts.
// [Input] Original Product API schemas and subscription hook via native HTTP.
// [Output] Existing read-only subscription, Token allowance and available-plan panels.
// [Pos] Native Settings destination; purchases and subscription commands have no page entry.
import {useEffect,useMemo,useRef,useState} from 'react';
import {Platform,Pressable,ScrollView,StyleSheet,Text,View} from 'react-native';
import {useTranslation} from 'react-i18next';
import InkLabel from '../../../../src/components/InkLabel.native';
import useInkColors from '../../../../src/components/useInkColors.native';
import {clientFetch} from '../../../../src/platform/transport';
import {createProductPaymentIntent,fetchProductPaymentIntent,fetchProductPlans,fetchProductSubscriptionContext,submitProductSubscriptionCommand,type CommandPreviewEnvelope,type CommandResultEnvelope,type ExecuteProductCommand,type PreviewProductCommand,type ProductCommand,type ProductCommandRequestOptions,type ProductPlan} from '../../api/productApi';
import {useStoryWorkspaceSubscription,type StoryWorkspaceSubscriptionApi} from '../../hooks/story-workspace/useStoryWorkspaceSubscription';
import {STATUS_LABELS,TABS,formatInteger,formatDate,productErrorPresentation,type SubscriptionTab} from './subscriptionPresentation';
function nativeApi(transport:typeof fetch):StoryWorkspaceSubscriptionApi {
  function command(input:PreviewProductCommand,options?:ProductCommandRequestOptions):Promise<CommandPreviewEnvelope>;
  function command(input:ExecuteProductCommand,options:ProductCommandRequestOptions&{idempotencyKey:string}):Promise<CommandResultEnvelope>;
  function command(input:ProductCommand,options:ProductCommandRequestOptions={}) {
    if(input.phase==='preview')return submitProductSubscriptionCommand(input,{...options,fetchImpl:transport});
    return submitProductSubscriptionCommand(input,{...options,fetchImpl:transport,idempotencyKey:options.idempotencyKey!});
  }
  return {context:options=>fetchProductSubscriptionContext({...options,fetchImpl:transport}),plans:(input,options)=>fetchProductPlans(input,{...options,fetchImpl:transport}),command,
    createPayment:(input,options)=>createProductPaymentIntent(input,{...options,fetchImpl:transport}),payment:(id,options)=>fetchProductPaymentIntent(id,{...options,fetchImpl:transport})};
}
export default function StoryWorkspaceSubscriptionPage({onBack,transport=clientFetch,onSessionExpired}:{onBack:()=>void;transport?:typeof fetch;onSessionExpired?:()=>void}) {
  const {t}=useTranslation(),c=useInkColors(),api=useMemo(()=>nativeApi(transport),[transport]),subscription=useStoryWorkspaceSubscription({api});
  const [activeTab,setActiveTab]=useState<SubscriptionTab>('info'),data=subscription.data;
  const currentPlan=useMemo(()=>{const code=data?.context.data.planVersion?.planCode;return code?data?.plans.data.find(plan=>plan.planCode===code)??null:null;},[data]);
  const expired=useRef(onSessionExpired);expired.current=onSessionExpired;
  useEffect(()=>{if(subscription.error?.status===401)expired.current?.();},[subscription.error]);
  const text={color:c['color-text-primary']},secondary={color:c['color-text-secondary']},card=[styles.card,{backgroundColor:c['color-bg-paper'],borderColor:c['color-border-paper']}];
  const button=(label:string,action:()=>void,disabled=false)=><Pressable accessibilityRole="button" disabled={disabled} onPress={action} style={[styles.button,{borderColor:c['color-border-paper'],opacity:disabled?0.5:1}]}><InkLabel style={text}>{label}</InkLabel></Pressable>;
  const heading=(label:string)=><Text accessibilityRole="header" style={[styles.heading,text]}>{label}</Text>;
  const empty=(title:string,description:string)=><View style={card}>{heading(title)}<InkLabel style={secondary}>{description}</InkLabel></View>;
  const error=subscription.error?productErrorPresentation(subscription.error):null;
  const context=data?.context.data,current=context?.subscription,allowance=context?.allowance,resetDate=allowance?.resetsAt??current?.currentPeriodEnd;
  const planNote=currentPlan?.note??'为持续创作保留一处安静的工作空间。';
  const consumedPercent=allowance&&allowance.granted>0?Math.min(100,Math.max(0,(allowance.consumed/allowance.granted)*100)):0;
  function planCard(plan:ProductPlan){const isCurrent=context?.planVersion?.planCode===plan.planCode;return <View key={plan.planCode} style={card}>
    <InkLabel style={secondary}>{plan.eyebrow}</InkLabel><InkLabel style={text}>{isCurrent?'当前套餐':!plan.available||!plan.eligibility.eligible?'暂不可开通':'可以开通'}</InkLabel>
    {heading(plan.planName)}<InkLabel style={secondary}>{plan.note}</InkLabel>{plan.details.map(detail=><InkLabel key={detail} style={text}>{`• ${detail}`}</InkLabel>)}
    {plan.monthlyAllowanceTokens!==null?<InkLabel style={text}>{`每月 ${formatInteger(plan.monthlyAllowanceTokens)} Token`}</InkLabel>:null}
  </View>;}
  return <View style={[styles.fill,{backgroundColor:c['color-bg-app']}]}>
    <View style={styles.header}>{button(t('settings.workspace.preferences.back'),onBack)}<InkLabel accessibilityRole="header" style={[text,{fontSize:22}]}>{t('settings.workspace.navigation.subscription')}</InkLabel></View>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <InkLabel style={secondary}>Dream · Subscription</InkLabel>{heading(context?.planVersion?.planName??currentPlan?.planName??'订阅')}
      <InkLabel style={secondary}>{data?planNote:subscription.isLoading?'正在读取你的套餐与额度。':'查看你的套餐与本周期额度。'}</InkLabel>
      {data?<><InkLabel style={secondary}>{`额度将在 ${formatDate(resetDate)} 更新`}</InkLabel>{button(subscription.isRefreshing?'正在更新…':'重新读取',subscription.refetch,subscription.isRefreshing)}{button('查看可选套餐',()=>setActiveTab('plans'))}</>:null}
      {subscription.isLoading&&!data?<InkLabel accessibilityLiveRegion="polite" style={secondary}>正在读取订阅</InkLabel>:null}
      {error?<View accessibilityRole="alert" style={card}>{heading(error.title)}<InkLabel style={secondary}>{`${error.description} ${error.recovery}`}</InkLabel>{button('重新读取',subscription.refetch)}</View>:null}
      {data?<>
        <View accessibilityRole="tablist" accessibilityLabel="订阅内容" style={styles.tabs}>{TABS.map(tab=><Pressable key={tab.id} accessibilityRole="tab" accessibilityState={{selected:activeTab===tab.id}} aria-selected={activeTab===tab.id} onPress={()=>setActiveTab(tab.id)} style={[styles.button,{backgroundColor:activeTab===tab.id?c['color-bg-hover']:'transparent',borderColor:c['color-border-paper']}]}><InkLabel style={text}>{tab.label}</InkLabel></Pressable>)}</View>
        <View accessibilityLabel={TABS.find(tab=>tab.id===activeTab)?.label}>
          {activeTab==='info'?(current&&context?.planVersion?<View style={card}><InkLabel style={secondary}>当前套餐</InkLabel>{heading(context.planVersion.planName)}<InkLabel style={text}>{STATUS_LABELS[current.status]??'当前套餐'}</InkLabel><InkLabel style={secondary}>{planNote}</InkLabel>{currentPlan?.details.map(detail=><InkLabel key={detail} style={text}>{`• ${detail}`}</InkLabel>)}<InkLabel style={secondary}>{`按月更新 · 下次更新 ${formatDate(resetDate)}`}</InkLabel></View>:empty('当前没有有效订阅','查看可选套餐，选择适合你的创作空间。')):null}
          {activeTab==='allowance'?(allowance?<View style={card}><InkLabel style={secondary}>本周期可用</InkLabel>{heading(`${formatInteger(allowance.remaining)} Token`)}<InkLabel style={text}>{`已使用 ${formatInteger(allowance.consumed)} / ${formatInteger(allowance.granted)}`}</InkLabel>
            <View accessibilityRole="progressbar" accessibilityLabel={`已使用 ${Math.round(consumedPercent)}%`} aria-valuemin={0} aria-valuemax={allowance.granted} aria-valuenow={allowance.consumed} style={[styles.progress,{backgroundColor:c['color-bg-hover']}]}><View style={{width:`${consumedPercent}%`,height:6,backgroundColor:c['color-action-primary']}}/></View>
            <InkLabel style={secondary}>{`${Math.round(consumedPercent)}% 已使用 · ${formatDate(allowance.resetsAt)} 后更新`}</InkLabel></View>:empty('额度暂不可用','当前没有可展示的月度 Token 额度。')):null}
          {activeTab==='plans'?<View style={styles.plans}><InkLabel style={secondary}>A place for stories to keep growing</InkLabel>{heading('为正在形成的故事留出空间')}<InkLabel style={secondary}>未完成商业配置的套餐会保留展示，但不会伪造价格或开通结果。</InkLabel>{data.plans.data.length?data.plans.data.map(planCard):empty('暂时没有可选套餐','稍后重新读取；页面不会显示本地套餐。')}</View>:null}
        </View>
        <InkLabel accessibilityLiveRegion="polite" style={styles.announcement}>{subscription.announcement}</InkLabel>
      </>:null}
    </ScrollView>
  </View>;
}
const styles=StyleSheet.create({fill:{flex:1,minHeight:0},header:{flexDirection:'row',alignItems:'center',gap:12,padding:12},content:{padding:20,gap:16,paddingBottom:32},heading:{fontFamily:Platform.OS==='ios'?'Georgia':'serif',fontSize:24,fontWeight:'600'},card:{gap:12,padding:16,borderWidth:1,borderRadius:16},button:{minHeight:44,padding:12,justifyContent:'center',borderRadius:12,borderWidth:StyleSheet.hairlineWidth},tabs:{flexDirection:'row',flexWrap:'wrap',gap:8},progress:{height:6,borderRadius:3,overflow:'hidden'},plans:{gap:16},announcement:{height:1,width:1,overflow:'hidden'}});
