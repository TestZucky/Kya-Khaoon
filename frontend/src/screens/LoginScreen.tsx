import { useCallback, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { ChevronLeft, Phone } from "lucide-react";
import { GlowOrb, Screen } from "@/components/Screen";
import { PrimaryButton } from "@/components/Button";
import { GoogleSignInButton } from "@/components/GoogleSignInButton";
import { DISPLAY_FONT } from "@/lib/theme";
import { useAppState } from "@/state/AppState";

export default function LoginScreen() {
  const navigate = useNavigate();
  const {
    prefs,
    setPref,
    requestOtp,
    loginWithGoogle,
    authed,
    authReady,
    authError,
    retrySignIn,
  } = useAppState();
  const complete = prefs.phone.length === 10;
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onGoogle = useCallback(
    async (idToken: string) => {
      setError(null);
      const result = await loginWithGoogle(idToken);
      if (result.ok) {
        // New users connect Swiggy first; returning ones go straight to picks.
        navigate(result.onboarded ? "/picks" : "/connect", { replace: true });
      } else {
        setError(result.error);
      }
    },
    [loginWithGoogle, navigate],
  );

  // Phone/OTP is kept but disabled for now — SMS isn't wired.
  const OTP_ENABLED = false;

  // Device sign-in makes this screen unreachable in the normal flow; it stays
  // for when Google/OTP come back. Anyone landing here (stale link, back
  // button) already has a session, so send them onward.
  if (authReady && authed) {
    return <Navigate to={prefs.onboarded ? "/picks" : "/connect"} replace />;
  }

  const submit = async () => {
    if (!complete || sending) return;
    setSending(true);
    setError(null);
    const result = await requestOtp(prefs.phone);
    setSending(false);
    if (result.ok) {
      // In console/dev mode the code rides along so the OTP screen can prefill it.
      navigate("/otp", { state: { devCode: result.devCode } });
    } else {
      setError(result.error);
    }
  };

  return (
    <Screen gradient className="px-6 pt-14 pb-8 relative overflow-hidden">
      <GlowOrb className="-top-10 right-0 w-64 h-64 opacity-20" />

      <button
        onClick={() => navigate("/")}
        className="text-white/40 mb-8 w-fit"
        aria-label="Back"
      >
        <ChevronLeft size={26} />
      </button>

      <motion.form
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-1 flex flex-col"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <div className="mb-6">
          <p className="text-orange-400 font-bold text-sm mb-2">Welcome 👋</p>
          <h2 className="text-4xl font-black text-white" style={DISPLAY_FONT}>
            Sign in
          </h2>
          <p className="text-white/35 mt-2 text-sm">
            One tap and your taste is saved for good.
          </p>
        </div>

        {/* Reaching this screen at all usually means the silent device sign-in
            failed, so say what went wrong instead of showing a dead form. */}
        {authError && (
          <div
            className="rounded-2xl p-4 mb-6"
            style={{
              background: "rgba(255,75,110,0.10)",
              border: "1px solid rgba(255,75,110,0.30)",
            }}
          >
            <p className="text-sm mb-3" style={{ color: "#FF4B6E" }}>
              {authError}
            </p>
            <button
              type="button"
              onClick={() => void retrySignIn()}
              className="text-white/70 text-sm font-bold underline underline-offset-4"
            >
              Try again
            </button>
          </div>
        )}

        <div className="mb-6">
          <GoogleSignInButton onCredential={onGoogle} />
        </div>

        <div className="flex items-center gap-3 mb-5">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-white/25 text-xs">phone (soon)</span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        {/* Phone/OTP kept but disabled for now — not selectable. */}
        <fieldset
          disabled={!OTP_ENABLED}
          className={OTP_ENABLED ? "" : "opacity-40 pointer-events-none select-none"}
          aria-hidden={!OTP_ENABLED}
        >
          <label
            className="rounded-2xl p-4 flex items-center gap-3 mb-4"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.10)",
            }}
          >
            <span className="text-white/50 text-sm font-bold border-r border-white/15 pr-3 flex-shrink-0">
              🇮🇳 +91
            </span>
            <input
              type="tel"
              inputMode="numeric"
              autoComplete="tel-national"
              placeholder="98765 43210"
              value={prefs.phone}
              tabIndex={-1}
              onChange={(e) =>
                setPref("phone", e.target.value.replace(/\D/g, "").slice(0, 10))
              }
              className="bg-transparent text-white text-lg font-medium outline-none flex-1 placeholder:text-white/20"
            />
          </label>

          <PrimaryButton type="submit" enabled={OTP_ENABLED && complete && !sending}>
            <Phone size={18} /> {sending ? "Sending…" : "Get OTP"}
          </PrimaryButton>
        </fieldset>

        {error && (
          <p className="text-center text-sm mt-4" style={{ color: "#FF4B6E" }}>
            {error}
          </p>
        )}

        <div className="flex-1" />
        <p className="text-white/20 text-xs text-center">
          By continuing you agree to our Terms &amp; Privacy Policy
        </p>
      </motion.form>
    </Screen>
  );
}
