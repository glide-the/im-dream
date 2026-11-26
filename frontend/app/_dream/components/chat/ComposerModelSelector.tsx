// [Input] Original useModelConfig owner and caller save/session/send-block callbacks.
// [Output] Migrated SelectModel UI backed by IM catalog, selection, entitlement and confirmed save behavior.
// [Pos] Presentation adapter only; Settings and Chat share the existing model data/HTTP implementation.
// [Sync] 2026-11-13: reread saved model/catalog on scene return after any pending save completes.
import {useEffect,useRef,useState} from 'react';
import useModelConfig from '../../hooks/useModelConfig';
import {SelectModel} from './SelectModel';
import type {ComposerModelSelectorProps} from './modelSelection';
export default function ComposerModelSelector({onBlockedChange,...props}:ComposerModelSelectorProps){
  const [saveAcknowledged,setSaveAcknowledged]=useState(false);
  const state=useModelConfig({onConfigSaved:()=>{setSaveAcknowledged(true);props.onConfigSaved?.();},onSessionExpired:props.onSessionExpired});
  const wasActive=useRef(props.active!==false);
  useEffect(()=>{
    if(props.active===false){wasActive.current=false;return;}
    if(!wasActive.current&&!state.saving){wasActive.current=true;state.setModelLoadNonce(value=>value+1);}
  },[props.active,state.saving,state.setModelLoadNonce]);
  useEffect(()=>{onBlockedChange?.(state.saving||state.modelSaveUnconfirmed);},[onBlockedChange,state.saving,state.modelSaveUnconfirmed]);
  const error=state.configReadError||state.modelCatalogError||(state.modelSaveUnconfirmed?state.modelStatus:null);
  return <SelectModel models={state.modelOptions} currentModel={state.selectedModel} defaultAlias={state.defaultModelAlias} onSelect={alias=>{setSaveAcknowledged(false);state.handleModelChange(alias);}} onReload={()=>state.setModelLoadNonce(value=>value+1)} loading={state.configLoading} saving={state.saving} disabled={props.disabled} error={error} status={state.modelSaveUnconfirmed||state.saving||saveAcknowledged?null:state.modelStatus} active={props.active}/>;
}
