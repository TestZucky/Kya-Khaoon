import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Check, ExternalLink, Loader2 } from "lucide-react";
import { Screen } from "@/components/Screen";
import { DISPLAY_FONT, ORANGE_GRAD } from "@/lib/theme";
import { formatPrice, type CartBill } from "@/lib/api";
import { useAppState } from "@/state/AppState";

type CartState =
  | { phase: "idle" }
  | { phase: "adding" }
  | { phase: "added"; checkoutUrl: string; bill: CartBill }
  | { phase: "error"; message: string };

/**
 * Swiggy's real bill. The card price is one dish pre-tax; the payable total adds
 * GST, delivery, packing and platform fees, so we show the breakdown rather than
 * letting the jump surprise people at checkout.
 */
function BillBreakdown({ bill }: { bill: CartBill }) {
  if (bill.total == null) return null;
  const rows: Array<[string, number | null]> = [
    ["Item total", bill.itemTotal],
    ["Taxes & GST", bill.taxes],
    ["Delivery", bill.deliveryFee],
    ["Packing", bill.packingFee],
    ["Platform fee", bill.platformFee],
  ];
  const shown = rows.filter(([, v]) => v != null && v !== 0);

  return (
    <div
      className="rounded-2xl p-4 mb-4"
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      {shown.map(([label, value]) => (
        <div key={label} className="flex justify-between text-sm mb-1.5">
          <span className="text-white/40">{label}</span>
          <span className="text-white/60">{formatPrice(value!)}</span>
        </div>
      ))}
      {bill.discount != null && bill.discount > 0 && (
        <div className="flex justify-between text-sm mb-1.5">
          <span className="text-green-400/70">Discount</span>
          <span className="text-green-400">−{formatPrice(bill.discount)}</span>
        </div>
      )}
      <div
        className="flex justify-between items-baseline pt-2.5 mt-2"
        style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}
      >
        <span className="text-white/70 text-sm font-semibold">To pay on Swiggy</span>
        <span className="text-orange-400 font-black text-xl" style={DISPLAY_FONT}>
          {formatPrice(bill.total)}
        </span>
      </div>
    </div>
  );
}

export default function MatchScreen() {
  const navigate = useNavigate();
  const { matched, clearMatch, orderMatched } = useAppState();
  const [cart, setCart] = useState<CartState>({ phase: "idle" });

  // Landing here directly (refresh, deep link) has nothing to celebrate.
  if (!matched) return <Navigate to="/picks" replace />;

  const keepBrowsing = () => {
    clearMatch();
    navigate("/picks");
  };

  // Adds the dish to the user's Swiggy cart. This is the hand-off — payment and
  // order placement happen in Swiggy, never here.
  const orderOnSwiggy = async () => {
    setCart({ phase: "adding" });
    const result = await orderMatched();
    setCart(
      result.ok
        ? {
            phase: "added",
            checkoutUrl: result.cart.checkoutUrl,
            bill: result.cart.bill,
          }
        : { phase: "error", message: result.error },
    );
  };

  return (
    <Screen gradient className="items-center justify-center px-6 relative overflow-hidden">
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% 60%, rgba(255,101,52,0.18), transparent)",
        }}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.75, y: 40 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ type: "spring", stiffness: 240, damping: 22 }}
        className="w-full max-w-sm z-10"
      >
        <div className="text-center mb-6">
          <div className="text-6xl mb-3">{cart.phase === "added" ? "🛒" : "🎉"}</div>
          <h1 className="text-4xl font-black text-white mb-1" style={DISPLAY_FONT}>
            {cart.phase === "added" ? "In your cart!" : "It's a Match!"}
          </h1>
          <p className="text-white/40">
            {cart.phase === "added"
              ? "Open Swiggy to pay & place the order"
              : "Your food twin found you"}
          </p>
        </div>

        <div
          className="rounded-3xl overflow-hidden mb-5 shadow-2xl"
          style={{ border: "2px solid rgba(255,101,52,0.35)" }}
        >
          {matched.imageUrl ? (
            <img
              src={matched.imageUrl}
              alt={matched.name}
              className="w-full h-52 object-cover bg-orange-900"
            />
          ) : (
            <div
              className="w-full h-52 flex items-center justify-center text-6xl"
              style={{ background: "linear-gradient(135deg, #3a1e12, #2a1420)" }}
            >
              🍽️
            </div>
          )}
          <div className="p-5" style={{ background: "rgba(255,255,255,0.05)" }}>
            <h3 className="text-white font-black text-xl mb-1" style={DISPLAY_FONT}>
              {matched.name}
            </h3>
            <p className="text-white/45 text-sm mb-3">{matched.restaurant}</p>
            <div className="flex items-center gap-3 text-sm">
              <span className="text-orange-400 font-bold text-lg">
                {formatPrice(matched.price)}
              </span>
              {/* Set expectations up front — Swiggy adds tax + fees at checkout. */}
              <span className="text-white/30 text-xs">+ taxes &amp; fees</span>
              {matched.etaMinutes != null && (
                <>
                  <span className="text-white/20">·</span>
                  <span className="text-white/45">{matched.etaMinutes} min</span>
                </>
              )}
              {matched.rating != null && (
                <>
                  <span className="text-white/20">·</span>
                  <span className="text-yellow-400">⭐ {matched.rating}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {cart.phase === "added" ? (
          <>
            <BillBreakdown bill={cart.bill} />
            <a
              href={cart.checkoutUrl}
              target="_blank"
              rel="noreferrer"
              className="w-full py-4 rounded-2xl text-white font-black text-lg flex items-center justify-center gap-2 active:scale-95 transition-all mb-3 shadow-xl"
              style={{ background: ORANGE_GRAD }}
            >
              Open Swiggy to checkout <ExternalLink size={18} />
            </a>
            <div className="flex items-center justify-center gap-2 mb-3 text-green-400 text-sm font-semibold">
              <Check size={16} /> Added {matched.name} to your Swiggy cart
            </div>
          </>
        ) : (
          <button
            onClick={() => void orderOnSwiggy()}
            disabled={cart.phase === "adding"}
            className="w-full py-4 rounded-2xl text-white font-black text-lg flex items-center justify-center gap-2 active:scale-95 transition-all mb-3 shadow-xl disabled:opacity-70"
            style={{ background: ORANGE_GRAD }}
          >
            {cart.phase === "adding" ? (
              <>
                <Loader2 size={18} className="animate-spin" /> Adding to cart…
              </>
            ) : (
              <>🛵 Order on Swiggy — {formatPrice(matched.price)}</>
            )}
          </button>
        )}

        {cart.phase === "error" && (
          <p className="text-center text-sm mb-3" style={{ color: "#FF4B6E" }}>
            {cart.message}
          </p>
        )}

        <button
          onClick={keepBrowsing}
          className="w-full py-4 rounded-2xl font-semibold text-sm active:scale-95 transition-all"
          style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.50)" }}
        >
          {cart.phase === "added" ? "Back to picks" : "Not this one, show the rest"}
        </button>
      </motion.div>
    </Screen>
  );
}
