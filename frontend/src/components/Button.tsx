import type { ButtonHTMLAttributes, ReactNode } from "react";
import { ORANGE_GRAD } from "@/lib/theme";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  /** Renders the muted, non-interactive state without hiding the button. */
  enabled?: boolean;
};

/** Full-width gradient CTA used at the bottom of the auth + onboarding flows. */
export function PrimaryButton({
  children,
  enabled = true,
  className = "",
  style,
  ...rest
}: Props) {
  return (
    <button
      {...rest}
      disabled={!enabled || rest.disabled}
      className={`w-full py-4 rounded-2xl font-black text-base flex items-center justify-center gap-2 transition-all ${
        enabled ? "active:scale-95" : "cursor-not-allowed"
      } ${className}`}
      style={{
        background: enabled ? ORANGE_GRAD : "rgba(255,255,255,0.07)",
        color: enabled ? "white" : "rgba(255,255,255,0.3)",
        ...style,
      }}
    >
      {children}
    </button>
  );
}

export function GhostButton({ children, className = "", style, ...rest }: Props) {
  return (
    <button
      {...rest}
      className={`py-4 rounded-2xl font-semibold active:scale-95 transition-all ${className}`}
      style={{
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.08)",
        color: "rgba(255,255,255,0.45)",
        ...style,
      }}
    >
      {children}
    </button>
  );
}
