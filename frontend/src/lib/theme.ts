/**
 * Design tokens lifted from the Kya Khaoon Figma file.
 * Anything colour-ish that appears in more than one screen lives here.
 */

export const COLORS = {
  bg: "#0D0A14",
  surface: "#1A0E2E",
  orange: "#FF6534",
  pink: "#FF4B6E",
  gold: "#FFB830",
  purple: "#C73FAF",
} as const;

export const BG_DARK =
  "linear-gradient(160deg, #1A0A2E 0%, #0D0A14 60%, #140A0A 100%)";
export const ORANGE_GRAD = "linear-gradient(135deg, #FF6534, #FF4B6E)";
export const GOLD_GRAD = "linear-gradient(135deg, #FF6534, #FFB830)";
export const HERO_GRAD =
  "linear-gradient(135deg, #FF6534 0%, #FF4B6E 55%, #C73FAF 100%)";

/** Display face used for every heading in the app. */
export const DISPLAY_FONT = { fontFamily: "'Bricolage Grotesque', sans-serif" };

/** Frosted-glass panel used for cards, inputs and list rows. */
export function glass(active = false) {
  return {
    background: active ? "rgba(255,101,52,0.12)" : "rgba(255,255,255,0.04)",
    border: `1px solid ${active ? "rgba(255,101,52,0.45)" : "rgba(255,255,255,0.07)"}`,
  };
}
