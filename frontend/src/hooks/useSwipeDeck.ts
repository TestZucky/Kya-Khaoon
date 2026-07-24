import { useCallback, useRef, useState, type PointerEvent } from "react";

export type SwipeHandlers = {
  onLike: () => void;
  onSkip: () => void;
};

/** Distance in px a card must travel before the gesture commits. */
const THRESHOLD = 90;

/**
 * Pointer-driven Tinder deck. Right = order, left = skip. Nothing else.
 * Returns the live drag offset so the card can rotate and the ORDER / SKIP
 * stamps can fade in proportionally.
 */
export function useSwipeDeck({ onLike, onSkip }: SwipeHandlers) {
  const [delta, setDelta] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const origin = useRef({ x: 0, y: 0 });
  const latest = useRef({ x: 0, y: 0 });

  const reset = useCallback(() => {
    latest.current = { x: 0, y: 0 };
    setDelta({ x: 0, y: 0 });
    setDragging(false);
  }, []);

  const onPointerDown = useCallback((e: PointerEvent<HTMLElement>) => {
    if (!e.isPrimary) return;
    origin.current = { x: e.clientX, y: e.clientY };
    latest.current = { x: 0, y: 0 };
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  }, []);

  const onPointerMove = useCallback(
    (e: PointerEvent<HTMLElement>) => {
      if (!dragging) return;
      const next = {
        x: e.clientX - origin.current.x,
        y: e.clientY - origin.current.y,
      };
      latest.current = next;
      setDelta(next);
    },
    [dragging],
  );

  const onPointerUp = useCallback(
    (e: PointerEvent<HTMLElement>) => {
      if (!dragging) return;
      if (e.currentTarget.hasPointerCapture(e.pointerId)) {
        e.currentTarget.releasePointerCapture(e.pointerId);
      }
      const { x } = latest.current;
      reset();
      if (Math.abs(x) > THRESHOLD) {
        if (x > 0) onLike();
        else onSkip();
      }
    },
    [dragging, onLike, onSkip, reset],
  );

  return {
    delta,
    dragging,
    /** 0 → 1 opacity for each swipe-direction stamp. */
    stamps: {
      like: clamp(delta.x / 80),
      skip: clamp(-delta.x / 80),
    },
    rotation: delta.x * 0.07,
    handlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onPointerCancel: onPointerUp,
    },
  };
}

const clamp = (v: number) => Math.max(0, Math.min(v, 1));
