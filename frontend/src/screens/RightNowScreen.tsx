import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { GlowOrb, Screen } from "@/components/Screen";
import { PrimaryButton } from "@/components/Button";
import { MOODS, PARTY_SIZES } from "@/data/preferences";
import { DISPLAY_FONT, ORANGE_GRAD } from "@/lib/theme";
import { mealNow, type MealPeriod } from "@/lib/mapPrefs";
import { useAppState } from "@/state/AppState";

const GREETING: Record<MealPeriod, string> = {
  breakfast: "Morning 🌅",
  lunch: "Lunchtime 🍚",
  snack: "Evening 🌇",
  dinner: "Dinner time 🌙",
  late_night: "Late night 🌃",
};

/**
 * Two taps before every deck: what mood, and how many people.
 *
 * These are the only two answers that genuinely change meal to meal, which is
 * why they're asked on each open rather than stored in the profile. Mood feeds
 * `Session.mood`; party size feeds `Session.companions` *and* becomes the cart
 * quantity at checkout, so ordering for four adds four portions.
 */
export default function RightNowScreen() {
  const navigate = useNavigate();
  const { setMealContext, prefs } = useAppState();
  const [mood, setMood] = useState<string | null>(null);
  const [party, setParty] = useState<number>(prefs.partySize ?? 1);

  const go = () => {
    setMealContext({ mood, partySize: party });
    // Pushed, not replaced: Back from the deck should land here — "change my
    // mood / party size" is the one useful step backwards. Replacing put the
    // deck on top of whatever preceded this screen, which for a fresh sign-up
    // meant Back dropped the user into the Swiggy connect step they'd finished.
    navigate("/picks");
  };

  return (
    <Screen gradient className="px-6 pt-12 pb-6 relative overflow-hidden">
      <GlowOrb className="-top-12 right-0 w-64 h-64 opacity-20" />

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6"
      >
        <p className="text-orange-400 font-bold text-sm mb-1">
          {GREETING[mealNow()] ?? "Hey 👋"}
        </p>
        <h2 className="text-3xl font-black text-white" style={DISPLAY_FONT}>
          What are you feeling?
        </h2>
      </motion.div>

      <div className="flex-1 flex flex-col gap-7 overflow-y-auto -mx-1 px-1">
        <div className="flex flex-col gap-3">
          <div className="flex items-baseline justify-between">
            <h3 className="text-white font-bold text-base">Mood</h3>
            <span className="text-white/30 text-xs">pick one</span>
          </div>
          <div className="grid grid-cols-3 gap-2.5">
            {MOODS.map((m) => {
              const sel = mood === m.value;
              return (
                <button
                  key={m.value}
                  onClick={() => setMood(sel ? null : m.value)}
                  aria-pressed={sel}
                  className="py-3 px-2 rounded-2xl flex flex-col items-center gap-1.5 transition-all active:scale-95"
                  style={{
                    background: sel ? "rgba(255,101,52,0.14)" : "rgba(255,255,255,0.04)",
                    border: `1.5px solid ${sel ? "#FF6534" : "rgba(255,255,255,0.07)"}`,
                  }}
                >
                  <span className="text-2xl">{m.emoji}</span>
                  <span
                    className="text-xs font-semibold text-center leading-tight"
                    style={{ color: sel ? "white" : "rgba(255,255,255,0.55)" }}
                  >
                    {m.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex items-baseline justify-between">
            <h3 className="text-white font-bold text-base">How many eating?</h3>
            <span className="text-white/30 text-xs">sets the order quantity</span>
          </div>
          <div className="grid grid-cols-5 gap-2">
            {PARTY_SIZES.map((p) => {
              const sel = party === p.people;
              return (
                <button
                  key={p.people}
                  onClick={() => setParty(p.people)}
                  aria-pressed={sel}
                  className="py-3 rounded-2xl flex flex-col items-center gap-1 transition-all active:scale-95"
                  style={{
                    background: sel ? ORANGE_GRAD : "rgba(255,255,255,0.04)",
                    border: `1.5px solid ${sel ? "transparent" : "rgba(255,255,255,0.07)"}`,
                  }}
                >
                  <span className="text-xl">{p.icon}</span>
                  <span
                    className="text-[11px] font-bold"
                    style={{ color: sel ? "white" : "rgba(255,255,255,0.5)" }}
                  >
                    {p.people}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="text-white/30 text-xs">
            {party === 1
              ? "We'll add one portion to your cart."
              : `We'll add ${party} portions to your cart.`}
          </p>
        </div>
      </div>

      <div className="pt-5">
        <PrimaryButton onClick={go} enabled className="w-full">
          Show my picks →
        </PrimaryButton>
        <button
          onClick={go}
          className="w-full text-white/30 text-sm font-medium mt-3 active:scale-95 transition-all"
        >
          Skip — just show me food
        </button>
      </div>
    </Screen>
  );
}
