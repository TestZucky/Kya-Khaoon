import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Check, Loader2, MapPin } from "lucide-react";
import { Screen } from "@/components/Screen";
import { PrimaryButton } from "@/components/Button";
import { DISPLAY_FONT, ORANGE_GRAD } from "@/lib/theme";
import { useAppState } from "@/state/AppState";
import type { Address } from "@/lib/api";

/**
 * Delivery location. Every menu/restaurant/cart call is scoped to a Swiggy
 * address, so we pick one before showing food.
 */
export default function AddressScreen() {
  const navigate = useNavigate();
  const { prefs, loadAddresses, chooseAddress } = useAppState();
  const [addresses, setAddresses] = useState<Address[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [attempt, setAttempt] = useState(0); // bump to retry

  useEffect(() => {
    let alive = true;
    setError(null);
    setAddresses(null);
    // One quiet retry — the first real Swiggy call right after connecting can be
    // slow, and a stray failure shouldn't dead-end onboarding.
    const load = (retriesLeft: number): Promise<void> =>
      loadAddresses()
        .then((list) => {
          if (!alive) return;
          setAddresses(list);
          setSelected(list[0]?.id ?? null);
        })
        .catch((e) => {
          if (!alive) return;
          if (retriesLeft > 0) return load(retriesLeft - 1);
          setError(e instanceof Error ? e.message : "Couldn't load your addresses.");
        });
    void load(1);
    return () => {
      alive = false;
    };
  }, [loadAddresses, attempt]);

  const next = prefs.onboarded ? "/picks" : "/onboarding";

  const save = async () => {
    if (!selected || saving) return;
    setSaving(true);
    const ok = await chooseAddress(selected);
    setSaving(false);
    if (ok) navigate(next, { replace: true });
    else setError("Couldn't save that address. Try again.");
  };

  return (
    <Screen gradient className="px-6 pt-14 pb-8 relative overflow-hidden">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-1 flex flex-col"
      >
        <div className="mb-6">
          <p className="text-orange-400 font-bold text-sm mb-2">Deliver to 📍</p>
          <h2 className="text-4xl font-black text-white" style={DISPLAY_FONT}>
            Where are you?
          </h2>
          <p className="text-white/35 mt-2 text-sm">
            We&apos;ll only show food that actually delivers here.
          </p>
        </div>

        {addresses === null && !error && (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 size={32} className="text-orange-400 animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center gap-4 my-8">
            <p className="text-center text-sm" style={{ color: "#FF4B6E" }}>
              {error}
            </p>
            <button
              onClick={() => setAttempt((a) => a + 1)}
              className="px-6 py-3 rounded-2xl text-white font-bold active:scale-95 transition-all"
              style={{ background: ORANGE_GRAD }}
            >
              Try again
            </button>
          </div>
        )}

        {addresses && addresses.length === 0 && (
          <p className="text-white/45 text-sm my-6">
            No saved Swiggy addresses. Add one in the Swiggy app first, then come back.
          </p>
        )}

        <div className="flex flex-col gap-3">
          {addresses?.map((a) => {
            const sel = selected === a.id;
            return (
              <button
                key={a.id}
                onClick={() => setSelected(a.id)}
                className="p-4 rounded-2xl flex items-center gap-3 text-left transition-all active:scale-95"
                style={{
                  background: sel ? "rgba(255,101,52,0.12)" : "rgba(255,255,255,0.04)",
                  border: `1px solid ${sel ? "rgba(255,101,52,0.45)" : "rgba(255,255,255,0.07)"}`,
                }}
              >
                <MapPin
                  size={18}
                  className="flex-shrink-0"
                  style={{ color: sel ? "#FF6534" : "rgba(255,255,255,0.35)" }}
                />
                <div className="flex-1 min-w-0">
                  <p
                    className="font-bold text-sm"
                    style={{ color: sel ? "#FF6534" : "white" }}
                  >
                    {a.label}
                  </p>
                  <p className="text-white/40 text-xs truncate">{a.line}</p>
                </div>
                {sel && <Check size={16} className="text-orange-400 flex-shrink-0" />}
              </button>
            );
          })}
        </div>

        <div className="flex-1" />

        {addresses && addresses.length > 0 && (
          <PrimaryButton
            enabled={!!selected && !saving}
            onClick={() => void save()}
          >
            {saving ? "Saving…" : "Deliver here"}
          </PrimaryButton>
        )}
      </motion.div>
    </Screen>
  );
}
