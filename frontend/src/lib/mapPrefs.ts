/** Translate the onboarding UI's answers into the backend's profile contract. */

import type { Preferences } from "@/state/AppState";
import type { ProfilePayload } from "@/lib/api";
import { PARTY_SIZES, splitEmojiLabel } from "@/data/preferences";

/**
 * Diet is multi-select in the UI but single-valued in the backend, so we send the
 * most restrictive choice. Pescatarian has no backend equivalent — it maps to
 * non_veg (least wrong: still allows fish) and should get real handling later.
 */
const DIET_RANK: Record<string, { value: string; rank: number }> = {
  Vegan: { value: "vegan", rank: 4 },
  "Pure Veg": { value: "veg", rank: 3 },
  Eggetarian: { value: "eggetarian", rank: 2 },
  Pescatarian: { value: "non_veg", rank: 1 },
  "Non-Veg": { value: "non_veg", rank: 0 },
};

function mapDiet(diet: string[]): string {
  let best = { value: "non_veg", rank: -1 };
  for (const option of diet) {
    const [, label] = splitEmojiLabel(option);
    const hit = DIET_RANK[label];
    if (hit && hit.rank > best.rank) best = hit;
  }
  return best.value;
}

function mapBudget(budget: number): string {
  if (budget < 200) return "under_200";
  if (budget <= 350) return "b200_350";
  if (budget <= 500) return "b350_500";
  return "above_500";
}

// HEALTH_GOALS order: Build Muscle, Lose Weight, Maintain, Enjoy Life.
const GOAL_BY_INDEX = ["gain_muscle", "lose_weight", "healthier", "just_decide"];

function mapGoal(goal: number | null): string {
  return goal !== null ? (GOAL_BY_INDEX[goal] ?? "just_decide") : "just_decide";
}

/** "🍛 Indian" → "Indian". */
function mapCuisines(cuisines: string[]): string[] {
  return cuisines.map((c) => splitEmojiLabel(c)[1]);
}

/** "🥛 Dairy" → "dairy" — matches the allergen tokens the backend filters on. */
function mapAllergies(allergies: string[]): string[] {
  return allergies.map((a) => splitEmojiLabel(a)[1].toLowerCase());
}

/**
 * Party size → the backend's `companions` vocabulary (solo | partner | friends |
 * family). Head-count is what the user actually picks; this is the coarse label
 * the recommender and the LLM prompt understand.
 */
export function companionsForParty(people: number): string | undefined {
  const hit = PARTY_SIZES.find((p) => p.people === people);
  return hit?.companions;
}

/** The backend's `MealPeriod` vocabulary — see schemas.py. */
export type MealPeriod = "breakfast" | "lunch" | "snack" | "dinner" | "late_night";

/**
 * Meal period from the device clock — feeds time-aware recommendations.
 *
 * Five windows, not three: 4pm is neither lunch nor dinner in India, it's the
 * chai-and-snack hour, and a 1am craving isn't dinner either. Collapsing those
 * into the neighbouring meal is what made a 4pm open serve a dinner deck.
 */
export function mealNow(date = new Date()): MealPeriod {
  const h = date.getHours();
  if (h >= 4 && h < 11) return "breakfast";
  if (h >= 11 && h < 16) return "lunch";
  if (h >= 16 && h < 19) return "snack"; // evening: chaat, samosa, rolls
  if (h >= 19 && h < 23) return "dinner";
  return "late_night";
}

export function toProfilePayload(prefs: Preferences): ProfilePayload {
  return {
    diet: mapDiet(prefs.diet),
    allergies: mapAllergies(prefs.allergies),
    // Onboarding doesn't ask these yet — the backend supports them for when it does.
    avoided_ingredients: [],
    restrictions: [],
    goal: mapGoal(prefs.goal),
    budget_band: mapBudget(prefs.budget),
    cuisines: mapCuisines(prefs.cuisines),
    adventure_level: "familiar_variety",
    // SPICE_LEVELS index (0 Mild .. 4 Devil Mode) matches Profile.spice_level.
    spice_level: prefs.spiceLevel,
    // Optional body metrics + home region — null when the user skipped them.
    height_cm: prefs.heightCm,
    weight_kg: prefs.weightKg,
    home_state: prefs.homeState,
  };
}
