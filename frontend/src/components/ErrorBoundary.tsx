import { Component, type ReactNode } from "react";
import { DISPLAY_FONT, ORANGE_GRAD } from "@/lib/theme";

type Props = { children: ReactNode };
type State = { error: Error | null };

/**
 * Last line of defence for render-time crashes.
 *
 * React unmounts the whole tree when a render throws, so without this the user
 * gets a blank black screen and no way forward. A caught error is logged once
 * (dev only — production consoles are the user's, not ours) and the user is
 * offered the one action that reliably works: reload.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    if (import.meta.env.DEV) {
      console.error("[kya] render crashed:", error);
    }
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-center px-8 bg-[#0D0A14]">
        <div className="text-5xl mb-4">🍳</div>
        <h1 className="text-white font-black text-2xl mb-2" style={DISPLAY_FONT}>
          Something burned
        </h1>
        <p className="text-white/35 text-sm mb-6">
          The app hit an unexpected error. A reload usually sorts it.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-3 rounded-2xl text-white font-bold active:scale-95 transition-all"
          style={{ background: ORANGE_GRAD }}
        >
          Reload
        </button>
        {import.meta.env.DEV && (
          <pre className="mt-6 max-w-full overflow-auto text-left text-[10px] text-white/30">
            {error.message}
          </pre>
        )}
      </div>
    );
  }
}
