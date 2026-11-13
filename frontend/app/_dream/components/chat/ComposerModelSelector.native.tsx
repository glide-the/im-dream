// [Input] Original IM model hook, native authenticated transport and App-owned config refresh.
// [Output] Migrated native SelectModel backed by unchanged catalog, callable checks and save confirmation.
// [Pos] Native presentation adapter; no runtime, model-routing or preference schema ownership.
// [Sync] 2026-11-13: reread saved model/catalog on scene return after any pending save completes.
import {useEffect,useRef,useState} from 'react';
import useModelConfig from '../../hooks/useModelConfig';
import {clientFetch} from '../../../../src/platform/transport';
import {SelectModel} from './SelectModel.native';
import type {ComposerModelSelectorProps} from './modelSelection';
const noBrowserEvent=()=>{};
export default function ComposerModelSelector({onBlockedChange,...props}:ComposerModelSelectorProps){
  const [saveAcknowledged,setSaveAcknowledged]=useState(false);
  const state=useModelConfig({transport:clientFetch,onConfigSaved:()=>{setSaveAcknowledged(true);props.onConfigSaved?.();},onSessionExpired:props.onSessionExpired,onWorkspaceModeChanged:noBrowserEvent,onImFullAccessChanged:noBrowserEvent});
  const wasActive=useRef(props.active!==false);
  useEffect(()=>{
    if(props.active===false){wasActive.current=false;return;}
    if(!wasActive.current&&!state.saving){wasActive.current=true;state.setModelLoadNonce(value=>value+1);}
  },[props.active,state.saving,state.setModelLoadNonce]);
  useEffect(()=>{onBlockedChange?.(state.saving||state.modelSaveUnconfirmed);},[onBlockedChange,state.saving,state.modelSaveUnconfirmed]);
  const error=state.configReadError||state.modelCatalogError||(state.modelSaveUnconfirmed?state.modelStatus:null);
  return <SelectModel models={state.modelOptions} currentModel={state.selectedModel} defaultAlias={state.defaultModelAlias} onSelect={alias=>{setSaveAcknowledged(false);state.handleModelChange(alias);}} onReload={()=>state.setModelLoadNonce(value=>value+1)} loading={state.configLoading} saving={state.saving} disabled={props.disabled} error={error} status={state.modelSaveUnconfirmed||state.saving||saveAcknowledged?null:state.modelStatus} active={props.active}/>;
}
