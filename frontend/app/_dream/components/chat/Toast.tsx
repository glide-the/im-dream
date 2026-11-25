// [Input] Feedback text, its optional trigger button, announcement urgency and dismissal callback.
// [Output] Timed feedback attached to the trigger, or at the top of the page for unanchored actions.
// [Pos] Shared feedback for actions inside the current dialog or page.
import { useEffect, useLayoutEffect, useRef, useState } from 'react';

interface ToastProps {
  message: string;
  onClose?: () => void;
  role?: 'status' | 'alert';
  hidden?: boolean;
  anchor?: HTMLButtonElement;
  id?: string;
}

export default function Toast({ message, onClose, role = 'status', hidden, anchor, id }: ToastProps) {
  const tipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{left: number; top: number; arrow: number; above: boolean}>();
  const [anchorVisible, setAnchorVisible] = useState(true);
  useLayoutEffect(() => {
    const tip = tipRef.current;
    if (!anchor || !tip || hidden) return;
    const place = () => {
      const button = anchor.getBoundingClientRect();
      const {width, height} = tip.getBoundingClientRect();
      const gap = parseFloat(getComputedStyle(document.documentElement).fontSize) / 2;
      const center = button.left + button.width / 2;
      const left = Math.max(gap, Math.min(center - width / 2, window.innerWidth - width - gap));
      const above = button.top >= height + gap * 2;
      setPosition({left, top: above ? button.top - height - gap : button.bottom + gap, arrow: center - left, above});
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
  }, [anchor, hidden, message]);
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
      role={role}
      aria-atomic="true"
      style={{
        position: 'fixed',
        top: anchor ? position?.top : 'calc(env(safe-area-inset-top, 0px) + 1rem)',
        left: anchor ? position?.left : '50%',
        transform: anchor ? undefined : 'translateX(-50%)',
        visibility: anchor && (!anchorVisible || !position) ? 'hidden' : undefined,
        zIndex: 60,
        boxSizing: 'border-box',
        width: 'max-content',
        maxWidth: 'calc(100% - 2rem)',
        padding: '0.625rem 1rem',
        borderRadius: '999px',
        background: 'var(--color-text-primary)',
        color: 'var(--color-bg-paper)',
        pointerEvents: 'none',
        textAlign: 'center',
        fontSize: '0.875rem',
        fontWeight: 600,
        boxShadow: '0 10px 24px var(--color-shadow-medium)',
      }}
    >
      {message}
      {anchor && position && <span aria-hidden="true" style={{
        position: 'absolute', left: position.arrow, [position.above ? 'bottom' : 'top']: 0,
        width: '0.5rem', height: '0.5rem', background: 'inherit',
        transform: `translate(-50%, ${position.above ? '50%' : '-50%'}) rotate(45deg)`,
      }}/>}
    </div>
  );
}
