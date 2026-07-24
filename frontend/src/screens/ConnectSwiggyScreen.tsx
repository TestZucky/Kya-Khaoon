import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "motion/react";
import { Loader2 } from "lucide-react";
import { GlowOrb, Screen } from "@/components/Screen";
import { PrimaryButton } from "@/components/Button";
import { DISPLAY_FONT, GOLD_GRAD } from "@/lib/theme";
import { startSwiggyConnect, swiggyStatus } from "@/lib/api";
import { useAppState } from "@/state/AppState";

/**
 * Required step: connect the user's real Swiggy account. Everything downstream —
 * addresses, dish prices/photos, the cart — is real once this is done. Already
 * connected? We route straight onward.
 */
export default function ConnectSwiggyScreen() {
  const navigate = useNavigate();
  const { prefs } = useAppState();
  const [params] = useSearchParams();
  const returned = params.get("swiggy"); // "connected" | "error" after OAuth
  const [checking, setChecking] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(
    returned === "error" ? "That didn't complete — let's try again." : null,
  );

  const nextStep = useCallback(
    () => navigate(prefs.onboarded ? "/picks" : "/address", { replace: true }),
    [navigate, prefs.onboarded],
  );

  useEffect(() => {
    // The callback just confirmed the connection — trust it and move on, even
    // if a status re-check would race the freshly-stored token on reload.
    if (returned === "connected") {
      nextStep();
      return;
    }
    let alive = true;
    void swiggyStatus().then((connected) => {
      if (!alive) return;
      if (connected) nextStep();
      else setChecking(false);
    });
    return () => {
      alive = false;
    };
  }, [nextStep, returned]);

  const connect = async () => {
    setConnecting(true);
    setError(null);
    try {
      window.location.href = await startSwiggyConnect();
    } catch {
      setConnecting(false);
      setError("Couldn't reach Swiggy. Try again.");
    }
  };

  if (checking) {
    return (
      <Screen gradient className="items-center justify-center">
        <Loader2 size={34} className="text-orange-400 animate-spin" />
      </Screen>
    );
  }

  return (
    <Screen gradient className="px-6 pt-14 pb-10 relative overflow-hidden">
      <GlowOrb className="-top-10 right-0 w-64 h-64 opacity-20" />
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-1 flex flex-col"
      >
        <div className="flex-1 flex flex-col justify-center items-center text-center gap-6">
          <div
            className="w-24 h-24 rounded-[30px] flex items-center justify-center text-5xl shadow-2xl"
            style={{ background: GOLD_GRAD }}
          >
            🛵
          </div>
          <div>
            <h2 className="text-3xl font-black text-white mb-2" style={DISPLAY_FONT}>
              Connect Swiggy
            </h2>
            <p className="text-white/45 text-sm leading-relaxed max-w-xs">
              We find your picks on Swiggy and add them to your cart in one tap.
              You&apos;ll sign in to Swiggy and approve — we never see your password.
            </p>
          </div>
        </div>

        {error && (
          <p className="text-center text-sm mb-4" style={{ color: "#FF4B6E" }}>
            {error}
          </p>
        )}

        <PrimaryButton enabled={!connecting} onClick={() => void connect()}>
          {connecting ? (
            <>
              <Loader2 size={18} className="animate-spin" /> Opening Swiggy…
            </>
          ) : (
            "🔗 Connect Swiggy"
          )}
        </PrimaryButton>
      </motion.div>
    </Screen>
  );
}
