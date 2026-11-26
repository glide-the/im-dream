// [Input] Feedback text, trigger button and optional explicit confirmation controls.
// [Output] Anchored interactive confirmation or timed operation feedback.
// [Pos] Shared feedback for actions inside the current dialog or page.
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';

interface ToastProps {
  message: string;
  onClose?: () => void;
  role?: 'status' | 'alert';
  hidden?: boolean;
  anchor?: HTMLButtonElement;
  id?: string;
  actions?: ReactNode;
  onDismissRequest?: () => void;
}

export default function Toast({ message, onClose, role = 'status', hidden, anchor, id, actions, onDismissRequest }: ToastProps) {
  const tipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{left: number; top: number; arrow: number; edge: 'left' | 'right' | 'top' | 'bottom'}>();
  const [anchorVisible, setAnchorVisible] = useState(true);
  const interactive = Boolean(actions);
  useLayoutEffect(() => {
    const tip = tipRef.current;
    if (!anchor || !tip || hidden) return;
    const place = () => {
      const button = anchor.getBoundingClientRect();
      const gap = parseFloat(getComputedStyle(document.documentElement).fontSize) / 2;
      if (interactive) {
        // Keep the entire column of article buttons available for a second selection.
        const onLeft = button.left >= window.innerWidth - button.right;
        const room = onLeft ? button.left : window.innerWidth - button.right;
        tip.style.maxWidth = `min(23rem, ${Math.max(0, room - 2 * gap)}px)`;
        const {width, height} = tip.getBoundingClientRect();
        const middle = button.top + button.height / 2;
        const top = Math.max(gap, Math.min(middle - height / 2, window.innerHeight - height - gap));
        setPosition({left: onLeft ? button.left - gap - width : button.right + gap, top,
          arrow: middle - top, edge: onLeft ? 'right' : 'left'});
        return;
      }
      tip.style.maxWidth = 'calc(100% - 2rem)';
      const {width, height} = tip.getBoundingClientRect();
      const center = button.left + button.width / 2;
      const left = Math.max(gap, Math.min(center - width / 2, window.innerWidth - width - gap));
      const above = button.top >= height + gap * 2;
      setPosition({left, top: above ? button.top - height - gap : button.bottom + gap, arrow: center - left, edge: above ? 'bottom' : 'top'});
    };
    place();
    const observer = new IntersectionObserver(([entry]) => setAnchorVisible(entry.isIntersecting));
    observer.observe(anchor);
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [anchor, hidden, message, interactive]);
  const placed = Boolean(position);
  useLayoutEffect(() => {
    if (interactive && placed && !hidden) tipRef.current?.querySelector('button')?.focus({preventScroll: true});
  }, [interactive, placed, hidden, anchor]);
  useEffect(() => {
    if (!interactive || hidden || !onDismissRequest) return;
    const outside = (event: PointerEvent) => {
      if (event.target instanceof Node && !tipRef.current?.contains(event.target) && !anchor?.contains(event.target)) onDismissRequest();
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      event.stopPropagation();
      onDismissRequest();
      anchor?.focus({preventScroll: true});
    };
    document.addEventListener('pointerdown', outside, true);
    document.addEventListener('keydown', escape, true);
    return () => {
      document.removeEventListener('pointerdown', outside, true);
      document.removeEventListener('keydown', escape, true);
    };
  }, [interactive, hidden, anchor, onDismissRequest]);
  useEffect(() => {
    if (!onClose) return;
    const timer = window.setTimeout(onClose, 2800);
    return () => window.clearTimeout(timer);
  }, [onClose]);

  return (
    <div
      ref={tipRef}
      id={id}
      hidden={hidden}
      role={interactive ? 'dialog' : role}
      aria-label={interactive ? message : undefined}
      aria-atomic={interactive ? undefined : true}
      style={{
        position: 'fixed',
        top: anchor ? position?.top : 'calc(env(safe-area-inset-top, 0px) + 1rem)',
        left: anchor ? position?.left : '50%',
        transform: anchor ? undefined : 'translateX(-50%)',
        visibility: anchor && (!anchorVisible || !position) ? 'hidden' : undefined,
        zIndex: 60,
        boxSizing: 'border-box',
        width: 'max-content',
        maxWidth: interactive ? 'min(23rem, calc(100% - 2rem))' : 'calc(100% - 2rem)',
        overflowWrap: 'anywhere',
        padding: '0.625rem 1rem',
        borderRadius: interactive ? '0.75rem' : '999px',
        background: 'var(--color-text-primary)',
        color: 'var(--color-bg-paper)',
        pointerEvents: interactive ? 'auto' : 'none',
        textAlign: 'center',
        fontSize: '0.875rem',
        fontWeight: 600,
        boxShadow: '0 10px 24px var(--color-shadow-medium)',
      }}
    >
      {interactive ? <span style={{display: 'block', maxHeight: '35vh', overflowY: 'auto'}}>{message}</span> : message}
      {actions}
      {anchor && position && <span aria-hidden="true" style={{
        position: 'absolute', [position.edge]: 0, [interactive ? 'top' : 'left']: position.arrow,
        width: '0.5rem', height: '0.5rem', background: 'inherit',
        transform: `translate(${position.edge === 'right' ? '50%' : '-50%'}, ${position.edge === 'bottom' ? '50%' : '-50%'}) rotate(45deg)`,
      }}/>}
    </div>
  );
}
