// [Sync] 2026-11-13: keep Chinese labels and check/back icons in fixed alignment columns.
// SPDX-License-Identifier: MIT
// Copyright (c) 2025 better-chatbot. Adapted from tool-select/agent-selector.tsx; full notice: frontend/third-party/better-chatbot/LICENSE.
// [Input] Original IM Deck/Agent catalog, selected ID and onChange callback.
// [Output] Migrated Agent menu group, search, selected feedback and choice/close behavior.
// [Pos] Chat presentation adapter; directory loading, Thread and Agent identity stay with IM callers.
import {useId,useMemo,useState} from 'react';
import {useTranslation} from 'react-i18next';
import {agentLabel,deckLabel,groupDeckAgents,type DeckChatSelectorProps,type DeckAgentSelection} from '../deck/deckAgentSelection';
import {iconMap} from '../deckVisuals';
import {IconCheck,IconChevronLeft} from './Icons';
export default function ComposerAgentSelector({selection,onBack,onSelected}:{selection:DeckChatSelectorProps;onBack:()=>void;onSelected:()=>void}){
  const {t,i18n}=useTranslation(),language=(i18n.language||'en').split('-')[0],id=useId();
  const [query,setQuery]=useState(''),[active,setActive]=useState(0);
  const groups=useMemo(()=>groupDeckAgents(selection.decks,query,language),[selection.decks,query,language]);
  const options:(DeckAgentSelection|undefined)[]=[...(selection.allowNone===false?[]:[undefined]),...groups.flatMap(({deck,agents})=>agents.map(agent=>({deckId:deck.id,agentId:agent.id})))];
  const choose=(value:DeckAgentSelection|undefined)=>{if(!selection.onChange)return;selection.onChange(value);onSelected();};
  return <section className="composer-agent-selector">
    <button type="button" onClick={onBack}><IconChevronLeft aria-hidden="true"/><span>{t('chat.agentTools.back')}</span></button>
    <input autoFocus type="search" role="combobox" aria-expanded="true" aria-controls={id} aria-activedescendant={options.length?`${id}-${active}`:undefined} aria-label={t('chat.deck.searchAgentPlaceholder')} placeholder={t('chat.deck.searchAgentPlaceholder')} value={query} onChange={event=>{setQuery(event.target.value);setActive(0);}}
      onKeyDown={event=>{if(event.key==='ArrowDown'){event.preventDefault();setActive(value=>Math.min(value+1,options.length-1));}else if(event.key==='ArrowUp'){event.preventDefault();setActive(value=>Math.max(0,value-1));}else if(event.key==='Enter'&&options.length){event.preventDefault();choose(options[active]);}else if(event.key==='ArrowLeft'){event.preventDefault();onBack();}}}/>
    {selection.error?<p role="alert">{selection.error}</p>:null}
    <div id={id} role="listbox" aria-label={t('chat.deck.agentListAria')}>
      {selection.allowNone!==false?<button id={`${id}-0`} type="button" role="option" aria-selected={!selection.selectedAgentId} onClick={()=>choose(undefined)}><span aria-hidden="true" className="composer-agent-selector__check">{!selection.selectedAgentId?<IconCheck/>:null}</span><span>{selection.noneLabel??t('chat.deck.noneAgent')}</span></button>:null}
      {groups.map(({deck,agents})=><div role="group" aria-label={deckLabel(deck,language)} key={deck.id}>
        <h4>{deckLabel(deck,language)}</h4>
        {agents.map(agent=>{const index=options.findIndex(option=>option?.agentId===agent.id),Icon=iconMap[agent.icon as keyof typeof iconMap]||iconMap.brain;return <button id={`${id}-${index}`} type="button" role="option" aria-selected={selection.selectedAgentId===agent.id} data-active={active===index} key={agent.id} onMouseDown={event=>event.preventDefault()} onMouseEnter={()=>setActive(index)} onClick={()=>choose({deckId:deck.id,agentId:agent.id})}>
          <span aria-hidden="true" className="composer-agent-selector__check">{selection.selectedAgentId===agent.id?<IconCheck/>:null}</span><Icon aria-hidden="true" size={15}/><span>{agentLabel(agent,language)}</span>
        </button>;})}
      </div>)}
      {groups.length===0?<p>{t('chat.deck.noAgentMatch')}</p>:null}
    </div>
  </section>;
}
