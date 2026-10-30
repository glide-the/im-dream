// [Input] Original draft/focus, workspace capability and Deck/Thread Skill context.
// [Output] Existing catalog discovery, builtin compact, filtering, dismissal and keyboard selection state.
// [Pos] Shared headless composer interaction; no command execution, submission or permission changes.
import {useCallback,useEffect,useMemo,useState,type Dispatch,type SetStateAction} from 'react';
import {filterInstalledSkillCommands,loadAvailableSkillCommands,withBuiltinCompact,type AvailableSkillCommand} from './slashSkillCommands';
export type ComposerSkillKey='ArrowDown'|'ArrowUp'|'Enter'|'Tab'|'Escape';
export default function useComposerSkills({query,setQuery,focused,workspaceEnabled,deckId,threadId,transport=fetch}:{query:string;setQuery:Dispatch<SetStateAction<string>>;focused:boolean;workspaceEnabled?:boolean;deckId?:string;threadId?:string;transport?:typeof fetch}) {
  const [commands,setCommands]=useState<readonly AvailableSkillCommand[]>([]);
  const [activeIndex,setActiveIndex]=useState(0),[dismissed,setDismissed]=useState<string|null>(null);
  useEffect(()=>{
    let active=true;setCommands([]);if(!workspaceEnabled)return()=>{active=false;};
    void loadAvailableSkillCommands({deckId,threadId},transport).then(value=>{if(active)setCommands(value);}).catch(()=>{if(active)setCommands([]);});
    return()=>{active=false;};
  },[deckId,threadId,workspaceEnabled,transport]);
  const matches=useMemo(()=>!focused || dismissed===query?[]:filterInstalledSkillCommands(query,withBuiltinCompact(commands)),[dismissed,commands,focused,query]);
  useEffect(()=>{setActiveIndex(0);if(dismissed!==null && dismissed!==query)setDismissed(null);},[dismissed,query]);
  const resetDismissal=useCallback(()=>setDismissed(null),[]);
  const select=useCallback((command:AvailableSkillCommand)=>{setQuery(`${command.command} `);setDismissed(null);},[setQuery]);
  function keyDown(key:string):boolean {
    if(!matches.length)return false;
    if(key==='ArrowDown'){setActiveIndex(current=>(current+1)%matches.length);return true;}
    if(key==='ArrowUp'){setActiveIndex(current=>(current-1+matches.length)%matches.length);return true;}
    if(key==='Enter' || key==='Tab'){select(matches[activeIndex] ?? matches[0]);return true;}
    if(key==='Escape'){setDismissed(query);return true;}
    return false;
  }
  return {matches,activeIndex,select,keyDown,resetDismissal};
}
