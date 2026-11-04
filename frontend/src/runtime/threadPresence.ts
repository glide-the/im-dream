// [Input] Native-verified account observations and the current authenticated UI owner.
// [Output] An immutable shared binary snapshot; missing observations remain absent.
// [Pos] Display projection only; no networking, task controls or persistence.
export type ThreadPresence = Readonly<{known:false}|{known:true;ownerId:string;hasActiveThread:boolean;observedAt:number}>;
const absent:ThreadPresence=Object.freeze({known:false});
export function createThreadPresenceStore() {
  let owner:string|undefined;
  let snapshot:ThreadPresence=absent;
  const listeners=new Set<()=>void>();
  function publish(value:ThreadPresence){snapshot=Object.freeze(value);for(const listener of listeners)listener();}
  return {
    getSnapshot:()=>snapshot,
    subscribe(listener:()=>void){listeners.add(listener);return()=>{listeners.delete(listener);};},
    setOwner(value:string|undefined){owner=value;publish(absent);},
    accept(value:unknown){
      if(!owner||!value||typeof value!=='object')return;
      const row=value as Record<string,unknown>;
      if(row.known===false){publish(absent);return;}
      if(row.known!==true||row.ownerId!==owner||typeof row.hasActiveThread!=='boolean'||typeof row.observedAt!=='number'||!Number.isFinite(row.observedAt))return;
      if(snapshot.known&&row.observedAt<snapshot.observedAt)return;
      publish({known:true,ownerId:owner,hasActiveThread:row.hasActiveThread,observedAt:row.observedAt});
    },
  };
}
