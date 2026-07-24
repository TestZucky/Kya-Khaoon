import { useState } from "react";
import { AlertTriangle, Zap } from "lucide-react";
import { DISPLAY_FONT } from "@/lib/theme";
import { formatPrice, type Pick } from "@/lib/api";

type Stamp = { like: number; skip: number };

/** Full-bleed food card — image fills it, everything else is overlaid. */
export function SwipeCard({
  pick,
  portions,
  delta,
  rotation,
  dragging,
  stamps,
  handlers,
}: {
  pick: Pick;
  /** Party size — swiping right adds this many portions, so price for that many. */
  portions: number;
  delta: { x: number; y: number };
  rotation: number;
  dragging: boolean;
  stamps: Stamp;
  handlers: Record<string, unknown>;
}) {
  const tags = [pick.cuisine, pick.isVeg ? "Veg" : "Non-Veg"];

  return (
    <div className="absolute inset-0 touch-none" style={{ zIndex: 2 }} {...handlers}>
      <div
        className="w-full h-full"
        style={{
          transform: `translateX(${delta.x}px) translateY(${delta.y * 0.2}px) rotate(${rotation}deg)`,
          transition: dragging ? "none" : "transform 0.35s cubic-bezier(0.16,1,0.3,1)",
          cursor: dragging ? "grabbing" : "grab",
          userSelect: "none",
        }}
      >
        <Stamp
          className="top-8 left-6 -rotate-12 border-green-400 text-green-400 text-xl"
          opacity={stamps.like}
          label="ORDER 🛵"
        />
        <Stamp
          className="top-8 right-6 rotate-12 border-red-400 text-red-400 text-xl"
          opacity={stamps.skip}
          label="NOPE 👎"
        />

        <div
          className="relative w-full h-full rounded-[28px] overflow-hidden shadow-2xl"
          style={{ border: "1px solid rgba(255,255,255,0.10)" }}
        >
          <CardImage src={pick.imageUrl} alt={pick.name} />

          {/* Bottom scrim so the text always reads over any photo. */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background:
                "linear-gradient(to bottom, transparent 30%, rgba(10,7,15,0.55) 62%, rgba(10,7,15,0.96) 100%)",
            }}
          />

          {pick.offer && (
            <span
              className="absolute top-5 left-5 px-3 py-1.5 rounded-xl text-xs font-black text-white shadow-lg"
              style={{ background: "rgba(255,101,52,0.95)" }}
            >
              {pick.offer}
            </span>
          )}

          <div className="absolute bottom-0 left-0 right-0 p-6 pt-20">
            <div className="flex flex-wrap items-center gap-1.5 mb-2.5">
              {tags.map((t) => (
                <span
                  key={t}
                  className="px-2.5 py-0.5 rounded-full text-[11px] font-bold text-white"
                  style={{
                    background: "rgba(255,101,52,0.4)",
                    backdropFilter: "blur(8px)",
                  }}
                >
                  {t}
                </span>
              ))}
              {pick.allergens.length > 0 && (
                <span className="flex items-center gap-1 text-white/50 text-[11px] ml-0.5">
                  <AlertTriangle size={11} className="text-yellow-500/80" />
                  contains {pick.allergens.join(", ")}
                </span>
              )}
            </div>

            <div className="flex items-end justify-between gap-3 mb-1">
              <h3
                className="text-white font-black text-3xl leading-[1.05]"
                style={DISPLAY_FONT}
              >
                {pick.name}
              </h3>
              {/* What this card actually costs *you*: one portion per person, so
                  a table of four sees the four-portion price, not a per-plate one
                  they'd have to multiply in their head. */}
              <div className="flex flex-col items-end flex-shrink-0">
                <span className="text-orange-400 font-black text-2xl" style={DISPLAY_FONT}>
                  {formatPrice(pick.price * portions)}
                </span>
                {portions > 1 && (
                  <span className="text-white/45 text-[11px] font-semibold whitespace-nowrap">
                    {formatPrice(pick.price)} each × {portions}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2.5 text-sm mb-3.5">
              <span className="text-white/60">{pick.restaurant}</span>
              {pick.rating != null && (
                <>
                  <span className="text-white/25">·</span>
                  <span className="text-yellow-400">⭐ {pick.rating}</span>
                </>
              )}
              {pick.etaMinutes != null && (
                <>
                  <span className="text-white/25">·</span>
                  <span className="text-white/60">{pick.etaMinutes} min</span>
                </>
              )}
            </div>

            <div
              className="rounded-2xl p-3.5 flex items-start gap-2.5"
              style={{
                background: "rgba(255,255,255,0.09)",
                border: "1px solid rgba(255,255,255,0.12)",
                backdropFilter: "blur(12px)",
              }}
            >
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                style={{ background: "rgba(255,101,52,0.28)" }}
              >
                <Zap size={13} className="text-orange-300" />
              </div>
              <div>
                <p className="text-white/45 text-[10px] font-black uppercase tracking-widest mb-0.5">
                  Why you should eat this
                </p>
                <p className="text-white/90 text-sm leading-snug">{pick.reason}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Real Swiggy images load; the fake backend's don't — so fall back gracefully. */
function CardImage({ src, alt }: { src: string | null; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (!src || failed) {
    return (
      <div
        className="w-full h-full flex items-center justify-center text-7xl"
        style={{ background: "linear-gradient(150deg, #3a1e12, #241019 70%, #14161f)" }}
      >
        🍽️
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
      className="w-full h-full object-cover bg-orange-900"
      draggable={false}
    />
  );
}

/** The rotated ORDER / NOPE badge that fades in with drag distance. */
function Stamp({
  label,
  opacity,
  className,
}: {
  label: string;
  opacity: number;
  className: string;
}) {
  return (
    <div
      className={`absolute z-20 px-3.5 py-1.5 rounded-xl font-black border-[3px] pointer-events-none ${className}`}
      style={{ opacity }}
    >
      {label}
    </div>
  );
}

/** A slightly-smaller card peeking behind the active one, so the deck reads as a stack. */
export function DeckShadowCard() {
  return (
    <div
      aria-hidden
      className="absolute rounded-[28px]"
      style={{
        inset: 0,
        transform: "scale(0.955) translateY(10px)",
        zIndex: 1,
        background: "rgba(255,255,255,0.06)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    />
  );
}
