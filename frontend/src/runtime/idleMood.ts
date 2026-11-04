// [Input] An account-owned, scoped Writing chooser observation with its original date.
// [Output] Today's last observed happy/unhappy expression; absent/other states default to happy.
// [Pos] Memory-only visual projection; no diary reads or writes.
type Mood=Readonly<{sad:boolean;date?:string}>;
const empty:Mood=Object.freeze({sad:false});
let owner:string|undefined,snapshot=empty;
const listeners=new Set<()=>void>();
function publish(value:Mood){snapshot=Object.freeze(value);for(const listener of listeners)listener();}
export const idleMood={
  getSnapshot:()=>snapshot,
  subscribe(listener:()=>void){listeners.add(listener);return()=>{listeners.delete(listener);};},
  setOwner(value:string|undefined){owner=value;publish(empty);},
  observe(actor:string|undefined,state:string|null,createdAt:string|undefined){
    if(!owner||actor!==owner||!createdAt)return;
    const date=new Date(createdAt),today=new Date();if(!Number.isFinite(date.getTime())||date.toDateString()!==today.toDateString())return;
    if(snapshot.date&&date.getTime()<new Date(snapshot.date).getTime())return;
    publish({sad:state==='unhappy',date:date.toISOString()});
  },
};
