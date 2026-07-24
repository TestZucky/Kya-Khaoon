import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppStateProvider, useAppState } from "@/state/AppState";
import SplashScreen from "@/screens/SplashScreen";
import LoginScreen from "@/screens/LoginScreen";
import OtpScreen from "@/screens/OtpScreen";
import ConnectSwiggyScreen from "@/screens/ConnectSwiggyScreen";
import AddressScreen from "@/screens/AddressScreen";
import OnboardingScreen from "@/screens/OnboardingScreen";
import RightNowScreen from "@/screens/RightNowScreen";
import PicksScreen from "@/screens/PicksScreen";
import MatchScreen from "@/screens/MatchScreen";
import ProfileScreen from "@/screens/ProfileScreen";

/**
 * Protected routes need a session token AND a completed profile.
 *
 * The device sign-in is async, so `authed` is briefly false on a cold load even
 * for a returning user — hold the splash until `authReady` rather than bouncing
 * them to /login and back.
 */
function RequireAuth({ children }: { children: ReactNode }) {
  const { authed, authReady, prefs } = useAppState();
  // Sub-second in practice; an empty frame beats a flash of the wrong screen.
  if (!authReady) return null;
  if (!authed) return <Navigate to="/login" replace />;
  if (!prefs.onboarded) return <Navigate to="/onboarding" replace />;
  return <>{children}</>;
}

/**
 * Signed-in, onboarded users skip the splash. They land on "right now" rather
 * than straight on the deck: mood and party size change meal to meal, so we ask
 * those two before building anything.
 */
function EntryRedirect() {
  const { authed, authReady, prefs } = useAppState();
  if (!authReady) return null;
  return authed && prefs.onboarded ? (
    <Navigate to="/right-now" replace />
  ) : (
    <SplashScreen />
  );
}

/**
 * Kya Khaoon is a phone-first product. On anything wider we letterbox it into a
 * device-sized column instead of stretching the layout across a desktop monitor.
 */
function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="w-full h-[100dvh] flex justify-center bg-black">
      <div
        className="relative w-full max-w-[440px] h-full overflow-hidden"
        style={{ boxShadow: "0 0 80px rgba(255,101,52,0.10)" }}
      >
        {children}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppStateProvider>
      <PhoneFrame>
        <Routes>
          {/* Sign-up flow */}
          <Route path="/" element={<EntryRedirect />} />
          <Route path="/login" element={<LoginScreen />} />
          <Route path="/otp" element={<OtpScreen />} />
          <Route path="/connect" element={<ConnectSwiggyScreen />} />
          <Route path="/address" element={<AddressScreen />} />
          <Route path="/onboarding" element={<OnboardingScreen />} />

          {/* The app itself: a deck of five, and the taste profile behind it. */}
          <Route
            path="/right-now"
            element={
              <RequireAuth>
                <RightNowScreen />
              </RequireAuth>
            }
          />
          <Route
            path="/picks"
            element={
              <RequireAuth>
                <PicksScreen />
              </RequireAuth>
            }
          />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <ProfileScreen />
              </RequireAuth>
            }
          />
          <Route path="/match" element={<MatchScreen />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </PhoneFrame>
    </AppStateProvider>
  );
}
