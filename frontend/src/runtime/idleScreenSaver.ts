// [Input] Genuine user interaction, foreground/blocked facts and a cancellable clock.
// [Output] One idle deadline and overlay visibility without changing page or task state.
// [Pos] App presentation policy; 25 seconds is the user-specified Notion requirement.
export const IDLE_SCREEN_SAVER_DELAY_MS=25_000;
type Clock={now:()=>number;set:(run:()=>void,delay:number)=>ReturnType<typeof setTimeout>;clear:(timer:ReturnType<typeof setTimeout>)=>void};
const clock:Clock={now:()=>performance.now(),set:(run,delay)=>setTimeout(run,delay),clear:clearTimeout};
export function createIdleScreenSaver({changed,eligible,delay=IDLE_SCREEN_SAVER_DELAY_MS,time=clock}:{changed:(visible:boolean)=>void;eligible:()=>boolean|Promise<boolean>;delay?:number;time?:Clock}) {
  let active=false,blocked=true,visible=false,disposed=false,epoch=0,last=time.now(),timer:ReturnType<typeof setTimeout>|undefined;
  function cancel(){epoch++;if(timer!==undefined)time.clear(timer);timer=undefined;}
  function show(value:boolean){if(visible!==value){visible=value;changed(value);}}
  function arm(){cancel();if(disposed||!active||blocked||visible)return;const version=epoch;
    timer=time.set(()=>{timer=undefined;void(async()=>{
      const remaining=delay-(time.now()-last);if(remaining>0){arm();return;}
      let allowed=false;try{allowed=await eligible();}catch{/* Uncertain input/modal ownership delays the overlay. */}
      if(disposed||version!==epoch||!active||blocked)return;
      if(allowed)show(true);else{last=time.now();arm();}
    })();},Math.max(0,delay-(time.now()-last)));
  }
  return {
    activity(){if(visible||disposed)return;last=time.now();arm();},
    dismiss(){if(disposed)return;show(false);last=time.now();arm();},
    availability(nextActive:boolean,nextBlocked:boolean){if(active===nextActive&&blocked===nextBlocked&&!disposed)return;disposed=false;active=nextActive;blocked=nextBlocked;cancel();show(false);last=time.now();arm();},
    dispose(){disposed=true;cancel();visible=false;},
  };
}
