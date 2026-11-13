// [Sync] 2026-11-13: use the shared close icon with explicit Chinese UI text metrics.
// SPDX-License-Identifier: MIT
// Copyright (c) 2025 better-chatbot. Adapted from components/select-model.tsx (66d816b04fd68b5240937c83ade50b478c9f4521).
// Full notice and original source: frontend/third-party/better-chatbot/.
// [Input] Original IM model catalog, saved selection and save/reload state.
// [Output] Migrated searchable grouped model menu, current check, disabled choices and Popover/Drawer presentation.
// [Pos] UI adapter for upstream SelectModel; IM data and authorization remain caller-owned.
import {useCallback,useEffect,useId,useMemo,useRef,useState} from 'react';
import {useTranslation} from 'react-i18next';
import type {GatewayModel} from '../../api/gatewayModelsApi';
import {modelMenuGroups,type SelectModelProps} from './modelSelection';
import ComposerPopover from './ComposerPopover';
import {IconCheck,IconChevronDown,IconLoader,IconX} from './Icons';
import './SelectModel.css';

export function SelectModel(props:SelectModelProps){
  const {t}=useTranslation(),[open,setOpen]=useState(false),trigger=useRef<HTMLButtonElement>(null);
  const selected=props.models.find(model=>model.modelAlias===props.currentModel);
  const close=useCallback(()=>{setOpen(false);trigger.current?.focus();},[]);
  useEffect(()=>{if(props.active===false)setOpen(false);},[props.active]);
  return <div className="model-selector">
    <button ref={trigger} type="button" className="model-selector__trigger" data-testid="model-selector-button" disabled={props.disabled||props.saving} aria-label={t('chat.modelMenu.trigger',{name:selected?.displayName||props.currentModel||t('chat.modelMenu.title')})} aria-expanded={open} aria-busy={props.loading||props.saving} aria-haspopup="dialog" onClick={()=>setOpen(value=>!value)}>
      {props.loading||props.saving?<IconLoader className="spin" aria-hidden="true"/>:null}<span data-testid="selected-model-name">{selected?.displayName||props.currentModel||t(props.loading?'chat.modelMenu.loading':'chat.modelMenu.title')}</span><IconChevronDown aria-hidden="true"/>
    </button>
    {props.error?<div className="model-selector__feedback" role="alert">{props.error}<button type="button" disabled={props.saving} onClick={props.onReload}>{t('chat.modelMenu.reload')}</button></div>:props.status?<p className="model-selector__feedback" role="status">{props.status}</p>:null}
    {open?<ModelMenu {...props} anchor={trigger} onClose={close}/>:null}
  </div>;
}

function ModelMenu({anchor,onClose,...props}:SelectModelProps&{anchor:React.RefObject<HTMLButtonElement|null>;onClose:()=>void}){
  const {t}=useTranslation(),[query,setQuery]=useState(''),[active,setActive]=useState(0),id=useId(),search=useRef<HTMLInputElement>(null);
  const groups=useMemo(()=>modelMenuGroups(props.models,query),[props.models,query]);
  const eligible=groups.flatMap(group=>group.models).filter(model=>model.callable);
  const choose=(model:GatewayModel)=>{if(!model.callable||props.disabled||props.loading||props.saving||props.error)return;props.onSelect(model.modelAlias);onClose();};
  useEffect(()=>{document.getElementById(`${id}-${eligible[active]?.modelAlias}`)?.scrollIntoView({block:'nearest'});},[active,id,query]);
  // Upstream renderModelItem retains unique model identity, current check and unavailable-item disabling.
  function renderModelItem(model:GatewayModel){
    const index=eligible.findIndex(item=>item.modelAlias===model.modelAlias),selected=props.currentModel===model.modelAlias;
    return <button key={model.modelAlias} id={`${id}-${model.modelAlias}`} type="button" role="option" aria-selected={selected} disabled={!model.callable||props.disabled||props.loading||props.saving||!!props.error} data-active={index>=0&&active===index} data-testid={`model-option-${model.modelAlias}`} tabIndex={-1} onMouseDown={event=>event.preventDefault()} onMouseEnter={()=>{if(index>=0)setActive(index);}} onClick={()=>choose(model)}>
      <span className="model-selector__check">{selected?<IconCheck aria-hidden="true"/>:null}</span>
      <span className="model-selector__identity"><strong>{model.displayName}</strong><small>{model.modelAlias}</small>{!model.callable?<small>{model.upgradeHint||t('chat.modelMenu.unavailable')}</small>:null}</span>
      {props.defaultAlias===model.modelAlias?<small className="model-selector__default">{t('chat.modelMenu.recommended')}</small>:null}
    </button>;
  }
  // Upstream CommandInput -> CommandGroup -> CommandItem, with IM's existing protocol metadata.
  const modelCommand=<>
    <header><strong>{t('chat.modelMenu.title')}</strong><button type="button" onClick={onClose} aria-label={t('chat.modelMenu.close')}><IconX aria-hidden="true"/></button></header>
    <div className="model-selector__search"><input ref={search} autoFocus type="search" role="combobox" aria-label={t('chat.modelMenu.search')} placeholder={t('chat.modelMenu.search')} aria-expanded="true" aria-controls={id} aria-activedescendant={eligible[active]?`${id}-${eligible[active].modelAlias}`:undefined} value={query} onChange={event=>{setQuery(event.target.value);setActive(0);}} onKeyDown={event=>{if(event.key==='ArrowDown'){event.preventDefault();setActive(index=>Math.min(index+1,eligible.length-1));}else if(event.key==='ArrowUp'){event.preventDefault();setActive(index=>Math.max(index-1,0));}else if(event.key==='Enter'&&eligible[active]){event.preventDefault();choose(eligible[active]);}}}/></div>
    <div id={id} role="listbox" aria-label={t('chat.modelMenu.title')} className="model-selector__list">
      {props.loading?<p role="status">{t('chat.modelMenu.loading')}</p>:null}
      {props.error?<div role="alert"><p>{props.error}</p><button type="button" onClick={props.onReload} disabled={props.saving}>{t('chat.modelMenu.reload')}</button></div>:null}
      {!props.loading&&!props.error&&props.currentModel&&!props.models.some(model=>model.modelAlias===props.currentModel)?<p role="status">{t('chat.modelMenu.savedUnavailable',{model:props.currentModel})}</p>:null}
      {groups.map(group=><div role="group" aria-label={t(`chat.modelMenu.protocols.${group.provider}`)} key={group.provider}><h4>{t(`chat.modelMenu.protocols.${group.provider}`)}</h4>{group.models.map(renderModelItem)}</div>)}
      {!props.loading&&!props.error&&groups.length===0?<p>{t('chat.modelMenu.empty')}</p>:null}
    </div>
  </>;
  return <ComposerPopover anchor={anchor} align="end" initialFocus={search} onClose={onClose} title={t('chat.modelMenu.title')} className="model-selector__panel">{modelCommand}</ComposerPopover>;
}
