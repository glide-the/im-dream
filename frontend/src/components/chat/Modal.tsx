// [Input] Open state, title/content, close callback, optional presentation variant, media toolbar actions, and controlled zoom state.
// [Output] Portal-backed accessible modal with backdrop/Escape close, focus containment/restoration, and one shared media-preview skeleton whose controls resize only marked media content.
// [Pos] shared modal component node in frontend/src/components/chat
// [Sync] 2026-08-22: add dialog semantics, keyboard/focus lifecycle, and an image-preview size while preserving the default connector modal.
// [Sync] 2026-08-23: replace the image-only surface with the shared Mermaid/Workspace immersive viewer: top-right actions and bottom zoom controls.
// [Sync] 2026-08-23: add non-passive wheel zoom over the media stage, sharing the existing 50%–200% controlled state and blocking background scroll.
// [Sync] 2026-08-23: keep the preview sheet at its fitted geometry while exposing zoom through a CSS variable for explicit image/diagram targets only.

import { useEffect, useId, useRef, type CSSProperties, type Dispatch, type ReactNode, type SetStateAction } from 'react';
import { createPortal } from 'react-dom';
import { IconMinus, IconPlus, IconX } from './Icons';
import './Modal.css';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');
const MEDIA_ZOOM_MIN = 50;
const MEDIA_ZOOM_MAX = 200;
const MEDIA_ZOOM_STEP = 10;
const MEDIA_WHEEL_ZOOM_THRESHOLD_PX = 40;
const MEDIA_WHEEL_LINE_HEIGHT_PX = 16;

interface ModalProps {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  closeLabel?: string;
  variant?: 'default' | 'media-preview';
  toolbarActions?: ReactNode;
  zoom?: {
    value: number;
    onChange: Dispatch<SetStateAction<number>>;
    zoomOutLabel: string;
    zoomInLabel: string;
  };
}

export default function Modal({
  open,
  title,
  children,
  onClose,
  closeLabel = 'Close',
  variant = 'default',
  toolbarActions,
  zoom,
}: ModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const mediaStageRef = useRef<HTMLDivElement>(null);
  const wheelDeltaRef = useRef(0);
  const onCloseRef = useRef(onClose);
  const zoomOnChange = zoom?.onChange;

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return undefined;

    const previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const previousBodyOverflow = document.body.style.overflow;
    const focusFrame = window.requestAnimationFrame(() => {
      const autofocusTarget = dialogRef.current?.querySelector<HTMLElement>('[autofocus]');
      (autofocusTarget ?? closeButtonRef.current)?.focus();
    });

    document.body.style.overflow = 'hidden';
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;

      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
      if (focusable.length === 0) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.cancelAnimationFrame(focusFrame);
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousBodyOverflow;
      previouslyFocused?.focus();
    };
  }, [open]);

  useEffect(() => {
    if (!open || variant !== 'media-preview' || !zoomOnChange) return undefined;
    const stage = mediaStageRef.current;
    if (!stage) return undefined;
    wheelDeltaRef.current = 0;

    const handleWheel = (event: WheelEvent) => {
      if (event.deltaY === 0) return;
      event.preventDefault();
      const deltaScale = event.deltaMode === WheelEvent.DOM_DELTA_LINE
        ? MEDIA_WHEEL_LINE_HEIGHT_PX
        : event.deltaMode === WheelEvent.DOM_DELTA_PAGE
          ? window.innerHeight
          : 1;
      const normalizedDelta = event.deltaY * deltaScale;
      if (
        wheelDeltaRef.current !== 0
        && Math.sign(wheelDeltaRef.current) !== Math.sign(normalizedDelta)
      ) {
        wheelDeltaRef.current = 0;
      }
      wheelDeltaRef.current += normalizedDelta;
      if (Math.abs(wheelDeltaRef.current) < MEDIA_WHEEL_ZOOM_THRESHOLD_PX) return;
      const direction = wheelDeltaRef.current < 0 ? 1 : -1;
      wheelDeltaRef.current = 0;
      zoomOnChange((current) => Math.min(
        MEDIA_ZOOM_MAX,
        Math.max(MEDIA_ZOOM_MIN, current + direction * MEDIA_ZOOM_STEP),
      ));
    };

    stage.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      stage.removeEventListener('wheel', handleWheel);
      wheelDeltaRef.current = 0;
    };
  }, [open, variant, zoomOnChange]);

  if (!open) return null;

  const mediaZoomStyle = zoom ? {
    '--media-preview-scale': zoom.value / 100,
    width: `${zoom.value}%`,
    minHeight: `${zoom.value}%`,
  } as CSSProperties : undefined;

  return createPortal(
    <div
      className={`modal-backdrop modal-backdrop--${variant}`}
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className={`modal-surface modal-surface--${variant}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <div className={`modal-header modal-header--${variant}`}>
          <h2 id={titleId} className={`modal-title modal-title--${variant}`}>{title}</h2>
          <div className={`modal-toolbar modal-toolbar--${variant}`}>
            {toolbarActions}
            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              className={`modal-close modal-close--${variant}`}
              aria-label={closeLabel}
              title={closeLabel}
            >
              <IconX aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className={`modal-content modal-content--${variant}`}>
          {variant === 'media-preview' && zoom ? (
            <div
              ref={mediaStageRef}
              className="modal-media-stage"
              onClick={(event) => {
                if (event.target === event.currentTarget) onClose();
              }}
            >
              <div
                className="modal-media-sizer"
                style={mediaZoomStyle}
                onClick={(event) => {
                  if (event.target === event.currentTarget) onClose();
                }}
              >
                <div className="modal-media-transform">{children}</div>
              </div>
            </div>
          ) : children}
        </div>
        {variant === 'media-preview' && zoom ? (
          <div className="modal-zoom-controls" role="group" aria-label={`${title} zoom`}>
            <button
              type="button"
              className="modal-zoom-button"
              aria-label={zoom.zoomOutLabel}
              title={zoom.zoomOutLabel}
              disabled={zoom.value <= MEDIA_ZOOM_MIN}
              onClick={() => zoom.onChange(Math.max(MEDIA_ZOOM_MIN, zoom.value - MEDIA_ZOOM_STEP))}
            >
              <IconMinus />
            </button>
            <output className="modal-zoom-value" aria-live="polite">{zoom.value}%</output>
            <button
              type="button"
              className="modal-zoom-button"
              aria-label={zoom.zoomInLabel}
              title={zoom.zoomInLabel}
              disabled={zoom.value >= MEDIA_ZOOM_MAX}
              onClick={() => zoom.onChange(Math.min(MEDIA_ZOOM_MAX, zoom.value + MEDIA_ZOOM_STEP))}
            >
              <IconPlus />
            </button>
          </div>
        ) : null}
      </div>
    </div>,
    document.body,
  );
}
