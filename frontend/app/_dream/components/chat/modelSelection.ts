// [Input] IM's validated Gateway catalog, saved alias and caller-owned selection/reload callbacks.
// [Output] Presentation props and searchable protocol groups for migrated SelectModel components.
// [Pos] UI projection only; callable/default/entitlement and persistence stay with gatewayModelsApi/useModelConfig.
import type {GatewayModel} from '../../api/gatewayModelsApi';
export interface SelectModelProps {
  models:GatewayModel[];currentModel:string;defaultAlias:string|null;
  onSelect:(alias:string)=>void;onReload:()=>void;
  loading:boolean;disabled?:boolean;saving:boolean;error?:string|null;status?:string|null;active?:boolean;
}
export interface ComposerModelSelectorProps {
  disabled?:boolean;active?:boolean;onConfigSaved?:()=>void;onSessionExpired?:()=>void;
  onBlockedChange?:(blocked:boolean)=>void;
}
export function modelMenuGroups(models:GatewayModel[],query:string){
  const filtered=models.filter(model=>(model.displayName+' '+model.modelAlias).toLowerCase().includes(query.trim().toLowerCase()));
  return [...new Set(filtered.map(model=>model.protocol))].map(provider=>({provider,models:filtered.filter(model=>model.protocol===provider)}));
}
