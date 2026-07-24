import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Screen } from "@/components/Screen";
import { GhostButton, PrimaryButton } from "@/components/Button";
import { ONBOARDING_STEPS } from "@/screens/onboarding/steps";
import { GOLD_GRAD } from "@/lib/theme";
import { useAppState } from "@/state/AppState";

export default function OnboardingScreen() {
  const navigate = useNavigate();
  const { submitOnboarding, onboardError } = useAppState();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const total = ONBOARDING_STEPS.length;
  const progress = ((step + 1) / total) * 100;
  const StepBody = ONBOARDING_STEPS[step];
  const isLast = step === total - 1;

  const advance = async () => {
    if (!isLast) {
      setStep((s) => s + 1);
      return;
    }
    // Final step: save the profile to the backend, then open the deck.
    setSubmitting(true);
    const ok = await submitOnboarding();
    setSubmitting(false);
    // Straight into "right now" — mood and party size still need asking.
    if (ok) navigate("/right-now", { replace: true });
  };

  return (
    <Screen gradient className="px-6 pt-12 pb-8 relative overflow-hidden">
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2.5">
          <span className="text-white/35 text-xs font-medium">
            Step {step + 1} of {total}
          </span>
          <span className="text-orange-400 text-xs font-black">
            {isLast ? "Almost there 🎉" : "30 seconds ⏱️"}
          </span>
        </div>
        <div className="h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, background: GOLD_GRAD }}
          />
        </div>
      </div>

      <motion.div
        key={step}
        initial={{ opacity: 0, x: 28 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
        // Merged screens run taller than the phone frame — scroll inside the
        // step so the progress bar and buttons stay pinned.
        className="flex-1 flex flex-col overflow-y-auto -mx-1 px-1"
      >
        <StepBody />
      </motion.div>

      {isLast && onboardError && (
        <p className="text-center text-sm mt-4" style={{ color: "#FF4B6E" }}>
          {onboardError}
        </p>
      )}

      <div className="flex gap-3 mt-6">
        {step > 0 && !submitting && (
          <GhostButton className="px-6" onClick={() => setStep((s) => s - 1)}>
            Back
          </GhostButton>
        )}
        <PrimaryButton
          onClick={() => void advance()}
          enabled={!submitting}
          className="flex-1"
        >
          {submitting ? "Saving…" : isLast ? "🚀 Start Eating!" : "Next →"}
        </PrimaryButton>
      </div>
    </Screen>
  );
}
