/**
 * The device id: a UUID minted once per browser and kept in localStorage. It is
 * the only thing that ties this browser back to its user row on the backend.
 *
 * Scope note: this remembers a *browser*, not a person. A new device, a cleared
 * site-data, or iOS Safari's 7-day storage eviction all read as a brand-new
 * user with a blank profile. That's the accepted trade-off for zero-friction
 * onboarding — a phone/OTP upgrade later attaches to the same user row.
 */

const DEVICE_KEY = "kya-khaoon:device";

function mint(): string {
  // randomUUID needs a secure context (https or localhost); fall back for the
  // plain-http LAN case so the app still works instead of throwing.
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  const rand = () => Math.random().toString(36).slice(2);
  return `dev-${rand()}${rand()}${rand()}`;
}

/** The stable id for this browser, creating and persisting one on first call. */
export function getDeviceId(): string {
  try {
    const existing = window.localStorage.getItem(DEVICE_KEY);
    if (existing) return existing;
    const fresh = mint();
    window.localStorage.setItem(DEVICE_KEY, fresh);
    return fresh;
  } catch {
    // Private mode / storage disabled: still return an id so the session works,
    // but it dies with the tab — the user is a stranger again on reload.
    return mint();
  }
}
