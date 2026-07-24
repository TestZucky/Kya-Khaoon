import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { ChevronLeft } from "lucide-react";
import { Screen } from "@/components/Screen";
import { PrimaryButton } from "@/components/Button";
import { DISPLAY_FONT } from "@/lib/theme";
import { useAppState } from "@/state/AppState";

const OTP_LENGTH = 6;
const KEYS = [1, 2, 3, 4, 5, 6, 7, 8, 9, "", 0, "⌫"] as const;

export default function OtpScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const { prefs, verifyOtp, requestOtp } = useAppState();

  // In dev (console SMS) the code is passed from the login screen — prefill it so
  // you can log in without reading the server log. Empty in production.
  const devCode = (location.state as { devCode?: string } | null)?.devCode ?? "";
  const [digits, setDigits] = useState<string[]>(() =>
    devCode
      ? [...devCode.padEnd(OTP_LENGTH, " ")].slice(0, OTP_LENGTH).map((c) => c.trim())
      : Array(OTP_LENGTH).fill(""),
  );
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  const code = digits.join("");
  const complete = code.length === OTP_LENGTH && digits.every(Boolean);

  const press = (key: (typeof KEYS)[number]) => {
    if (key === "") return;
    setError(null);
    setDigits((prev) => {
      const next = [...prev];
      if (key === "⌫") {
        const last = next.map(Boolean).lastIndexOf(true);
        if (last >= 0) next[last] = "";
      } else {
        const slot = next.indexOf("");
        if (slot >= 0) next[slot] = String(key);
      }
      return next;
    });
  };

  const submit = async () => {
    if (!complete || verifying) return;
    setVerifying(true);
    setError(null);
    const result = await verifyOtp(code);
    setVerifying(false);
    if (result.ok) {
      // Returning users go straight to picks; new users connect Swiggy first.
      navigate(result.onboarded ? "/picks" : "/connect", { replace: true });
    } else {
      setError(result.error);
      setDigits(Array(OTP_LENGTH).fill(""));
    }
  };

  const resend = async () => {
    setError(null);
    const r = await requestOtp(prefs.phone);
    if (!r.ok) setError(r.error);
    else if (r.devCode) setDigits([...r.devCode]);
  };

  return (
    <Screen gradient className="px-6 pt-14 pb-8 relative overflow-hidden">
      <button
        onClick={() => navigate("/login")}
        className="text-white/40 mb-8 w-fit"
        aria-label="Back"
      >
        <ChevronLeft size={26} />
      </button>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-1 flex flex-col"
      >
        <div className="mb-8">
          <p className="text-orange-400 font-bold text-sm mb-2">OTP sent 📱</p>
          <h2 className="text-4xl font-black text-white" style={DISPLAY_FONT}>
            Verify it&apos;s you
          </h2>
          <p className="text-white/35 mt-2 text-sm">
            Sent to +91 {prefs.phone || "XXXXXXXXXX"}
          </p>
        </div>

        <div className="flex gap-2 mb-6">
          {digits.map((digit, i) => (
            <div
              key={i}
              className="flex-1 h-14 rounded-2xl flex items-center justify-center text-2xl font-black text-white transition-all"
              style={{
                background: digit ? "rgba(255,101,52,0.15)" : "rgba(255,255,255,0.05)",
                border: `2px solid ${digit ? "#FF6534" : "rgba(255,255,255,0.08)"}`,
              }}
            >
              {digit || "·"}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-2 mb-4">
          {KEYS.map((key, i) => (
            <button
              key={i}
              onClick={() => press(key)}
              aria-label={key === "⌫" ? "Delete" : String(key)}
              className={`h-14 rounded-2xl text-white text-xl font-bold active:scale-95 transition-all ${
                key === "" ? "pointer-events-none opacity-0" : ""
              }`}
              style={{ background: key === "" ? "transparent" : "rgba(255,255,255,0.06)" }}
            >
              {key}
            </button>
          ))}
        </div>

        {error && (
          <p className="text-center text-sm mb-3" style={{ color: "#FF4B6E" }}>
            {error}
          </p>
        )}

        <PrimaryButton
          enabled={complete && !verifying}
          onClick={() => void submit()}
          className="text-white"
        >
          {verifying ? "Verifying…" : "Verify & Continue"}
        </PrimaryButton>

        <button
          onClick={() => void resend()}
          className="text-white/35 text-xs font-medium py-3 mt-1 active:scale-95 transition-all"
        >
          Didn&apos;t get it? Resend code
        </button>
      </motion.div>
    </Screen>
  );
}
