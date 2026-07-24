export const CUISINES = [
  "🍛 Indian",
  "🍕 Italian",
  "🍜 Chinese",
  "🍣 Japanese",
  "🌮 Mexican",
  "🥗 Healthy",
  "🍔 American",
  "🥘 Middle Eastern",
  "🍲 Thai",
  "🥞 Breakfast",
];

export const DIET_OPTIONS = [
  "🍖 Non-Veg",
  "🥦 Pure Veg",
  "🥚 Eggetarian",
  "🌱 Vegan",
  "🐟 Pescatarian",
];

/**
 * Allergens the user can flag. The label after the emoji lowercases to the token
 * the backend filters on (`dairy`, `gluten`, `soy`, `fish` are in the seeded
 * catalogue today; the rest are stored and take effect as the catalogue grows).
 */
export const ALLERGY_OPTIONS = [
  "🥛 Dairy",
  "🌾 Gluten",
  "🫘 Soy",
  "🐟 Fish",
  "🦐 Shellfish",
  "🥜 Peanuts",
  "🌰 Nuts",
  "🥚 Egg",
];

export const SPICE_LEVELS = [
  { emoji: "😌", label: "Mild" },
  { emoji: "🌶️", label: "Medium" },
  { emoji: "🔥", label: "Spicy" },
  { emoji: "💀", label: "Extra Hot" },
  { emoji: "☠️", label: "Devil Mode" },
];

export const HEALTH_GOALS = [
  { icon: "💪", label: "Build Muscle", sub: "High protein picks" },
  { icon: "🏃", label: "Lose Weight", sub: "Low-cal meals" },
  { icon: "⚖️", label: "Maintain", sub: "Balanced diet" },
  { icon: "😋", label: "Enjoy Life", sub: "No restrictions" },
];

export const COMPANION = [
  { icon: "🧍", label: "Just me", sub: "Solo foodie" },
  // "partner" in the backend still maps to a couple ordering together — the copy
  // makes the "you + partner" reading explicit rather than "ordering for them".
  { icon: "💑", label: "Me + partner", sub: "Couple, date night 💕" },
  { icon: "👫", label: "Friends", sub: "Squad goals" },
  { icon: "👨‍👩‍👧", label: "Family", sub: "Everyone happy" },
];

/**
 * Asked on every app open, not during onboarding — mood is the one thing that
 * genuinely changes meal to meal.
 *
 * `value` is what the backend stores on Session.mood. The scorer maps some of
 * these to a target dish heaviness (`_MOOD_HEAVINESS` in concepts.py); the rest
 * get no heaviness nudge and rely on the LLM, which reads them verbatim. Adding
 * a mood here is safe either way — an unmapped one is never silently dropped.
 */
export const MOODS = [
  { emoji: "🤗", label: "Comfort", value: "comfort" },
  { emoji: "🥗", label: "Light", value: "light" },
  { emoji: "💪", label: "Healthy", value: "healthy" },
  { emoji: "🍔", label: "Indulgent", value: "indulgent" },
  { emoji: "🔥", label: "Spicy", value: "spicy" },
  { emoji: "🧭", label: "Adventurous", value: "adventurous" },
  { emoji: "⚡", label: "Quick bite", value: "quick" },
  { emoji: "🍲", label: "Hearty", value: "hearty" },
  { emoji: "🌿", label: "Fresh", value: "fresh" },
  { emoji: "🛋️", label: "Cozy", value: "cozy" },
  { emoji: "🍰", label: "Sweet tooth", value: "sweet" },
  { emoji: "🎉", label: "Celebrating", value: "celebrating" },
];

/**
 * How many people are eating. Drives two things: `Session.companions` for the
 * recommender, and the **cart quantity** at checkout — so a table of four adds
 * four portions instead of one.
 */
export const PARTY_SIZES = [
  { icon: "🧍", label: "Just me", people: 1, companions: "solo" },
  { icon: "💑", label: "Two of us", people: 2, companions: "partner" },
  { icon: "👫", label: "Three", people: 3, companions: "friends" },
  { icon: "👨‍👩‍👧", label: "Four", people: 4, companions: "family" },
  { icon: "🎊", label: "Five+", people: 5, companions: "friends" },
];

export const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export const BUDGET = { min: 50, max: 3000, step: 25, presets: [200, 500, 1000, 2000] };

/**
 * Home state — powers regional comfort-food picks ("someone from Punjab may crave
 * a home dish"). Union Territories included; kept as plain strings so the value we
 * store and send to the backend is human-readable.
 */
export const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Delhi",
  "Jammu & Kashmir",
  "Ladakh",
  "Puducherry",
  "Chandigarh",
  "Andaman & Nicobar Islands",
  "Dadra & Nagar Haveli and Daman & Diu",
  "Lakshadweep",
];

/** Splits "🍛 Indian" into ["🍛", "Indian"]. */
export function splitEmojiLabel(value: string): [string, string] {
  const [emoji, ...rest] = value.split(" ");
  return [emoji, rest.join(" ")];
}
