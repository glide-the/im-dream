// [Sync] 2026-10-29: lock one initial production-build GET while editing before the explicit save.
// [Input] Production Settings UI with externally injected, strict public memory DTO responses.
// [Output] Desktop/narrow save, conflict, unknown result, reload and read failure journeys.
// [Pos] Provider-free browser validation; no normal account/database/model mutation.
// [Sync] 2026-10-15: validate the sole new L3 behavior page through visible controls.
// Business impact: memory desired/revision and save receipts change only inside fixtures.
// Reflections reports, Project/Episode, canonical Story artifacts, Run .dream and after-turn Hook are out of scope.
import { expect,test,type Page } from '@playwright/test';
import { installFixtures,WEB_BASE } from './fixtures/calendarHarness';
test.use({channel:'chrome'});test.setTimeout(60_000);
const themes=[
 {id:'THEME_FRUSTRATION',label:'挫败',default_action:'acknowledge_then_help',actions:['acknowledge_then_help','help_only','ask_support_type']},
 {id:'THEME_DEFENSE',label:'防御',default_action:'respect_distance',actions:['respect_distance','help_only','ask_support_type']},
 {id:'THEME_PRESSURE',label:'压力',default_action:'prioritize_actions',actions:['prioritize_actions','acknowledge_then_help','ask_support_type']},
 {id:'THEME_VALUE',label:'价值',default_action:'connect_goal_to_choice',actions:['connect_goal_to_choice','acknowledge_only','help_only']},
];
const desired={enabled:false,themes:Object.fromEntries(themes.map(t=>[t.id,{enabled:true,action:t.default_action}]))};
async function fixture(page:Page,mode:'normal'|'unknown'|'conflict'|'read-fail'='normal') {
 const base=await installFixtures(page,{authEntryLifecycle:true,memorySettingsLifecycle:true});
 let snapshot={owner_id:'memory-fixture-user',revision:0,taxonomy_revision:'memory-rules-v1',default:desired,desired:structuredClone(desired),catalog:themes,updated_at:null as string|null};
 const requests:{id:string;body:{expected_revision:number;desired:typeof desired}}[]=[];
 let fault=mode==='read-fail';
 let reads=0;
 await page.route('**/api/memory/behavior**',async route=>{
  const req=route.request();
  if(req.method()==='GET'&&new URL(req.url()).pathname.includes('/receipt/')) {await route.fulfill({json:{status:'committed',result:snapshot}});return;}
  if(req.method()==='GET') {reads++;if(fault){await route.fulfill({status:503,json:{detail:'unavailable'}});}else await route.fulfill({json:snapshot});return;}
  const body=req.postDataJSON();requests.push({id:req.headers()['x-request-id'],body});
  if(mode==='conflict'){await route.fulfill({status:409,json:{detail:{error_code:'MEMORY_SETTINGS_CONFLICT',outcome_unknown:false}}});return;}
  snapshot={...snapshot,revision:1,desired:body.desired,updated_at:'2026-10-15T01:00:00Z'};
  if(mode==='unknown'){await route.fulfill({status:503,json:{detail:{error_code:'ADMIN_OPERATION_UNAVAILABLE',outcome_unknown:true}}});return;}
  await route.fulfill({json:snapshot});
 });
 return {base,requests,getReadCount:()=>reads,recoverRead:()=>{fault=false;}};
}
async function open(page:Page) {
 await page.goto(`${WEB_BASE}/story-workspace/settings/behavior`);
 await expect(page.getByRole('heading',{name:'记忆回应',exact:true})).toBeVisible();
}
test('desktop save, exact desired payload and persisted reopen',async({page})=>{
 const lane=await fixture(page);await open(page);
 const enabled=page.getByRole('checkbox',{name:'使用回顾记忆调整回应'});await expect(enabled).not.toBeChecked();
 await enabled.check();await page.getByRole('combobox',{name:'压力 回应方式'}).selectOption('acknowledge_then_help');
 expect(lane.getReadCount()).toBe(1);
 await page.getByRole('button',{name:'保存',exact:true}).click();
 await expect(page.getByRole('status')).toHaveText('已保存，下一次回应使用此设置。');
 await page.screenshot({path:'/private/tmp/ink-l2-l3-memory-behavior-desktop-20261015.png',fullPage:true});
 expect(lane.requests).toHaveLength(1);expect(lane.requests[0].body.expected_revision).toBe(0);expect(lane.requests[0].body.desired.enabled).toBe(true);expect(lane.requests[0].id).toMatch(/^[0-9a-f-]{36}$/);
 await page.reload();await expect(enabled).toBeChecked();await expect(page.getByRole('combobox',{name:'压力 回应方式'})).toHaveValue('acknowledge_then_help');
 expect(lane.base.getUnexpected()).toEqual([]);
});
test('unknown save result survives reopen and receipt check without second write',async({page})=>{
 const lane=await fixture(page,'unknown');await open(page);
 await page.getByRole('checkbox',{name:'使用回顾记忆调整回应'}).check();await page.getByRole('button',{name:'保存',exact:true}).click();
 await expect(page.locator('.memory-behavior').getByRole('alert')).toContainText('尚未核实');await page.reload();
 await page.getByRole('button',{name:'核实保存结果'}).click();await expect(page.getByRole('status')).toContainText('已保存');
 expect(lane.requests).toHaveLength(1);
});
test('conflict preserves draft and explicit reload recovers current settings',async({page})=>{
 await fixture(page,'conflict');await open(page);
 const enabled=page.getByRole('checkbox',{name:'使用回顾记忆调整回应'});await enabled.check();await page.getByRole('button',{name:'保存',exact:true}).click();
 await expect(page.locator('.memory-behavior').getByRole('alert')).toContainText('草稿已保留');await expect(enabled).toBeChecked();
 await page.getByRole('button',{name:'读取最新设置'}).click();await expect(enabled).not.toBeChecked();
});
test('narrow keyboard controls and read failure recovery have no horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});const lane=await fixture(page,'read-fail');await open(page);
 await expect(page.locator('.memory-behavior').getByRole('alert')).toContainText('无法读取');lane.recoverRead();await page.getByRole('button',{name:'重新读取'}).click();
 const enabled=page.getByRole('checkbox',{name:'使用回顾记忆调整回应'});await enabled.focus();await page.keyboard.press('Space');await expect(enabled).toBeChecked();
 await page.getByRole('button',{name:'保存',exact:true}).click();await expect(page.getByRole('status')).toContainText('已保存');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:'/private/tmp/ink-l2-l3-memory-behavior-narrow-20261015.png',fullPage:true});
});
