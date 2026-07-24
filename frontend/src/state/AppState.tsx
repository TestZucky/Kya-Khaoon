import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  addToCart as apiAddToCart,
  chooseAddress as apiChooseAddress,
  deviceLogin as apiDeviceLogin,
  fetchDeck as apiFetchDeck,
  getAddresses as apiGetAddresses,
  googleLogin as apiGoogleLogin,
  onboard as apiOnboard,
  recordSwipe,
  requestOtp as apiRequestOtp,
  verifyOtp as apiVerifyOtp,
  setAuthToken,
  setReauthorize,
  type Address,
  type CartResult,
  type Pick,
} from "@/lib/api";
import { getDeviceId } from "@/lib/device";
import { companionsForParty, mealNow, toProfilePayload } from "@/lib/mapPrefs";
import { loadJSON, saveJSON } from "@/lib/storage";

export type Preferences = {
  phone: string;
  budget: number;
  cuisines: string[];
  diet: string[];
  /** Emoji-labelled allergens; a hard exclusion in the recommender. */
  allergies: string[];
  spiceLevel: number;
  goal: number | null;
  /**
   * How many people are eating, asked on every open. Persisted so the picker
   * defaults to whatever you chose last time. Drives both the recommender's
   * `companions` hint and the cart quantity at checkout.
   */
  partySize: number;
  /** Optional body metrics — drive BMI-aware picks; null when the user skipped. */
  heightCm: number | null;
  weightKg: number | null;
  /** Home state/region — drives regional comfort-food picks; null when skipped. */
  homeState: string | null;
  /** Set from the server on login and after onboarding; gates the deck routes. */
  onboarded: boolean;
};

const DEFAULT_PREFS: Preferences = {
  phone: "",
  budget: 300,
  cuisines: [],
  diet: [],
  allergies: [],
  spiceLevel: 2,
  goal: null,
  partySize: 1,
  heightCm: null,
  weightKg: null,
  homeState: null,
  onboarded: false,
};

type Session = { token: string | null };

const PREFS_KEY = "kya-khaoon:prefs";
const SESSION_KEY = "kya-khaoon:session";

const initialSession = loadJSON<Session>(SESSION_KEY, { token: null });
// Prime the API module with any persisted token before the first render.
setAuthToken(initialSession.token);

export type DeckStatus = "idle" | "loading" | "ready" | "error";

type AppState = {
  prefs: Preferences;
  setPref: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
  togglePref: (
    key: "cuisines" | "diet" | "allergies",
    value: string,
  ) => void;

  /** True once a session token exists. */
  authed: boolean;
  /**
   * False until the startup device sign-in has settled. Routes must wait for
   * this before treating `authed: false` as "signed out", or a refresh flashes
   * the login screen while the session is still being minted.
   */
  authReady: boolean;
  /**
   * Why the silent device sign-in failed, if it did. Almost always "backend is
   * down" — without surfacing it the user lands on a login screen with no
   * explanation for why nothing works.
   */
  authError: string | null;
  /** Re-run the device sign-in after a failure. */
  retrySignIn: () => Promise<void>;
  /** Sends an OTP; returns the dev code in console mode so the UI can show it. */
  requestOtp: (
    phone: string,
  ) => Promise<{ ok: true; devCode: string | null } | { ok: false; error: string }>;
  /** Verifies the OTP, stores the session, returns whether the user is onboarded. */
  verifyOtp: (
    code: string,
  ) => Promise<{ ok: true; onboarded: boolean } | { ok: false; error: string }>;
  /** Signs in with a Google ID token, stores the session. */
  loginWithGoogle: (
    idToken: string,
  ) => Promise<{ ok: true; onboarded: boolean } | { ok: false; error: string }>;

  /**
   * The current meal's context, from the "right now" screen. Mood is transient
   * (a fresh open should ask again); party size is persisted into prefs.
   */
  mood: string | null;
  setMealContext: (ctx: { mood: string | null; partySize: number }) => void;

  /** Fetch the user's saved Swiggy delivery addresses. */
  loadAddresses: () => Promise<Address[]>;
  /** Set the delivery address for search + cart. */
  chooseAddress: (addressId: string) => Promise<boolean>;

  /** Sends the profile to the backend. Returns true on success. */
  submitOnboarding: () => Promise<boolean>;
  onboardError: string | null;

  deck: Pick[];
  deckSize: number;
  deckStatus: DeckStatus;
  deckError: string | null;
  fetchDeck: () => Promise<void>;
  skipTop: () => void;
  likeTop: () => Pick | undefined;

  matched: Pick | null;
  clearMatch: () => void;
  orderMatched: () => Promise<
    { ok: true; cart: CartResult } | { ok: false; error: string }
  >;
};

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Preferences>(() =>
    loadJSON(PREFS_KEY, DEFAULT_PREFS),
  );
  const [token, setToken] = useState<string | null>(initialSession.token);
  // Always false at boot: a persisted token proves nothing on its own (the row
  // it points at may be gone after a `make wipe`), so the router waits for the
  // server to confirm before trusting `authed` or `prefs.onboarded`.
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [onboardError, setOnboardError] = useState<string | null>(null);
  // Dedupe concurrent sign-ins — StrictMode fires mount effects twice in dev.
  const signingIn = useRef(false);

  const [deck, setDeck] = useState<Pick[]>([]);
  const [deckSize, setDeckSize] = useState(0);
  const [deckStatus, setDeckStatus] = useState<DeckStatus>("idle");
  const [deckError, setDeckError] = useState<string | null>(null);
  const [matched, setMatched] = useState<Pick | null>(null);
  // Deliberately not persisted — "what are you feeling?" should be asked fresh
  // on every open rather than assumed from last night.
  const [mood, setMood] = useState<string | null>(null);
  // Dedupe concurrent fetches — StrictMode fires mount effects twice in dev.
  const fetchingDeck = useRef(false);

  useEffect(() => saveJSON(PREFS_KEY, prefs), [prefs]);
  useEffect(() => {
    saveJSON(SESSION_KEY, { token });
    setAuthToken(token);
  }, [token]);

  /**
   * Sign in with this browser's device id, returning the fresh token. Used both
   * at startup and as the 401 recovery hook, so an expired session (or a wiped
   * dev DB) heals itself instead of stranding the user on a dead screen.
   */
  const signInWithDevice = useCallback(async (): Promise<string | null> => {
    if (signingIn.current) return null;
    signingIn.current = true;
    setAuthError(null);
    try {
      const auth = await apiDeviceLogin(getDeviceId());
      // Set the module token synchronously — an in-flight 401 retry replays
      // before the [token] effect below would get a chance to run.
      setAuthToken(auth.token);
      setToken(auth.token);
      // The server owns the profile. If it has none, there are no saved answers
      // — so clear the local copy too, or a "new" user on this device starts
      // onboarding with someone else's diet and allergies already ticked.
      setPrefs((p) =>
        auth.onboarded
          ? { ...p, onboarded: true }
          : { ...DEFAULT_PREFS, partySize: p.partySize },
      );
      return auth.token;
    } catch (e) {
      setAuthError(
        e instanceof Error ? e.message : "Couldn't start a session. Try again.",
      );
      return null;
    } finally {
      signingIn.current = false;
      setAuthReady(true);
    }
  }, []);

  const retrySignIn = useCallback(async () => {
    await signInWithDevice();
  }, [signInWithDevice]);

  // Reconcile with the server on every load, not just when a token is missing.
  // `/auth/device` is an idempotent get-or-create, so this costs one fast call
  // and makes a wiped DB behave exactly like a first-ever visit.
  useEffect(() => {
    void signInWithDevice();
  }, [signInWithDevice]);

  // Let the API client recover from an expired session on its own.
  useEffect(() => {
    setReauthorize(signInWithDevice);
    return () => setReauthorize(null);
  }, [signInWithDevice]);

  const setPref = useCallback<AppState["setPref"]>((key, value) => {
    setPrefs((p) => ({ ...p, [key]: value }));
  }, []);

  const togglePref = useCallback<AppState["togglePref"]>((key, value) => {
    setPrefs((p) => {
      const list = p[key];
      return {
        ...p,
        [key]: list.includes(value)
          ? list.filter((v) => v !== value)
          : [...list, value],
      };
    });
  }, []);

  const requestOtp = useCallback<AppState["requestOtp"]>(async (phone) => {
    try {
      const { devCode } = await apiRequestOtp(phone);
      setPrefs((p) => ({ ...p, phone }));
      return { ok: true, devCode };
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : "Couldn't send code" };
    }
  }, []);

  const verifyOtp = useCallback<AppState["verifyOtp"]>(
    async (code) => {
      try {
        const auth = await apiVerifyOtp(prefs.phone, code);
        setToken(auth.token);
        setPrefs((p) => ({ ...p, phone: auth.phone, onboarded: auth.onboarded }));
        return { ok: true, onboarded: auth.onboarded };
      } catch (e) {
        return { ok: false, error: e instanceof Error ? e.message : "Couldn't verify" };
      }
    },
    [prefs.phone],
  );

  const setMealContext = useCallback<AppState["setMealContext"]>((ctx) => {
    setMood(ctx.mood);
    setPrefs((p) => ({ ...p, partySize: ctx.partySize }));
    // A new context means the old deck is stale — force the next fetch.
    setDeck([]);
    setDeckStatus("idle");
    setMatched(null);
  }, []);

  const loadAddresses = useCallback(() => apiGetAddresses(), []);

  const chooseAddress = useCallback(async (addressId: string) => {
    try {
      await apiChooseAddress(addressId);
      return true;
    } catch {
      return false;
    }
  }, []);

  const loginWithGoogle = useCallback<AppState["loginWithGoogle"]>(async (idToken) => {
    try {
      const auth = await apiGoogleLogin(idToken);
      setToken(auth.token);
      setPrefs((p) => ({ ...p, phone: auth.phone, onboarded: auth.onboarded }));
      return { ok: true, onboarded: auth.onboarded };
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : "Google sign-in failed" };
    }
  }, []);

  const submitOnboarding = useCallback(async () => {
    setOnboardError(null);
    try {
      await apiOnboard(toProfilePayload(prefs));
      setPrefs((p) => ({ ...p, onboarded: true }));
      return true;
    } catch (e) {
      setOnboardError(e instanceof Error ? e.message : "Something went wrong");
      return false;
    }
  }, [prefs]);

  const fetchDeck = useCallback(async () => {
    if (!token) {
      setDeckStatus("error");
      setDeckError("Please log in first.");
      return;
    }
    if (fetchingDeck.current) return;
    fetchingDeck.current = true;
    setDeckStatus("loading");
    setDeckError(null);
    setMatched(null);
    try {
      const cards = await apiFetchDeck({
        meal: mealNow(),
        mood: mood ?? undefined,
        companions: companionsForParty(prefs.partySize),
      });
      setDeck(cards);
      setDeckSize(cards.length);
      setDeckStatus("ready");
    } catch (e) {
      setDeckStatus("error");
      setDeckError(e instanceof Error ? e.message : "Couldn't load your picks");
    } finally {
      fetchingDeck.current = false;
    }
  }, [token, mood, prefs.partySize]);

  const skipTop = useCallback(() => {
    setDeck((d) => {
      const top = d[0];
      if (top) void recordSwipe(top.cardId, "left").catch(() => {});
      return d.slice(1);
    });
  }, []);

  const likeTop = useCallback(() => {
    const top = deck[0];
    if (!top) return undefined;
    void recordSwipe(top.cardId, "right").catch(() => {});
    setDeck((d) => d.slice(1));
    setMatched(top);
    return top;
  }, [deck]);

  const clearMatch = useCallback(() => setMatched(null), []);

  const orderMatched = useCallback<AppState["orderMatched"]>(async () => {
    if (!matched) return { ok: false, error: "Nothing matched." };
    try {
      // One portion per person from the "right now" screen.
      const cart = await apiAddToCart(matched.cardId, prefs.partySize);
      return { ok: true, cart };
    } catch (e) {
      return { ok: false, error: e instanceof Error ? e.message : "Couldn't add to cart" };
    }
  }, [matched, prefs.partySize]);

  const value = useMemo<AppState>(
    () => ({
      prefs,
      setPref,
      togglePref,
      authed: token !== null,
      authReady,
      authError,
      retrySignIn,
      requestOtp,
      verifyOtp,
      loginWithGoogle,
      mood,
      setMealContext,
      loadAddresses,
      chooseAddress,
      submitOnboarding,
      onboardError,
      deck,
      deckSize,
      deckStatus,
      deckError,
      fetchDeck,
      skipTop,
      likeTop,
      matched,
      clearMatch,
      orderMatched,
    }),
    [
      prefs,
      setPref,
      togglePref,
      token,
      authReady,
      authError,
      retrySignIn,
      requestOtp,
      verifyOtp,
      mood,
      setMealContext,
      loadAddresses,
      chooseAddress,
      submitOnboarding,
      onboardError,
      deck,
      deckSize,
      deckStatus,
      deckError,
      fetchDeck,
      skipTop,
      likeTop,
      matched,
      clearMatch,
      orderMatched,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAppState must be used inside <AppStateProvider>");
  return ctx;
}
