import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { GlowOrb, Screen } from "@/components/Screen";
import { COLORS, DISPLAY_FONT, GOLD_GRAD } from "@/lib/theme";

/**
 * Branded splash shown while the deck is being built, instead of a bare spinner.
 *
 * Deck generation is genuinely slow (an LLM call, then a Swiggy resolve per dish),
 * so rather than hide that we make the wait feel intentional: an orbiting plate of
 * cuisines, a breathing logo, and status lines that narrate what's actually
 * happening. Purely cosmetic — it never gates or delays the fetch itself.
 */

const ORBIT = ["🍛", "🍕", "🍜", "🌮", "🍣", "🥗"];

const STATUS_LINES = [
  "Reading your taste profile…",
  "Checking what you've been ordering…",
  "Scanning restaurants near you…",
  "Skipping anything you're allergic to…",
  "Plating up your picks…",
];

const RING_PX = 248; // ring box size
const ORBIT_RADIUS = 106; // clears the 112px logo tile with room to breathe
const SPIN_SECONDS = 16;

export default function LoadingSplash({ title = "Kya Khaoon" }: { title?: string }) {
  const [line, setLine] = useState(0);

  useEffect(() => {
    const id = setInterval(
      () => setLine((i) => (i + 1) % STATUS_LINES.length),
      1600,
    );
    return () => clearInterval(id);
  }, []);

  return (
    <Screen gradient className="items-center justify-center relative overflow-hidden">
      <motion.div
        className="absolute inset-0"
        animate={{ opacity: [0.55, 1, 0.55] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
      >
        <GlowOrb className="top-10 left-2 w-72 h-72 opacity-25" />
        <GlowOrb className="bottom-24 right-0 w-60 h-60 opacity-20" color={COLORS.gold} />
      </motion.div>

      <div className="z-10 flex flex-col items-center px-8 text-center">
        <div
          className="relative flex items-center justify-center"
          style={{ width: RING_PX, height: RING_PX }}
        >
          <motion.div
            className="absolute inset-0"
            animate={{ rotate: 360 }}
            transition={{ duration: SPIN_SECONDS, repeat: Infinity, ease: "linear" }}
          >
            {ORBIT.map((emoji, i) => {
              const angle = (i / ORBIT.length) * Math.PI * 2;
              return (
                <div
                  key={emoji}
                  className="absolute"
                  style={{
                    left: "50%",
                    top: "50%",
                    marginLeft: Math.cos(angle) * ORBIT_RADIUS - 16,
                    marginTop: Math.sin(angle) * ORBIT_RADIUS - 16,
                    width: 32,
                    height: 32,
                  }}
                >
                  {/* Counter-spin so each dish stays upright as the ring turns. */}
                  <motion.span
                    className="block text-2xl leading-none"
                    animate={{ rotate: -360 }}
                    transition={{
                      duration: SPIN_SECONDS,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  >
                    {emoji}
                  </motion.span>
                </div>
              );
            })}
          </motion.div>

          <motion.div
            className="absolute rounded-full"
            style={{ width: 128, height: 128, background: GOLD_GRAD, filter: "blur(28px)" }}
            animate={{ scale: [1, 1.18, 1], opacity: [0.35, 0.6, 0.35] }}
            transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
          />

          <motion.div
            className="w-28 h-28 rounded-[36px] flex items-center justify-center text-6xl shadow-2xl relative"
            style={{ background: GOLD_GRAD }}
            animate={{ y: [0, -10, 0], scale: [1, 1.04, 1] }}
            transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
          >
            🍽️
          </motion.div>
        </div>

        <motion.h1
          className="text-4xl font-black text-white tracking-tight mt-7"
          style={DISPLAY_FONT}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          {title}
        </motion.h1>

        <div className="h-6 mt-3 flex items-center justify-center">
          <AnimatePresence mode="wait">
            <motion.p
              key={line}
              className="text-white/45 text-sm font-medium"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35 }}
            >
              {STATUS_LINES[line]}
            </motion.p>
          </AnimatePresence>
        </div>

        {/* Indeterminate shimmer — progress is unknowable, so we never fake a %. */}
        <div
          className="mt-7 h-1.5 w-44 rounded-full overflow-hidden"
          style={{ background: "rgba(255,255,255,0.08)" }}
        >
          <motion.div
            className="h-full w-1/2 rounded-full"
            style={{ background: GOLD_GRAD }}
            animate={{ x: ["-100%", "200%"] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      </div>
    </Screen>
  );
}
