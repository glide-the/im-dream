// [Input] Production idle deadline, account presence and dated mood projections with an injected clock.
// [Output] Boundary, race, foreground, account and missing-observation contracts.
// [Pos] Provider-free technical tests; production policy stays 25 seconds, no service/model/data operations.
import {test,expect} from '@playwright/test';
import {createIdleScreenSaver,IDLE_SCREEN_SAVER_DELAY_MS} from '../src/runtime/idleScreenSaver';
import {createThreadPresenceStore} from '../src/runtime/threadPresence';
import {idleMood} from '../src/runtime/idleMood';

function fixture(eligible:()=>boolean|Promise<boolean>=()=>true){
 let now=0,id=0;
 const pending=new Map<number,{at:number;run:()=>void}>(),states:boolean[]=[];
 const controller=createIdleScreenSaver({changed:value=>states.push(value),eligible,time:{now:()=>now,
  set:(run,delay)=>{const key=++id;pending.set(key,{at:now+delay,run});return key as unknown as ReturnType<typeof setTimeout>;},
  clear:key=>{pending.delete(key as unknown as number);}}});
 return {controller,states,pending,async advance(ms:number){now+=ms;const due=[...pending].filter(([,value])=>value.at<=now);for(const [key,value]of due){pending.delete(key);value.run();}await Promise.resolve();await Promise.resolve();}};
}

test('25-second boundary and genuine interaction reset one deadline',async()=>{
 const f=fixture();f.controller.availability(true,false);
 await f.advance(IDLE_SCREEN_SAVER_DELAY_MS-1);expect(f.states).toEqual([]);
 f.controller.activity();expect(f.pending.size).toBe(1);
 await f.advance(1);expect(f.states).toEqual([]);
 await f.advance(IDLE_SCREEN_SAVER_DELAY_MS-1);expect(f.states).toEqual([true]);expect(f.pending.size).toBe(0);
 f.controller.activity();expect(f.states).toEqual([true]);
 f.controller.dismiss();expect(f.states).toEqual([true,false]);expect(f.pending.size).toBe(1);
 f.controller.dispose();expect(f.pending.size).toBe(0);
});

test('a late eligibility result cannot cover a new modal or a backgrounded page',async()=>{
 let release!:(allowed:boolean)=>void;
 const f=fixture(()=>new Promise<boolean>(resolve=>{release=resolve;}));f.controller.availability(true,false);
 await f.advance(IDLE_SCREEN_SAVER_DELAY_MS);f.controller.availability(true,true);release(true);await Promise.resolve();
 expect(f.states).toEqual([]);expect(f.pending.size).toBe(0);
 f.controller.availability(true,false);await f.advance(IDLE_SCREEN_SAVER_DELAY_MS);f.controller.availability(false,false);release(true);await Promise.resolve();
 expect(f.states).toEqual([]);expect(f.pending.size).toBe(0);
 f.controller.dispose();
});

test('foreground return starts a fresh deadline and background removes the visible layer',async()=>{
 const f=fixture();f.controller.availability(true,false);await f.advance(IDLE_SCREEN_SAVER_DELAY_MS);expect(f.states).toEqual([true]);
 f.controller.availability(false,false);expect(f.states).toEqual([true,false]);expect(f.pending.size).toBe(0);
 await f.advance(100_000);expect(f.pending.size).toBe(0);
 f.controller.availability(true,false);await f.advance(IDLE_SCREEN_SAVER_DELAY_MS-1);expect(f.states).toEqual([true,false]);
 f.controller.dispose();await f.advance(1);expect(f.states).toEqual([true,false]);
});

test('shared presence preserves true until an authoritative false and isolates account changes',()=>{
 const store=createThreadPresenceStore();store.setOwner('first');
 expect(store.getSnapshot()).toEqual({known:false});
 store.accept({known:true,ownerId:'first',hasActiveThread:true,observedAt:20});
 const current=store.getSnapshot();store.accept({error:'unavailable'});expect(store.getSnapshot()).toBe(current);
 store.accept({known:true,ownerId:'foreign',hasActiveThread:false,observedAt:30});expect(store.getSnapshot()).toBe(current);
 store.accept({known:true,ownerId:'first',hasActiveThread:false,observedAt:19});expect(store.getSnapshot()).toBe(current);
 store.accept({known:true,ownerId:'first',hasActiveThread:false,observedAt:21});expect(store.getSnapshot()).toMatchObject({known:true,hasActiveThread:false});
 store.setOwner('second');store.accept({known:true,ownerId:'first',hasActiveThread:true,observedAt:50});expect(store.getSnapshot()).toEqual({known:false});
});

test('today mood consumes original state IDs and cannot cross an account or note date',()=>{
 const today=new Date().toISOString(),yesterday=new Date(Date.now()-86_400_000).toISOString();
 idleMood.setOwner('first');idleMood.observe('first','unhappy',today);expect(idleMood.getSnapshot().sad).toBe(true);
 idleMood.observe('other','happy',today);expect(idleMood.getSnapshot().sad).toBe(true);
 idleMood.observe('first','happy',yesterday);expect(idleMood.getSnapshot().sad).toBe(true);
 idleMood.setOwner('second');expect(idleMood.getSnapshot().sad).toBe(false);
});
