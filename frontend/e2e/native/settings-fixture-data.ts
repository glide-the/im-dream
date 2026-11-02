// [Input] Synthetic Memory and Product DTOs shaped by the original public schemas.
// [Output] Shared browser/Hermes settings fixture data only.
// [Pos] Technical fixture; values do not describe a real user, subscription or release.
const catalog=[
{id:'THEME_FRUSTRATION',label:'挫败',default_action:'acknowledge_then_help',actions:['acknowledge_then_help','help_only','ask_support_type']},
{id:'THEME_DEFENSE',label:'防御',default_action:'respect_distance',actions:['respect_distance','help_only','ask_support_type']},
{id:'THEME_PRESSURE',label:'压力',default_action:'prioritize_actions',actions:['prioritize_actions','acknowledge_then_help','ask_support_type']},
{id:'THEME_VALUE',label:'价值',default_action:'connect_goal_to_choice',actions:['connect_goal_to_choice','acknowledge_only','help_only']}];
const desired={enabled:false,themes:Object.fromEntries(catalog.map(theme=>[theme.id,{enabled:true,action:theme.default_action}]))};
const initial={owner_id:'7',revision:0,taxonomy_revision:'memory-rules-v1',default:desired,desired:JSON.parse(JSON.stringify(desired)),catalog,updated_at:null};
const timestamp='2026-10-29T00:00:00Z',next='2026-11-29T00:00:00Z';
const activePlan={planCode:'free',planName:'Free',eyebrow:'A quiet beginning',note:'从一段创作目标开始',details:['查看已有 Deck','保留原有创作内容'],description:null,planVersionId:'pv_free',version:1,versionStatus:'published',billingCycle:'monthly',monthlyAllowanceTokens:100000,monthlyPriceMicrousd:0,currency:'USD',available:true,unavailableReason:null,entitlements:[],eligibility:{eligible:true,reasonCode:null,appliesAt:null},availableActions:[]};
const pendingPlan={...activePlan,planCode:'dream',planName:'Dream',planVersionId:null,version:null,versionStatus:null,monthlyAllowanceTokens:null,monthlyPriceMicrousd:null,available:false,unavailableReason:'configuration_incomplete',eligibility:{eligible:false,reasonCode:'PLAN_NOT_AVAILABLE',appliesAt:null}};
const context={data:{canonicalUser:{id:'7'},subscription:{id:'sub_fixture',status:'active',version:1,cycleAnchorAt:timestamp,currentPeriodNumber:0,currentPeriodStart:timestamp,currentPeriodEnd:next,renewalEnabled:true,cancelAtPeriodEnd:false,pendingChange:null,allowedActions:[]},planVersion:{planCode:'free',planName:'Free',planVersionId:'pv_free',version:1,billingCycle:'monthly',monthlyAllowanceTokens:100000,monthlyPriceMicrousd:0,currency:'USD'},entitlements:[],allowance:{unit:'tokens',granted:100000,reserved:1000,consumed:24000,remaining:75000,resetsAt:next},asOf:timestamp},meta:{requestId:'context_fixture'}};
const plans={data:[activePlan,pendingPlan],meta:{total:2,page:1,pageSize:20,requestId:'plans_fixture'}};

export {initial as memorySnapshot,context as subscriptionContext,plans as subscriptionPlans,timestamp};
