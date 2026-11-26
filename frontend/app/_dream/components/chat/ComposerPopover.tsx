// [Sync] 2026-11-13: keep an open desktop Agent cascade beside its parent within the available viewport.
// [Sync] 2026-11-13: accept a focusable initial element for the grouped Agent menu.
// [Input] Caller-owned trigger, close action, initial focus and menu content.
// [Output] Bounded desktop popover or narrow-screen sheet, preserving keyboard focus and viewport limits.
// [Pos] IM presentation adapter for migrated Better Chatbot Popover/Drawer callers.
// [Sync] 2026-11-13: reuse one viewport/focus boundary for Agent/tools and model selection.
import {useEffect,useLayoutEffect,useRef,useState,type CSSProperties,type ReactNode,type RefObject} from 'react';
import {createPortal} from 'react-dom';
import './ComposerPopover.css';
interface Props {anchor:RefObject<HTMLButtonElement|null>;initialFocus?:RefObject<HTMLElement|null>;onClose:()=>void;title:string;className:string;children:ReactNode;align?:'start'|'end';sidePanelWidth?:number;}
export default function ComposerPopover({anchor,initialFocus,onClose,title,className,children,align='start',sidePanelWidth=0}:Props){
  const root=useRef<HTMLDivElement>(null),[sheet,setSheet]=useState(false),[position,setPosition]=useState<CSSProperties>({visibility:'hidden'});
  useEffect(()=>{if(!sheet)return;const previous=document.body.style.overflow;document.body.style.overflow='hidden';return()=>{document.body.style.overflow=previous;};},[sheet]);
  useLayoutEffect(()=>{
    function layout(){
      const rect=anchor.current?.getBoundingClientRect();if(!rect)return;
      const viewport=window.visualViewport,top=viewport?.offsetTop??0,bottom=top+(viewport?.height??innerHeight),narrow=matchMedia('(max-width:767px)').matches;
      setSheet(narrow);
      if(narrow){setPosition({left:8,bottom:Math.max(8,innerHeight-bottom+8),width:innerWidth-16,maxHeight:Math.max(0,(bottom-top)*.7),zIndex:1150});return;}
      const above=Math.max(0,Math.min(rect.top,bottom)-top-16),below=Math.max(0,bottom-rect.bottom-16),up=above>=below,width=Math.min(336,innerWidth-16);
      let left=Math.max(8,Math.min(align==='end'?rect.right-width:rect.left,innerWidth-width-8));
      if(sidePanelWidth&&innerWidth>=width+sidePanelWidth+24&&left+width+sidePanelWidth+16>innerWidth&&left-sidePanelWidth-8<8)left=innerWidth-width-sidePanelWidth-16;
      setPosition({left,width,...(up?{bottom:innerHeight-Math.min(rect.top,bottom)+8}:{top:Math.max(top,rect.bottom)+8}),maxHeight:Math.min(520,up?above:below),zIndex:1150});
    }
    layout();
    const outside=(event:PointerEvent)=>{if(event.target instanceof Node&&!root.current?.contains(event.target)&&!anchor.current?.contains(event.target))onClose();};
    const keyboard=(event:KeyboardEvent)=>{
      if(event.key==='Escape'){event.preventDefault();event.stopPropagation();onClose();return;}
      if(event.key!=='Tab'||!matchMedia('(max-width:767px)').matches)return;
      const focusable=Array.from(root.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),a[href]')??[]).filter(node=>node.tabIndex>=0&&node.getClientRects().length>0);
      const first=focusable[0],last=focusable.at(-1);
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
    };
    document.addEventListener('pointerdown',outside);document.addEventListener('keydown',keyboard);
    window.addEventListener('resize',layout);window.visualViewport?.addEventListener('resize',layout);
    return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',keyboard);window.removeEventListener('resize',layout);window.visualViewport?.removeEventListener('resize',layout);};
  },[anchor,initialFocus,onClose,align,sidePanelWidth]);
  // Positioning first removes visibility:hidden; focus after that DOM commit.
  useLayoutEffect(()=>{if(position.visibility!=='hidden')initialFocus?.current?.focus();},[initialFocus,position.visibility]);
  return createPortal(<>{sheet?<div className="composer-popover-backdrop" aria-hidden="true"/>:null}<div ref={root} role="dialog" aria-modal={sheet||undefined} aria-label={title} className={`composer-popover ${className}${sheet?' composer-popover--sheet':''}`} style={position}>{children}</div></>,document.body);
}
