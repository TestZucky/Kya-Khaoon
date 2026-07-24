import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Check, ChevronLeft, Loader2 } from "lucide-react";
import { Screen } from "@/components/Screen";
import { GhostButton } from "@/components/Button";
import { DISPLAY_FONT, GOLD_GRAD, ORANGE_GRAD } from "@/lib/theme";
import { HEALTH_GOALS, SPICE_LEVELS } from "@/data/preferences";
import { BodyPicker, GoalPicker } from "@/screens/onboarding/steps";
import { startSwiggyConnect, swiggyStatus } from "@/lib/api";
import { useAppState } from "@/state/AppState";

/**
 * Just the taste profile. Orders, ratings and delivery tracking stay in Swiggy —
 * this app only owns the preferences that drive the picks.
 */
export default function ProfileScreen() {
  const navigate = useNavigate();
  const { prefs, submitOnboarding } = useAppState();
  const [params] = useSearchParams();
  const returned = params.get("swiggy"); // "connected" | "error" after OAuth
  const [connected, setConnected] = useState<boolean | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [extrasOpen, setExtrasOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // The optional extras write through the same upserting /onboard call the
  // onboarding flow uses, so there's one code path for "save my profile".
  const saveExtras = async () => {
    setSaving(true);
    const ok = await submitOnboarding();
    setSaving(false);
    setSaved(ok);
  };

  useEffect(() => {
    void swiggyStatus().then(setConnected);
  }, [returned]);

  const connectSwiggy = async () => {
    setConnecting(true);
    try {
      window.location.href = await startSwiggyConnect();
    } catch {
      setConnecting(false);
    }
  };

  const rows: [string, string][] = [
    ["Budget", `₹${prefs.budget} per meal`],
    ["Spice", SPICE_LEVELS[prefs.spiceLevel].label],
    ["Diet", prefs.diet.length ? strip(prefs.diet).join(", ") : "Anything"],
    ["From", prefs.homeState ?? "Not set"],
    ["Goal", prefs.goal !== null ? HEALTH_GOALS[prefs.goal].label : "Not set"],
    [
      "Usually eating for",
      prefs.partySize === 1 ? "Just me" : `${prefs.partySize} people`,
    ],
  ];

  return (
    <Screen gradient className="px-5 pt-12 pb-8">
      <button
        onClick={() => navigate(-1)}
        className="text-white/40 mb-6 w-fit"
        aria-label="Back to picks"
      >
        <ChevronLeft size={26} />
      </button>

      <div className="flex items-center gap-4 mb-7">
        <div
          className="w-16 h-16 rounded-[22px] flex items-center justify-center text-3xl flex-shrink-0"
          style={{ background: GOLD_GRAD }}
        >
          🧑‍🍳
        </div>
        <div className="min-w-0">
          <h1 className="text-white font-black text-2xl" style={DISPLAY_FONT}>
            Your taste
          </h1>
          <p className="text-white/35 text-sm">
            {prefs.phone ? `+91 ${prefs.phone}` : "Signed in"}
          </p>
        </div>
      </div>

      <Section title="Swiggy">
        {connected ? (
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ background: "rgba(34,197,94,0.15)" }}
            >
              <Check size={18} className="text-green-400" />
            </div>
            <div>
              <p className="text-white font-bold text-sm">Connected 🎉</p>
              <p className="text-white/40 text-xs">
                Orders add straight to your real Swiggy cart.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-white/50 text-sm">
              Connect your Swiggy account so picks resolve to real dishes and
              &ldquo;Order&rdquo; adds to your actual cart.
            </p>
            {returned === "error" && (
              <p className="text-sm" style={{ color: "#FF4B6E" }}>
                Connection didn&apos;t complete — try again.
              </p>
            )}
            <button
              onClick={() => void connectSwiggy()}
              disabled={connecting || connected === null}
              className="w-full py-3 rounded-2xl text-white font-black flex items-center justify-center gap-2 active:scale-95 transition-all disabled:opacity-60"
              style={{ background: ORANGE_GRAD }}
            >
              {connecting ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Opening Swiggy…
                </>
              ) : (
                "🔗 Connect Swiggy"
              )}
            </button>
          </div>
        )}
      </Section>

      <Section title="Preferences">
        <div className="flex flex-col gap-3">
          {rows.map(([label, value]) => (
            <div key={label} className="flex items-baseline justify-between gap-4">
              <span className="text-white/35 text-sm flex-shrink-0">{label}</span>
              <span className="text-white/75 text-sm font-semibold text-right">
                {value}
              </span>
            </div>
          ))}
        </div>
      </Section>

      {/*
        These three used to be onboarding steps. They're genuinely optional —
        each has a safe default — so they moved here rather than standing between
        a new user and their first deck.
      */}
      <Section title="Make picks smarter (optional)">
        {!extrasOpen ? (
          <button
            onClick={() => setExtrasOpen(true)}
            className="text-sm font-bold text-orange-400 active:scale-95 transition-all"
          >
            + Health goal, body stats
          </button>
        ) : (
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-3">
              <p className="text-white/35 text-xs font-medium">Health goal</p>
              <GoalPicker />
            </div>
            <div className="flex flex-col gap-3">
              <p className="text-white/35 text-xs font-medium">
                Height &amp; weight — tunes how hearty your picks are
              </p>
              <BodyPicker />
            </div>
            <button
              onClick={() => void saveExtras()}
              disabled={saving}
              className="w-full py-3 rounded-2xl text-white font-black active:scale-95 transition-all disabled:opacity-60"
              style={{ background: ORANGE_GRAD }}
            >
              {saving ? "Saving…" : saved ? "Saved ✓" : "Save"}
            </button>
          </div>
        )}
      </Section>

      {prefs.allergies.length > 0 && (
        <Section title="Never recommend">
          <div className="flex flex-wrap gap-2">
            {prefs.allergies.map((a) => (
              <span
                key={a}
                className="px-3.5 py-1.5 rounded-xl text-sm font-semibold"
                style={{
                  background: "rgba(255,75,110,0.12)",
                  border: "1px solid rgba(255,75,110,0.25)",
                  color: "#FF4B6E",
                }}
              >
                {a}
              </span>
            ))}
          </div>
        </Section>
      )}

      {prefs.cuisines.length > 0 && (
        <Section title="Cuisines you love">
          <div className="flex flex-wrap gap-2">
            {prefs.cuisines.map((c) => (
              <span
                key={c}
                className="px-3.5 py-1.5 rounded-xl text-sm font-semibold"
                style={{
                  background: "rgba(255,101,52,0.10)",
                  border: "1px solid rgba(255,101,52,0.20)",
                  color: "#FF6534",
                }}
              >
                {c}
              </span>
            ))}
          </div>
        </Section>
      )}

      <div className="flex-1" />

      {/*
        No sign-out. Under device identity this browser *is* the account, so
        "sign out" could only blank the local copy while the server kept the
        profile — the next reload would silently restore it. Changing your
        answers is what people actually want here, and that's this button.
      */}
      <div className="flex flex-col gap-3 mt-8">
        <GhostButton onClick={() => navigate("/onboarding")} className="w-full">
          Edit preferences
        </GhostButton>
      </div>
    </Screen>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-5">
      <p className="text-white/30 text-[10px] font-black uppercase tracking-widest mb-3">
        {title}
      </p>
      <div
        className="p-4 rounded-3xl"
        style={{
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.07)",
        }}
      >
        {children}
      </div>
    </div>
  );
}

/** "🥦 Pure Veg" → "Pure Veg" — the emoji is redundant in a dense list. */
const strip = (values: string[]) =>
  values.map((v) => v.split(" ").slice(1).join(" "));
