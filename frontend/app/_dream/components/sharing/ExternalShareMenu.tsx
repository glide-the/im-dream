// [Input] A record action trigger, current share status and caller-owned operations.
// [Output] Viewport-contained copy/view/settings popup with keyboard and outside dismissal.
// [Pos] External-links action presenter; public state checks remain in useExternalLinks.
import {useLayoutEffect, useRef, useState, type CSSProperties} from 'react';
import {createPortal} from 'react-dom';
import {useTranslation} from 'react-i18next';
import {FiGlobe} from 'react-icons/fi';
import {IconCopy, IconSettings} from '../chat/Icons';

interface Props {
  triggerId: string;
  active: boolean;
  onCopy: () => void;
  onView: () => void;
  onSettings: () => void;
  onClose: () => void;
}

export default function ExternalShareMenu({triggerId, active, onCopy, onView, onSettings, onClose}: Props) {
  const {t} = useTranslation();
  const ref = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose); closeRef.current = onClose;
  const [position, setPosition] = useState<CSSProperties>({visibility: 'hidden'});

  useLayoutEffect(() => {
    const trigger = document.getElementById(triggerId), menu = ref.current;
    if (!trigger || !menu) return;
    const anchor = trigger.getBoundingClientRect(), popup = menu.getBoundingClientRect();
    const edge = 12, gap = 6;
    setPosition({
      left: Math.max(edge, Math.min(anchor.right - popup.width, window.innerWidth - popup.width - edge)),
      top: anchor.bottom + gap + popup.height <= window.innerHeight - edge
        ? anchor.bottom + gap : Math.max(edge, anchor.top - popup.height - gap),
    });
    const focusFrame = requestAnimationFrame(() => menu.querySelector<HTMLButtonElement>('button')?.focus());
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !menu.contains(event.target) && !trigger.contains(event.target)) closeRef.current();
    };
    const dismiss = () => closeRef.current();
    const scroll = (event: Event) => {if (!(event.target instanceof Node) || !menu.contains(event.target)) dismiss();};
    document.addEventListener('pointerdown', outside);
    window.addEventListener('resize', dismiss);
    window.addEventListener('scroll', scroll, true);
    return () => {
      cancelAnimationFrame(focusFrame);
      document.removeEventListener('pointerdown', outside);
      window.removeEventListener('resize', dismiss);
      window.removeEventListener('scroll', scroll, true);
    };
  }, [triggerId]);

  function restoreTrigger() {document.getElementById(triggerId)?.focus();}
  return createPortal(
    <div ref={ref} id={triggerId + '-menu'} role="menu" aria-labelledby={triggerId} className="external-links__menu" style={position} onKeyDown={event => {
      if (event.key === 'Escape' || event.key === 'Tab') {
        if (event.key === 'Escape') {event.preventDefault(); event.stopPropagation();}
        restoreTrigger(); onClose(); return;
      }
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const items = Array.from(ref.current?.querySelectorAll<HTMLButtonElement>('button') ?? []);
      const index = items.indexOf(document.activeElement as HTMLButtonElement);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
        : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items[next]?.focus();
    }}>
      {active ? <>
        <button type="button" role="menuitem" tabIndex={-1} onClick={() => {restoreTrigger(); onCopy();}}><IconCopy aria-hidden="true"/>{t('externalShare.copy')}</button>
        <button type="button" role="menuitem" tabIndex={-1} onClick={() => {restoreTrigger(); onView();}}><FiGlobe aria-hidden="true"/>{t('externalShare.view')}</button>
        <div role="separator"/>
      </> : null}
      <button type="button" role="menuitem" tabIndex={-1} onClick={() => {restoreTrigger(); onSettings();}}><IconSettings aria-hidden="true"/>{t('externalShare.settings')}</button>
    </div>, document.body,
  );
}
