import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, Loader2, X } from "lucide-react";
import { Screen } from "@/components/Screen";
import { DeckShadowCard, SwipeCard } from "@/components/SwipeCard";
import LoadingSplash from "@/screens/LoadingSplash";
import { useSwipeDeck } from "@/hooks/useSwipeDeck";
import { DISPLAY_FONT, GOLD_GRAD, ORANGE_GRAD } from "@/lib/theme";
import { mealNow, type MealPeriod } from "@/lib/mapPrefs";
import { useAppState } from "@/state/AppState";

/**
 * Floor for the boot splash. The deck fetch usually outlasts this; the floor only
 * stops a warm/cached load from flashing the splash for 80ms. It never delays the
 * fetch — raise it if you want a longer branded moment on fast connections.
 */
const MIN_SPLASH_MS = 1800;

const MEAL_TITLE: Record<MealPeriod, string> = {
  breakfast: "Breakfast picks ☀️",
  lunch: "Lunch picks 🍚",
  snack: "Evening picks 🌇",
  dinner: "Dinner picks 🌙",
  late_night: "Late-night picks 🌃",
};

/**
 * The whole app after onboarding: a full-screen deck of AI picks, swipe right to
 * order, left to skip.
 */
export default function PicksScreen() {
  const navigate = useNavigate();
  const { deck, deckSize, deckStatus, deckError, fetchDeck, likeTop, prefs, skipTop } =
    useAppState();

  const [minSplashDone, setMinSplashDone] = useState(false);

  useEffect(() => {
    if (deckStatus === "idle") void fetchDeck();
  }, [deckStatus, fetchDeck]);

  useEffect(() => {
    const id = setTimeout(() => setMinSplashDone(true), MIN_SPLASH_MS);
    return () => clearTimeout(id);
  }, []);

  const top = deck[0];
  const hasNext = deck.length > 1;
  const seen = deckSize - deck.length;
  const title = MEAL_TITLE[mealNow()] ?? "Today's picks 🍽️";

  const handleLike = useCallback(() => {
    if (likeTop()) navigate("/match");
  }, [likeTop, navigate]);

  const swipe = useSwipeDeck({ onLike: handleLike, onSkip: skipTop });
  const showDeck = deckStatus === "ready" && !!top;

  // Cold open (app boot / reload): take over the whole screen with the branded
  // splash rather than showing an empty deck frame. Refreshes mid-session keep the
  // inline spinner, and an error always wins so failures stay visible.
  const coldOpen = deckSize === 0 && deckStatus !== "error";
  if (coldOpen && (deckStatus !== "ready" || !minSplashDone)) {
    return <LoadingSplash />;
  }

  return (
    <Screen>
      <div className="flex items-center justify-between px-5 pt-12 pb-2">
        <div>
          <h1 className="text-white font-black text-2xl leading-tight" style={DISPLAY_FONT}>
            {title}
          </h1>
          <p className="text-white/35 text-xs font-medium mt-0.5">
            {showDeck
              ? `${seen + 1} of ${deckSize} · ${
                  prefs.partySize > 1 ? `prices for ${prefs.partySize}` : "swipe to decide"
                }`
              : "Kya Khaoon?"}
          </p>
        </div>
        <button
          onClick={() => navigate("/profile")}
          aria-label="Your preferences"
          className="w-11 h-11 rounded-[16px] flex items-center justify-center text-xl shadow-lg flex-shrink-0"
          style={{ background: GOLD_GRAD }}
        >
          🧑‍🍳
        </button>
      </div>

      <div className="flex-1 relative min-h-0 mx-4 mt-2">
        {deckStatus === "loading" && <DeckMessage loading text="Cooking up your picks…" />}

        {deckStatus === "error" && (
          <DeckMessage
            emoji="📡"
            title="Couldn't load your picks"
            text={deckError ?? "Something went wrong"}
            action={{ label: "Try again", onClick: () => void fetchDeck() }}
          />
        )}

        {deckStatus === "ready" &&
          (top ? (
            <>
              {hasNext && <DeckShadowCard />}
              <SwipeCard
                pick={top}
                portions={prefs.partySize}
                delta={swipe.delta}
                rotation={swipe.rotation}
                dragging={swipe.dragging}
                stamps={swipe.stamps}
                handlers={swipe.handlers}
              />
            </>
          ) : (
            <DeckMessage
              emoji="😮‍💨"
              title={`That's all ${deckSize}!`}
              text="You've seen today's picks. Come back later for a fresh set."
              action={{ label: "Show me more", onClick: () => void fetchDeck() }}
            />
          ))}
      </div>

      <div className="flex items-center justify-center gap-10 px-5 pt-4 pb-6">
        <ActionButton
          onClick={showDeck ? skipTop : undefined}
          label="Skip"
          color="#FF4B6E"
          bg="rgba(255,75,110,0.12)"
          border="rgba(255,75,110,0.30)"
          disabled={!showDeck}
        >
          <X size={28} style={{ color: "#FF4B6E" }} />
        </ActionButton>
        <ActionButton
          onClick={showDeck ? handleLike : undefined}
          label="Order"
          color="#FF6534"
          bg="rgba(255,101,52,0.18)"
          border="rgba(255,101,52,0.40)"
          disabled={!showDeck}
        >
          <Heart size={28} style={{ color: "#FF6534" }} fill="rgba(255,101,52,0.4)" />
        </ActionButton>
      </div>
    </Screen>
  );
}

function ActionButton({
  children,
  label,
  bg,
  border,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  label: string;
  color: string;
  bg: string;
  border: string;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <button
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
        className="w-16 h-16 rounded-full flex items-center justify-center shadow-xl active:scale-90 transition-all disabled:opacity-30"
        style={{ background: bg, border: `2px solid ${border}` }}
      >
        {children}
      </button>
      <span className="text-white/40 text-[11px] font-semibold">{label}</span>
    </div>
  );
}

function DeckMessage({
  loading,
  emoji,
  title,
  text,
  action,
}: {
  loading?: boolean;
  emoji?: string;
  title?: string;
  text: string;
  action?: { label: string; onClick: () => void };
}) {
  return (
    <div
      className="w-full h-full rounded-[28px] flex flex-col items-center justify-center text-center px-8"
      style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
    >
      {loading ? (
        <Loader2 size={40} className="text-orange-400 animate-spin mb-4" />
      ) : (
        <div className="text-5xl mb-4">{emoji}</div>
      )}
      {title && <p className="text-white font-black text-xl mb-2">{title}</p>}
      <p className="text-white/35 text-sm mb-6">{text}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-6 py-3 rounded-2xl text-white font-bold active:scale-95 transition-all"
          style={{ background: ORANGE_GRAD }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
