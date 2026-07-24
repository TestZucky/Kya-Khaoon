import { useEffect, useRef, useState } from "react";

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
const GIS_SRC = "https://accounts.google.com/gsi/client";

// Minimal shape of the Google Identity Services global we use.
type Gis = {
  accounts: {
    id: {
      initialize: (config: {
        client_id: string;
        callback: (r: { credential: string }) => void;
      }) => void;
      renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void;
    };
  };
};

declare global {
  interface Window {
    google?: Gis;
  }
}

/**
 * Load Google's script once. Both the load and the error path have to be wired
 * on an already-present tag too, or a second mount hangs forever on a script
 * that already failed.
 */
function loadGis(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve();

    const fail = () => reject(new Error("Google's sign-in script failed to load"));
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${GIS_SRC}"]`,
    );
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", fail);
      return;
    }

    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = fail;
    document.head.appendChild(script);
  });
}

/**
 * "Continue with Google". Renders nothing if VITE_GOOGLE_CLIENT_ID isn't set,
 * so the app works fine before Google is configured.
 */
export function GoogleSignInButton({
  onCredential,
}: {
  onCredential: (idToken: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!CLIENT_ID) return;
    let cancelled = false;

    loadGis()
      .then(() => {
        if (cancelled || !ref.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (r) => onCredential(r.credential),
        });
        window.google.accounts.id.renderButton(ref.current, {
          theme: "filled_black",
          size: "large",
          shape: "pill",
          text: "continue_with",
          width: 300,
        });
      })
      .catch(() => {
        // Offline, blocked by an extension, or a misconfigured client id. A
        // silent no-op here leaves an empty gap where the only button should be.
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [onCredential]);

  if (!CLIENT_ID) return null;
  if (failed) {
    return (
      <p className="text-center text-xs text-white/35 min-h-[44px]">
        Google sign-in is unavailable right now.
      </p>
    );
  }
  return <div ref={ref} className="flex justify-center min-h-[44px]" />;
}
