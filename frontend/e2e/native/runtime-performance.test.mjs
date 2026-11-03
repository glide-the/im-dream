// [Input] Explicit counters, native read outcomes and a controlled clock passed into the production monitor.
// [Output] CPU/attribution/window/lifecycle contracts without providers, devices or business writes.
// [Pos] Isolated diagnostics technical tests; fixture counters do not represent iPhone heat or overhead.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {measurePerformance,appendPerformance,createPerformanceMonitor,PERFORMANCE_POLICY} from '../../src/runtime/runtimePerformance.ts';
const raw=(overrides={})=>({pid:7,monotonicMs:1000,timestampMs:10000,cpuMs:100,cores:4,thermal:'nominal',simulator:true,collectionWallMs:0.5,collectionCpuMs:0.2,threadsState:'available',threadsTotal:2,threadsTruncated:false,threads:[{id:'1',label:'主线程（共享）',cpuMs:20},{id:'2',label:'其他App线程',cpuMs:30}],activities:[],commandsState:'available',activitiesTruncated:false,...overrides});
const settle=async()=>{for(let i=0;i<5;i++)await Promise.resolve();};
function harness(read,available=true){let next=0;const jobs=new Map(),changes=[];let time=0;const monitor=createPerformanceMonitor({read,available:()=>available,changed:value=>changes.push(value),now:()=>time++,schedule:(fn,ms)=>{assert.ok([PERFORMANCE_POLICY.intervalMs,PERFORMANCE_POLICY.timeoutMs].includes(ms));jobs.set(++next,fn);return next;},cancel:id=>jobs.delete(id)});return {monitor,jobs,changes,async advance(){const entry=jobs.entries().next().value;assert.ok(entry);jobs.delete(entry[0]);entry[1]();await settle();}};}
test('CPU is cumulative CPU delta per elapsed interval; one core=100%, total can exceed 100%',()=>{
 const before=raw(),after=raw({monotonicMs:3000,cpuMs:4100,threads:[{id:'1',label:'主线程（共享）',cpuMs:2020}]});
 const {point}=measurePerformance(after,before,4);assert.equal(point.cpuPercent,200);assert.equal(point.devicePercent,50);assert.equal(point.threads[0].cpuPercent,100);assert.equal(point.requestWallMs,4);
});
test('commands use their mapped OS thread; shared requests never receive allocated CPU',()=>{
 const before=raw(),after=raw({monotonicMs:3000,cpuMs:1100,threads:[{id:'1',label:'主线程（共享）',cpuMs:420}],activities:[{id:'guest:2:1',kind:'command',label:'命令实例',phase:'executing',threadId:'1'},{id:'http:2',kind:'request',label:'Chat请求',phase:'reading'},{id:'guest:3:1',kind:'command',label:'命令实例',phase:'executing',threadId:'new'}]});
 const {point}=measurePerformance(after,before,0);assert.equal(point.activities[0].cpuPercent,20);assert.equal(point.activities[1].cpuPercent,null);assert.equal(point.activities[2].cpuPercent,null);
});
test('new and missing threads remain unmeasured; unavailable thread reads retain process CPU',()=>{
 const after=raw({monotonicMs:3000,cpuMs:300,threads:[{id:'new',label:'其他App线程',cpuMs:9999}]});assert.equal(measurePerformance(after,raw(),0).point.threads[0].cpuPercent,null);
 const point=measurePerformance({...after,threadsState:'unavailable'},raw(),0).point;assert.equal(point.cpuPercent,10);assert.deepEqual(point.threads,[]);
});
test('first sample, clock/counter resets and PID changes form gaps; core-count changes omit normalization',()=>{
 assert.equal(measurePerformance(raw(),undefined,0).point.cpuPercent,null);
 for(const changed of [{monotonicMs:1000},{monotonicMs:500},{monotonicMs:3000,cpuMs:1},{monotonicMs:3000,pid:8}])assert.equal(measurePerformance(raw(changed),raw(),0).point.cpuPercent,null);
 assert.equal(measurePerformance(raw({monotonicMs:3000,cpuMs:300,cores:8}),raw(),0).point.devicePercent,null);
});
test('retention is capped by sample count, elapsed window and process identity',()=>{
 let points=[];for(let i=0;i<300;i++)points=appendPerformance(points,measurePerformance(raw({monotonicMs:1000+i*2000}),undefined,0).point);
 assert.equal(points.length,PERFORMANCE_POLICY.maxSamples);assert.ok(points.at(-1).tick-points[0].tick<=PERFORMANCE_POLICY.retentionMs);
 assert.equal(appendPerformance(points,measurePerformance(raw({pid:8,monotonicMs:900000}),undefined,0).point).length,1);
});
test('invalid counters, capacity, thermal states and core counts fail closed; unknown overhead stays null',()=>{
 for(const changed of [{cpuMs:Infinity},{cpuMs:-1},{cores:0},{thermal:'hot'},{threads:Array(257).fill({id:'1',label:'x',cpuMs:1})}])assert.throws(()=>measurePerformance(raw(changed),undefined,0));
 assert.equal(measurePerformance(raw({collectionCpuMs:null}),undefined,0).point.collectionCpuMs,null);
});
test('multiple visible owners coalesce one native read and one timer; final release stops sampling',async()=>{
 let resolve,calls=0;const h=harness(()=>{calls++;return new Promise(done=>resolve=done);});const a=h.monitor.acquire(true),b=h.monitor.acquire(true);assert.equal(calls,1);resolve(raw());await settle();assert.equal(h.jobs.size,1);a.release();assert.equal(h.jobs.size,1);b.release();assert.equal(h.jobs.size,0);assert.equal(h.monitor.getSnapshot().status,'closed');
});
test('background, hidden views and manual pause release timers; resumed samples establish a fresh baseline',async()=>{
 let tick=0;const h=harness(async()=>raw({monotonicMs:1000+(tick++)*2000,cpuMs:100+tick*10}));const owner=h.monitor.acquire(true);await settle();await h.advance();assert.notEqual(h.monitor.getSnapshot().points.at(-1).cpuPercent,null);
 owner.setActive(false);assert.equal(h.jobs.size,0);assert.equal(h.monitor.getSnapshot().status,'background');owner.setActive(true);await settle();assert.equal(h.monitor.getSnapshot().points.at(-1).cpuPercent,null);
 h.monitor.setPaused(true);assert.equal(h.jobs.size,0);assert.equal(h.monitor.getSnapshot().status,'paused');h.monitor.setPaused(false);await settle();assert.equal(h.monitor.getSnapshot().points.at(-1).cpuPercent,null);owner.release();assert.equal(h.jobs.size,0);
});
test('late native results after release are discarded and cannot resurrect timers',async()=>{
 let resolve;const h=harness(()=>new Promise(done=>resolve=done));const owner=h.monitor.acquire(true);owner.release();resolve(raw());await settle();assert.equal(h.monitor.getSnapshot().points.length,0);assert.equal(h.jobs.size,0);
});
test('a failed sample preserves history, reports failure and retries with a gap',async()=>{
 let attempt=0;const h=harness(async()=>{if(++attempt===2)throw Error('private details');return raw({monotonicMs:attempt*2000,cpuMs:attempt*40});});const owner=h.monitor.acquire(true);await settle();await h.advance();assert.equal(h.monitor.getSnapshot().status,'failed');assert.equal(h.monitor.getSnapshot().points.length,1);assert.ok(!JSON.stringify(h.monitor.getSnapshot()).includes('private details'));await h.advance();assert.equal(h.monitor.getSnapshot().status,'sampling');assert.equal(h.monitor.getSnapshot().points.at(-1).cpuPercent,null);owner.release();
});
test('unavailable native capability performs no reads or scheduling',()=>{
 let calls=0;const h=harness(async()=>{calls++;return raw();},false);const owner=h.monitor.acquire(true);assert.equal(h.monitor.getSnapshot().status,'unavailable');assert.equal(calls,0);assert.equal(h.jobs.size,0);owner.release();
});
test('a stalled native read times out; closing cancels its deadline and a late result cannot replace history',async()=>{
 const resolvers=[];const h=harness(()=>new Promise(resolve=>resolvers.push(resolve)));const owner=h.monitor.acquire(true);assert.equal(h.jobs.size,1);
 await h.advance();assert.equal(h.monitor.getSnapshot().status,'failed');assert.equal(h.jobs.size,1);
 await h.advance();owner.release();await settle();assert.equal(h.jobs.size,0);
 for(const resolve of resolvers)resolve(raw());await settle();assert.equal(h.monitor.getSnapshot().status,'closed');assert.equal(h.monitor.getSnapshot().points.length,0);
});
