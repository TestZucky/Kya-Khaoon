/**
 * Onboarding, in two screens.
 *
 * The split is by *consequence*, not by topic. Screen 1 asks the two things that
 * are hard filters — diet and allergies — because getting them wrong means
 * showing someone food they can't or won't eat. Screen 2 asks the three that
 * only tilt the ranking: budget, cuisines, spice. Everything else either has a
 * safe default (goal), is genuinely optional (body metrics, home region), or is
 * per-meal rather than permanent (mood, party size — asked on every open).
 *
 * The optional editors live here too and are exported for the profile screen, so
 * a user who wants to tune those can, without any of it blocking a first deck.
 */

import { Check, ShieldCheck } from "lucide-react";
import {
  ALLERGY_OPTIONS,
  BUDGET,
  CUISINES,
  DIET_OPTIONS,
  HEALTH_GOALS,
  INDIAN_STATES,
  SPICE_LEVELS,
  splitEmojiLabel,
} from "@/data/preferences";
import { DISPLAY_FONT, GOLD_GRAD, ORANGE_GRAD } from "@/lib/theme";
import { useAppState } from "@/state/AppState";

// Body-metric slider bounds — wide enough for adults; only used when the user opts in.
const HEIGHT = { min: 120, max: 220, step: 1, default: 170 };
const WEIGHT = { min: 30, max: 200, step: 1, default: 65 };

/** BMI + a friendly category label for a live readout. */
function bmiReadout(heightCm: number, weightKg: number): { value: number; label: string; color: string } {
  const bmi = weightKg / (heightCm / 100) ** 2;
  const value = Math.round(bmi * 10) / 10;
  if (bmi < 18.5) return { value, label: "Underweight", color: "#5AC8FA" };
  if (bmi < 25) return { value, label: "Healthy range", color: "#34C759" };
  if (bmi < 30) return { value, label: "Overweight", color: "#FFB830" };
  return { value, label: "Obese", color: "#FF4B6E" };
}

function StepHeader({ level, title, sub }: { level: string; title: string; sub: string }) {
  return (
    <div>
      <p className="text-xs text-orange-400 font-black uppercase tracking-widest mb-1">
        {level}
      </p>
      <h2 className="text-3xl font-black text-white" style={DISPLAY_FONT}>
        {title}
      </h2>
      <p className="text-white/35 mt-1 text-sm">{sub}</p>
    </div>
  );
}

/** Labels one question inside a merged screen. */
export function SectionLabel({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <h3 className="text-white font-bold text-base">{title}</h3>
      {sub && <span className="text-white/30 text-xs flex-shrink-0">{sub}</span>}
    </div>
  );
}

// ── Individual pickers ──────────────────────────────────────────────────────

function DietPicker() {
  const { prefs, togglePref } = useAppState();
  return (
    <div className="flex flex-wrap gap-2.5">
      {DIET_OPTIONS.map((d) => {
        const sel = prefs.diet.includes(d);
        const [emoji, label] = splitEmojiLabel(d);
        return (
          <button
            key={d}
            onClick={() => togglePref("diet", d)}
            aria-pressed={sel}
            className="px-4 py-2.5 rounded-2xl flex items-center gap-2 text-sm font-semibold transition-all active:scale-95"
            style={{
              background: sel ? "rgba(255,101,52,0.12)" : "rgba(255,255,255,0.05)",
              border: `1px solid ${sel ? "rgba(255,101,52,0.45)" : "rgba(255,255,255,0.09)"}`,
              color: sel ? "#FF6534" : "rgba(255,255,255,0.55)",
            }}
          >
            <span className="text-base">{emoji}</span>
            {label}
            {sel && <Check size={14} className="flex-shrink-0" />}
          </button>
        );
      })}
    </div>
  );
}

function AllergyPicker() {
  const { prefs, togglePref } = useAppState();
  const none = prefs.allergies.length === 0;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2.5">
        {ALLERGY_OPTIONS.map((a) => {
          const sel = prefs.allergies.includes(a);
          return (
            <button
              key={a}
              onClick={() => togglePref("allergies", a)}
              aria-pressed={sel}
              className="px-4 py-2.5 rounded-2xl text-sm font-semibold transition-all active:scale-95"
              style={{
                background: sel ? "rgba(255,75,110,0.18)" : "rgba(255,255,255,0.05)",
                border: `1px solid ${sel ? "#FF4B6E" : "rgba(255,255,255,0.09)"}`,
                color: sel ? "#FF4B6E" : "rgba(255,255,255,0.50)",
              }}
            >
              {a}
            </button>
          );
        })}
      </div>
      <div
        className="flex items-center gap-3 p-3.5 rounded-2xl"
        style={{
          background: none ? "rgba(255,255,255,0.04)" : "rgba(255,75,110,0.08)",
          border: `1px solid ${none ? "rgba(255,255,255,0.07)" : "rgba(255,75,110,0.18)"}`,
        }}
      >
        <ShieldCheck
          size={18}
          className="flex-shrink-0"
          style={{ color: none ? "rgba(255,255,255,0.35)" : "#FF4B6E" }}
        />
        <span className="text-sm" style={{ color: "rgba(255,255,255,0.6)" }}>
          {none
            ? "Nothing selected — you'll see everything."
            : `We'll hide anything with ${prefs.allergies
                .map((a) => splitEmojiLabel(a)[1].toLowerCase())
                .join(", ")}.`}
        </span>
      </div>
    </div>
  );
}

function BudgetPicker() {
  const { prefs, setPref } = useAppState();
  const pct = ((prefs.budget - BUDGET.min) / (BUDGET.max - BUDGET.min)) * 100;
  return (
    <div className="flex flex-col gap-4">
      <div
        className="rounded-3xl p-5 flex flex-col items-center gap-5"
        style={{
          background: "rgba(255,255,255,0.04)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <span className="text-5xl font-black text-white" style={DISPLAY_FONT}>
          ₹{prefs.budget}
        </span>
        <div
          className="w-full relative h-2 rounded-full"
          style={{ background: "rgba(255,255,255,0.10)" }}
        >
          <div
            className="absolute top-0 left-0 h-full rounded-full transition-all"
            style={{ width: `${pct}%`, background: GOLD_GRAD }}
          />
          <input
            type="range"
            aria-label="Budget per meal"
            min={BUDGET.min}
            max={BUDGET.max}
            step={BUDGET.step}
            value={prefs.budget}
            onChange={(e) => setPref("budget", Number(e.target.value))}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
        </div>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {BUDGET.presets.map((v) => {
          const sel = prefs.budget === v;
          return (
            <button
              key={v}
              onClick={() => setPref("budget", v)}
              className="py-2 rounded-xl text-sm font-bold transition-all active:scale-95"
              style={{
                background: sel ? "rgba(255,101,52,0.15)" : "rgba(255,255,255,0.04)",
                border: `1px solid ${sel ? "rgba(255,101,52,0.4)" : "rgba(255,255,255,0.07)"}`,
                color: sel ? "#FF6534" : "rgba(255,255,255,0.4)",
              }}
            >
              ₹{v}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function CuisinePicker() {
  const { prefs, togglePref } = useAppState();
  return (
    <div className="flex flex-wrap gap-2.5">
      {CUISINES.map((c) => {
        const sel = prefs.cuisines.includes(c);
        return (
          <button
            key={c}
            onClick={() => togglePref("cuisines", c)}
            aria-pressed={sel}
            className="px-4 py-2.5 rounded-2xl text-sm font-semibold transition-all active:scale-95"
            style={{
              background: sel ? ORANGE_GRAD : "rgba(255,255,255,0.05)",
              border: `1px solid ${sel ? "transparent" : "rgba(255,255,255,0.09)"}`,
              color: sel ? "white" : "rgba(255,255,255,0.50)",
              transform: sel ? "scale(1.04)" : "scale(1)",
            }}
          >
            {c}
          </button>
        );
      })}
    </div>
  );
}

function SpicePicker() {
  const { prefs, setPref } = useAppState();
  const level = SPICE_LEVELS[prefs.spiceLevel];
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex items-center gap-3">
        <span className="text-4xl select-none">{level.emoji}</span>
        <p className="text-white font-black text-lg">{level.label}</p>
      </div>
      <div className="flex gap-2.5 w-full">
        {SPICE_LEVELS.map((s, i) => (
          <button
            key={s.label}
            onClick={() => setPref("spiceLevel", i)}
            aria-label={s.label}
            className="flex-1 h-3 rounded-full transition-all active:scale-95"
            style={{
              background:
                i <= prefs.spiceLevel
                  ? `hsl(${20 - i * 4}, 90%, ${62 - i * 8}%)`
                  : "rgba(255,255,255,0.10)",
            }}
          />
        ))}
      </div>
      <div className="flex justify-between w-full text-white/25 text-xs px-0.5">
        <span>Mild 😇</span>
        <span>Devil 👹</span>
      </div>
    </div>
  );
}

// ── The two onboarding screens ──────────────────────────────────────────────

/**
 * Diet and allergies are the hard filters — the answers that decide what we must
 * never show. Home region rides along because it's the same kind of question
 * ("about you") and it's a strong signal: most people want their local food, and
 * the recommender can't guess it from anything else.
 */
function SafetyStep() {
  return (
    <div className="flex-1 flex flex-col gap-7">
      <StepHeader
        level="Step 1 of 2"
        title="A bit about you"
        sub="What you eat, and where you're from 🛡️"
      />
      <div className="flex flex-col gap-3">
        <SectionLabel title="Your diet" sub="pick any" />
        <DietPicker />
      </div>
      <div className="flex flex-col gap-3">
        <SectionLabel title="Anything to avoid?" sub="allergies" />
        <AllergyPicker />
      </div>
      <div className="flex flex-col gap-3">
        <SectionLabel title="Where are you from?" sub="for local favourites" />
        <HomeStatePicker />
      </div>
    </div>
  );
}

/** Soft signals: these tilt the ranking, they never hide a dish. */
function TasteStep() {
  return (
    <div className="flex-1 flex flex-col gap-7">
      <StepHeader
        level="Step 2 of 2"
        title="How you like to eat"
        sub="Rough answers are fine — we learn the rest 🎯"
      />
      <div className="flex flex-col gap-3">
        <SectionLabel title="Budget" sub="per meal" />
        <BudgetPicker />
      </div>
      <div className="flex flex-col gap-3">
        <SectionLabel title="Cuisines you love" sub="optional" />
        <CuisinePicker />
      </div>
      <div className="flex flex-col gap-3">
        <SectionLabel title="How spicy?" />
        <SpicePicker />
      </div>
    </div>
  );
}

export const ONBOARDING_STEPS = [SafetyStep, TasteStep];

// ── Optional extras — rendered on the profile screen, never in onboarding ────

export function GoalPicker() {
  const { prefs, setPref } = useAppState();
  return (
    <div className="grid grid-cols-2 gap-3">
      {HEALTH_GOALS.map((g, i) => {
        const sel = prefs.goal === i;
        return (
          <button
            key={g.label}
            onClick={() => setPref("goal", sel ? null : i)}
            aria-pressed={sel}
            className="p-4 rounded-3xl flex flex-col gap-1.5 transition-all active:scale-95 text-left"
            style={{
              background: sel ? "rgba(255,101,52,0.12)" : "rgba(255,255,255,0.04)",
              border: `2px solid ${sel ? "#FF6534" : "rgba(255,255,255,0.07)"}`,
            }}
          >
            <span className="text-2xl">{g.icon}</span>
            <span
              className="font-bold text-sm"
              style={{ color: sel ? "white" : "rgba(255,255,255,0.65)" }}
            >
              {g.label}
            </span>
            <span
              className="text-xs"
              style={{ color: sel ? "#FF6534" : "rgba(255,255,255,0.30)" }}
            >
              {g.sub}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export function BodyPicker() {
  const { prefs, setPref } = useAppState();
  const on = prefs.heightCm !== null && prefs.weightKg !== null;
  const bmi = on ? bmiReadout(prefs.heightCm!, prefs.weightKg!) : null;

  if (!on) {
    return (
      <button
        onClick={() => {
          setPref("heightCm", HEIGHT.default);
          setPref("weightKg", WEIGHT.default);
        }}
        className="px-5 py-3 rounded-2xl text-sm font-bold text-white active:scale-95 transition-all self-start"
        style={{ background: ORANGE_GRAD }}
      >
        Add height &amp; weight
      </button>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <SliderRow
        label="Height"
        unit="cm"
        value={prefs.heightCm!}
        min={HEIGHT.min}
        max={HEIGHT.max}
        step={HEIGHT.step}
        onChange={(v) => setPref("heightCm", v)}
      />
      <SliderRow
        label="Weight"
        unit="kg"
        value={prefs.weightKg!}
        min={WEIGHT.min}
        max={WEIGHT.max}
        step={WEIGHT.step}
        onChange={(v) => setPref("weightKg", v)}
      />
      {bmi && (
        <div
          className="rounded-2xl p-4 flex items-center justify-between"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div>
            <p className="text-white/40 text-xs">Your BMI</p>
            <p className="text-2xl font-black" style={{ color: bmi.color }}>
              {bmi.value}
            </p>
          </div>
          <span
            className="text-sm font-bold px-3 py-1.5 rounded-full"
            style={{ background: `${bmi.color}22`, color: bmi.color }}
          >
            {bmi.label}
          </span>
        </div>
      )}
      <button
        onClick={() => {
          setPref("heightCm", null);
          setPref("weightKg", null);
        }}
        className="self-center text-white/35 text-sm font-medium active:scale-95 transition-all"
      >
        Remove my stats
      </button>
    </div>
  );
}

export function HomeStatePicker() {
  const { prefs, setPref } = useAppState();
  return (
    <div
      className="rounded-2xl px-4 py-3.5"
      style={{
        background: "rgba(255,255,255,0.05)",
        border: `1px solid ${
          prefs.homeState ? "rgba(255,101,52,0.4)" : "rgba(255,255,255,0.09)"
        }`,
      }}
    >
      <label className="text-white/35 text-xs font-medium">Home state</label>
      <select
        value={prefs.homeState ?? ""}
        onChange={(e) => setPref("homeState", e.target.value || null)}
        className="w-full bg-transparent text-white text-base font-semibold outline-none mt-0.5"
        style={{ colorScheme: "dark" }}
      >
        <option value="">Not set</option>
        {INDIAN_STATES.map((s) => (
          <option key={s} value={s} className="text-black">
            {s}
          </option>
        ))}
      </select>
    </div>
  );
}

function SliderRow({
  label,
  unit,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex justify-between items-baseline">
        <span className="text-white/50 text-sm font-semibold">{label}</span>
        <span className="text-white font-black text-lg" style={DISPLAY_FONT}>
          {value}
          <span className="text-white/35 text-sm font-medium"> {unit}</span>
        </span>
      </div>
      <div
        className="w-full relative h-2 rounded-full"
        style={{ background: "rgba(255,255,255,0.10)" }}
      >
        <div
          className="absolute top-0 left-0 h-full rounded-full transition-all"
          style={{ width: `${pct}%`, background: GOLD_GRAD }}
        />
        <input
          type="range"
          aria-label={`${label} in ${unit}`}
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
    </div>
  );
}
