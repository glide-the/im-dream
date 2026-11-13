// [Sync] 2026-11-13: align original UI icons and preserve the Chinese Agent list scroll boundary.
// [Sync] 2026-11-13: desktop Agent cascade and read-only MCP catalog with Thread-only tool switches.
// SPDX-License-Identifier: MIT
// Copyright (c) 2025 better-chatbot. Adapted from tool-select/index.tsx and agent-selector.tsx; full notice: frontend/third-party/better-chatbot/LICENSE.
// [Sync] 2026-11-13: one current-Agent trigger opens the migrated Agent/tools menu; IM data owners remain.
// [Input] Original composer tool mode, read-only MCP catalog and Thread selection and optional management navigation.
// [Output] Accessible, viewport-bounded tool panel with search, Thread-scoped switches and retained-scene dismissal.
// [Pos] Chat presentation; original hooks own configuration and the Runner owns tool loading.
// [Sync] 2026-11-13: implement the standalone Chat tools interaction without changing send DTOs.
import {useCallback,useEffect,useLayoutEffect,useRef,useState,type CSSProperties} from 'react';
import {useTranslation} from 'react-i18next';
import type {ComposerToolsMenuProps} from './ComposerToolsMenu.types';
import useChatMcpCatalog from '../../hooks/useChatMcpCatalog';
import {toggleChatMcp} from '../../hooks/useChatToolSelection';
import {serverStatusLabel} from '../claude-mcp/mcpResourcePresentation';
import {buildToolChoiceOptions} from './useComposerDraft';
import './ComposerToolsMenu.css';
import ComposerPopover from './ComposerPopover';
import ComposerAgentSelector from './ComposerAgentSelector';
import {selectedComposerAgent} from './composerAgentSelection';
import {agentLabel} from '../deck/deckAgentSelection';
import {iconMap} from '../deckVisuals';
import {IconChevronDown,IconChevronRight,IconX} from './Icons';
const AGENT_MENU_WIDTH=320;

export default function ComposerToolsMenu(props:ComposerToolsMenuProps) {
  const {t,i18n}=useTranslation(),trigger=useRef<HTMLButtonElement>(null);
  const agent=selectedComposerAgent(props.agentSelection),Icon=iconMap[agent?.icon as keyof typeof iconMap]||iconMap.brain;
  const label=props.agentSelection?.loading?t('chat.deck.loadingAgents'):agent?agentLabel(agent,(i18n.language||'en').split('-')[0]):props.agentSelection?.selectedAgentId?t('chat.agentTools.unavailable'):props.agentSelection?.noneLabel??t('chat.deck.noneAgent');
  const [open,setOpen]=useState(false);
  useEffect(()=>{if(props.active===false)setOpen(false);},[props.active]);
  const close=useCallback(()=>{setOpen(false);trigger.current?.focus();},[]);
  return <>
    <button ref={trigger} type="button" className="composer-tools-trigger" disabled={props.disabled} aria-label={t('chat.agentTools.trigger',{name:label})} title={t(props.fullAccessEnabled?'chat.inputDock.fullAccess':props.toolChoice==='manual'?'chat.inputDock.toolChoiceManual':'chat.inputDock.toolChoiceAuto')} aria-haspopup="dialog" aria-expanded={open}
      onClick={()=>setOpen(value=>!value)}><Icon aria-hidden="true" size={14}/><span className="composer-agent-trigger__name">{label}</span><IconChevronDown aria-hidden="true"/></button>
    {open?<ToolsPanel {...props} trigger={trigger} onClose={close}/>:null}
  </>;
}

function ToolsPanel({toolChoice,onToolChoice,fullAccessEnabled,disabled,loading,onManageTools,agentSelection,tools=[],onToolsChange,trigger,onClose}:ComposerToolsMenuProps&{trigger:React.RefObject<HTMLButtonElement|null>;onClose:()=>void}) {
  const {t}=useTranslation(),state=useChatMcpCatalog(),search=useRef<HTMLInputElement>(null),agentRow=useRef<HTMLButtonElement>(null);
  const [narrow,setNarrow]=useState(()=>matchMedia('(max-width:767px)').matches);
  useEffect(()=>{const media=matchMedia('(max-width:767px)'),change=()=>setNarrow(media.matches);media.addEventListener('change',change);return()=>media.removeEventListener('change',change);},[]);
  const [query,setQuery]=useState(''),[choosingAgent,setChoosingAgent]=useState(false),hoverSuppressed=useRef(false);
  const closeAgent=()=>{hoverSuppressed.current=true;setChoosingAgent(false);agentRow.current?.focus();};
  const visible=state.servers.filter(server=>(server.display_name+' '+server.name).toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  return <ComposerPopover anchor={trigger} initialFocus={agentRow} onClose={onClose} title={t('chat.agentTools.title')} sidePanelWidth={choosingAgent&&!narrow?AGENT_MENU_WIDTH:undefined} className="composer-tools-panel">
    <header><strong>{t('chat.agentTools.title')}</strong><button type="button" aria-label={t('chat.toolsMenu.close')} onClick={onClose}><IconX aria-hidden="true"/></button></header>
    <div className={'composer-tools-panel__body'+(choosingAgent&&narrow?' composer-tools-panel__body--agents':'')}>
      {choosingAgent&&narrow&&agentSelection?<ComposerAgentSelector selection={agentSelection} onBack={()=>setChoosingAgent(false)} onSelected={onClose}/>:<>
      <button ref={agentRow} className="composer-agent-selector__entry" aria-haspopup="listbox" aria-expanded={choosingAgent} onMouseEnter={()=>{if(!hoverSuppressed.current&&!narrow&&agentSelection?.onChange&&!agentSelection.loading&&!disabled)setChoosingAgent(true);}} type="button" disabled={!agentSelection?.onChange||agentSelection.loading||disabled} onMouseLeave={()=>{hoverSuppressed.current=false;}} onClick={()=>{hoverSuppressed.current=false;setChoosingAgent(true);}} onKeyDown={event=>{if(event.key==='ArrowRight'){event.preventDefault();hoverSuppressed.current=false;setChoosingAgent(true);}else if(event.key==='ArrowLeft'&&choosingAgent){event.preventDefault();closeAgent();}}}>{t('chat.agentTools.select')} <IconChevronRight aria-hidden="true"/></button>
      <fieldset onMouseEnter={()=>{if(!narrow)setChoosingAgent(false);}} disabled={disabled||loading}><legend>{t('chat.inputDock.toolModeAria')}</legend>
        {fullAccessEnabled?<span>{t('chat.inputDock.fullAccess')}</span>:buildToolChoiceOptions(t).map(option=><label key={option.value}><input type="radio" name="composer-tool-mode" value={option.value} checked={toolChoice===option.value} onChange={()=>onToolChoice(option.value)}/><span>{option.label}</span></label>)}
      </fieldset>
      <label className="composer-tools-panel__search">{t('chat.toolsMenu.services')}{state.capability?.enabled&&!state.loading?` · ${tools.filter(tool=>tool.type==='mcp').length}`:''}
        <input ref={search} autoFocus type="search" aria-label={t('chat.toolsMenu.search')} placeholder={t('chat.toolsMenu.search')} value={query} onChange={event=>setQuery(event.target.value)}/>
      </label>
      <p>{t('chat.toolsMenu.scope')}</p>
      {state.loading?<p role="status">{t('chat.toolsMenu.loading')}</p>:null}
      {state.capability&&!state.capability.enabled?<p role="status">{t('chat.toolsMenu.unavailable')}</p>:null}
      {state.capability?.enabled?visible.map(server=>{
        const checked=tools.some(tool=>tool.type==='mcp'&&tool.server_name===server.name);
        const available=server.enabled&&(server.auth_state==='anonymous'||server.auth_state==='authenticated');
        return <div className="composer-tools-panel__service" key={server.name} onMouseEnter={()=>{if(!narrow)setChoosingAgent(false);}}>
          <div><strong>{server.display_name||server.name}</strong>{!available?<small>{serverStatusLabel(server,server.state)}</small>:null}</div>
          <button type="button" role="switch" aria-checked={checked} aria-label={server.display_name||server.name}
            disabled={disabled||state.loading||!onToolsChange||(!available&&!checked)} onClick={()=>onToolsChange?.(toggleChatMcp(tools,server.name))}><span className="composer-tools-switch" aria-hidden="true"/></button>
        </div>;
      }):null}
      {!state.loading&&!state.error&&state.capability?.enabled&&visible.length===0?<p role="status">{t(query?'chat.toolsMenu.noMatch':'chat.toolsMenu.empty')}</p>:null}
      {state.error?<div role="alert"><p>{state.error}</p><button type="button" disabled={state.loading} onClick={()=>void state.load()}>{t('chat.toolsMenu.retry')}</button></div>:null}
      <div className="composer-tools-panel__device"><strong>{t('chat.toolsMenu.audio')}</strong><small>{t('chat.toolsMenu.appOnly')}</small></div>
      </>}
    </div>
    {onManageTools?<footer><button type="button" onClick={()=>{onClose();onManageTools();}}>{t('chat.toolsMenu.manage')}</button></footer>:null}
    {choosingAgent&&!narrow&&agentSelection?<AgentSubmenu anchor={agentRow} onBack={closeAgent}><ComposerAgentSelector selection={agentSelection} onBack={closeAgent} onSelected={onClose}/></AgentSubmenu>:null}
  </ComposerPopover>;
}

function AgentSubmenu({anchor,onBack,children}:{anchor:React.RefObject<HTMLButtonElement|null>;onBack:()=>void;children:React.ReactNode}){
  const root=useRef<HTMLDivElement>(null),[position,setPosition]=useState<CSSProperties>({visibility:'hidden'});
  useLayoutEffect(()=>{
    const layout=()=>{const rect=anchor.current?.getBoundingClientRect();if(!rect)return;const width=Math.min(AGENT_MENU_WIDTH,innerWidth-16);const panel=anchor.current?.closest('.composer-tools-panel')?.getBoundingClientRect()??rect;const right=panel.right+8;const left=right+width<=innerWidth-8?right:Math.max(8,panel.left-width-8);const height=Math.min(root.current?.getBoundingClientRect().height??480,480,innerHeight-24);setPosition({left,top:Math.max(8,Math.min(rect.top,innerHeight-height-8)),width,maxHeight:Math.min(480,innerHeight-24)});};
    layout();const frame=requestAnimationFrame(layout),panel=anchor.current?.closest('.composer-tools-panel'),observer=new MutationObserver(layout);if(panel)observer.observe(panel,{attributes:true,attributeFilter:['style']});window.addEventListener('resize',layout);return()=>{cancelAnimationFrame(frame);observer.disconnect();window.removeEventListener('resize',layout);};
  },[anchor]);
  useLayoutEffect(()=>{if(position.visibility!=='hidden')root.current?.querySelector('input')?.focus();},[position.visibility]);
  return <div ref={root} className="composer-agent-flyout" style={position} onKeyDown={event=>{if(event.key==='ArrowLeft'){event.preventDefault();event.stopPropagation();onBack();}}}>{children}</div>;
}
