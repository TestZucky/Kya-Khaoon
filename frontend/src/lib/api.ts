/**
 * Backend client. The one place that knows the API's wire shape; everything
 * above this file speaks the camelCase types declared here.
 *
 * Error contract: every function either resolves with data or rejects with an
 * `ApiError` whose `message` is safe to render. Network failures, non-JSON
 * bodies and unexpected statuses are all normalised here so no screen has to
 * guess what `catch (e)` holds.
 */

const BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  /** The backend's `request_id`, when it sent one — quotable in a bug report. */
  readonly requestId?: string;

  constructor(message: string, status = 0, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

export type ProfilePayload = {
  diet: string;
  allergies: string[];
  avoided_ingredients: string[];
  restrictions: string[];
  goal: string;
  budget_band: string;
  cuisines: string[];
  adventure_level: string;
  spice_level: number; // 0 (mild) .. 4 (devil mode)
  // Optional — null when the user skipped these onboarding steps.
  height_cm: number | null;
  weight_kg: number | null;
  home_state: string | null;
};

/** A resolved deck card — the backend's CardOut, camelCased. */
export type Pick = {
  cardId: number;
  name: string;
  restaurant: string;
  price: number;
  etaMinutes: number | null;
  rating: number | null;
  imageUrl: string | null;
  cuisine: string;
  isVeg: boolean;
  isAd: boolean;
  offer: string | null;
  reason: string;
  allergens: string[];
};

export type DeckContext = {
  mood?: string;
  hunger?: string;
  meal?: string;
  companions?: string;
  budgetOverride?: number;
};

export type Address = { id: string; label: string; line: string };

// The session token from sign-in, sent as Bearer on protected calls.
let authToken: string | null = null;
export function setAuthToken(token: string | null) {
  authToken = token;
}

/**
 * Called when a protected request comes back 401 (expired session). With a
 * device id on hand we can mint a fresh token and retry instead of bouncing the
 * user to a login screen — AppState wires this up at startup.
 */
let reauthorize: (() => Promise<string | null>) | null = null;
export function setReauthorize(fn: (() => Promise<string | null>) | null) {
  reauthorize = fn;
}

type CallOptions = {
  method?: "GET" | "POST" | "PUT";
  body?: unknown;
  auth?: boolean;
};

async function call<T>(
  path: string,
  { method = "GET", body, auth = false }: CallOptions = {},
  retryOn401 = true,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    if (!authToken) throw new ApiError("You're signed out. Please log in again.", 401);
    headers.Authorization = `Bearer ${authToken}`;
  }

  let resp: Response;
  try {
    resp = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // fetch only rejects on a transport failure — DNS, CORS, offline, refused.
    throw new ApiError("Can't reach the server. Is the backend running?");
  }

  // Session expired (30-day TTL) or the DB was wiped under us — re-mint from the
  // device id and replay once. Only once, so a persistent 401 can't loop.
  if (resp.status === 401 && auth && retryOn401 && reauthorize) {
    const fresh = await reauthorize();
    if (fresh) return call<T>(path, { method, body, auth }, false);
  }

  if (!resp.ok) {
    const detail = (await resp.json().catch(() => null)) as
      | { detail?: string; request_id?: string }
      | null;
    throw new ApiError(
      detail?.detail ?? `Request failed (${resp.status})`,
      resp.status,
      detail?.request_id,
    );
  }

  // 204 No Content (e.g. /address) has no body to parse.
  if (resp.status === 204 || resp.headers.get("content-length") === "0") {
    return undefined as T;
  }
  try {
    return (await resp.json()) as T;
  } catch {
    throw new ApiError("The server sent a response we couldn't read.", resp.status);
  }
}

const post = <T>(path: string, body: unknown, auth = false) =>
  call<T>(path, { method: "POST", body, auth });

/** The user's saved Swiggy delivery addresses. */
export async function getAddresses(): Promise<Address[]> {
  return call<Address[]>("/addresses", { auth: true });
}

/** Set the delivery address used for search and cart. */
export async function chooseAddress(addressId: string): Promise<void> {
  await post("/address", { address_id: addressId }, true);
}

/** Sends an OTP. In dev (console SMS provider) the code comes back as devCode. */
export async function requestOtp(phone: string): Promise<{ devCode: string | null }> {
  const data = await post<{ ok: boolean; dev_code: string | null }>(
    "/auth/request-otp",
    { phone },
  );
  return { devCode: data.dev_code };
}

export type AuthResult = {
  token: string;
  userId: number;
  phone: string;
  onboarded: boolean;
};

type AuthResponse = {
  token: string;
  user_id: number;
  phone: string | null;
  onboarded: boolean;
};

const toAuthResult = (data: AuthResponse): AuthResult => ({
  token: data.token,
  userId: data.user_id,
  phone: data.phone ?? "",
  onboarded: data.onboarded,
});

/** Verifies the OTP and returns a session token. */
export async function verifyOtp(phone: string, code: string): Promise<AuthResult> {
  return toAuthResult(
    await post<AuthResponse>("/auth/verify-otp", { phone, code }),
  );
}

/** Trades this browser's device id for a session (creates the user on first use). */
export async function deviceLogin(deviceId: string): Promise<AuthResult> {
  return toAuthResult(
    await post<AuthResponse>("/auth/device", { device_id: deviceId }),
  );
}

/** Verifies a Google ID token and returns a session (creates the user on first use). */
export async function googleLogin(idToken: string): Promise<AuthResult> {
  return toAuthResult(
    await post<AuthResponse>("/auth/google", { id_token: idToken }),
  );
}

export async function onboard(profile: ProfilePayload): Promise<{ id: number }> {
  // Delivery address is chosen separately via chooseAddress().
  return post("/onboard", { profile }, true);
}

type DeckResponse = {
  deck_id: number;
  cards: Array<{
    card_id: number;
    name: string;
    restaurant: string;
    price: number;
    eta_minutes: number | null;
    rating: number | null;
    image_url: string | null;
    cuisine: string;
    is_veg: boolean;
    is_ad: boolean;
    offer: string | null;
    reason: string;
    allergens: string[];
  }>;
};

export async function fetchDeck(ctx: DeckContext = {}): Promise<Pick[]> {
  const data = await post<DeckResponse>(
    "/decks",
    {
      mood: ctx.mood ?? null,
      hunger: ctx.hunger ?? null,
      // Meal period from the client's clock. The backend stores it on the
      // Session, scores concepts against it, and tells the LLM what time of day
      // it is — dropping it silently disables all three.
      meal: ctx.meal ?? null,
      companions: ctx.companions ?? null,
      budget_override: ctx.budgetOverride ?? null,
    },
    true,
  );
  return data.cards.map((c) => ({
    cardId: c.card_id,
    name: c.name,
    restaurant: c.restaurant,
    price: c.price,
    etaMinutes: c.eta_minutes,
    rating: c.rating,
    imageUrl: c.image_url,
    cuisine: c.cuisine,
    isVeg: c.is_veg,
    isAd: c.is_ad,
    offer: c.offer,
    reason: c.reason,
    allergens: c.allergens,
  }));
}

export async function recordSwipe(
  cardId: number,
  direction: "right" | "left",
  rejectionReason?: string,
): Promise<void> {
  await post(
    "/swipes",
    { card_id: cardId, direction, rejection_reason: rejectionReason ?? null },
    true,
  );
}

/** Swiggy's real bill for the cart. All fields null when Swiggy didn't tell us. */
export type CartBill = {
  total: number | null;
  itemTotal: number | null;
  taxes: number | null;
  deliveryFee: number | null;
  packingFee: number | null;
  platformFee: number | null;
  discount: number | null;
};

export type CartResult = {
  restaurant: string;
  item: string;
  /** The dish's menu price — pre-tax, pre-fees. See `bill.total` for the payable. */
  price: number;
  /** Portions added — the party size, echoed back by the server. */
  quantity: number;
  checkoutUrl: string;
  bill: CartBill;
};

/**
 * Adds the matched dish to the user's Swiggy cart. Does NOT place the order.
 * `quantity` is the party size from the "right now" screen — one portion each.
 */
export async function addToCart(cardId: number, quantity = 1): Promise<CartResult> {
  const data = await post<{
    restaurant: string;
    item: string;
    price: number;
    quantity: number;
    checkout_url: string;
    total: number | null;
    item_total: number | null;
    taxes: number | null;
    delivery_fee: number | null;
    packing_fee: number | null;
    platform_fee: number | null;
    discount: number | null;
  }>("/cart", { card_id: cardId, quantity }, true);
  return {
    restaurant: data.restaurant,
    item: data.item,
    price: data.price,
    quantity: data.quantity,
    checkoutUrl: data.checkout_url,
    bill: {
      total: data.total,
      itemTotal: data.item_total,
      taxes: data.taxes,
      deliveryFee: data.delivery_fee,
      packingFee: data.packing_fee,
      platformFee: data.platform_fee,
      discount: data.discount,
    },
  };
}

/**
 * Whether the user has connected their real Swiggy account. Any failure reads as
 * "not connected" — the screen's job is to offer the connect button, and it can
 * do that safely whether the answer is no or unknown.
 */
export async function swiggyStatus(): Promise<boolean> {
  try {
    const data = await call<{ connected: boolean }>("/auth/swiggy/status", {
      auth: true,
    });
    return !!data.connected;
  } catch {
    return false;
  }
}

/** Kick off the Swiggy OAuth connect; returns the URL to send the browser to. */
export async function startSwiggyConnect(): Promise<string> {
  const data = await post<{ authorize_url: string }>("/auth/swiggy/start", {}, true);
  return data.authorize_url;
}

export const formatPrice = (rupees: number) => `₹${rupees}`;
