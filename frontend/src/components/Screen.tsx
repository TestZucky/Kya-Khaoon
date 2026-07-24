import type { CSSProperties, ReactNode } from "react";
import { BG_DARK, COLORS, DISPLAY_FONT } from "@/lib/theme";

type ScreenProps = {
  children: ReactNode;
  /** Tab screens sit on flat bg; auth/onboarding screens get the gradient. */
  gradient?: boolean;
  /** Leaves room for the bottom nav pinned to the phone frame. */
  withNav?: boolean;
  className?: string;
  style?: CSSProperties;
};

/**
 * Fills the phone frame and scrolls internally, so the bottom nav can stay
 * pinned to the frame rather than to the browser window.
 */
export function Screen({
  children,
  gradient = false,
  withNav = false,
  className = "",
  style,
}: ScreenProps) {
  return (
    <div
      className={`h-full flex flex-col overflow-y-auto scrollbar-hide ${
        withNav ? "pb-24" : ""
      } ${className}`}
      style={{ background: gradient ? BG_DARK : COLORS.bg, ...style }}
    >
      {children}
    </div>
  );
}

/** The "eyebrow + big title" pairing used at the top of every tab screen. */
export function ScreenHeader({
  eyebrow,
  title,
  action,
}: {
  eyebrow: string;
  title: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="px-5 pt-12 pb-4 flex items-start justify-between gap-4">
      <div>
        <p className="text-white/35 text-xs font-medium mb-0.5">{eyebrow}</p>
        <h2 className="text-white font-black text-2xl" style={DISPLAY_FONT}>
          {title}
        </h2>
      </div>
      {action}
    </div>
  );
}

/** Soft radial colour wash used behind the auth screens. */
export function GlowOrb({
  color = COLORS.orange,
  className = "",
}: {
  color?: string;
  className?: string;
}) {
  return (
    <div
      className={`absolute rounded-full blur-3xl pointer-events-none ${className}`}
      style={{ background: `radial-gradient(circle, ${color}, transparent)` }}
    />
  );
}
