import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { GlowOrb, Screen } from "@/components/Screen";
import { COLORS, DISPLAY_FONT, GOLD_GRAD, ORANGE_GRAD } from "@/lib/theme";

/** Cuisines that drift up behind the logo — a hint of what the app is about. */
const FLOATERS = [
  { emoji: "🍛", left: "12%", delay: 0, duration: 9 },
  { emoji: "🍕", left: "78%", delay: 1.6, duration: 11 },
  { emoji: "🍜", left: "30%", delay: 3.2, duration: 10 },
  { emoji: "🌮", left: "64%", delay: 4.6, duration: 12 },
  { emoji: "🍣", left: "46%", delay: 6.1, duration: 10.5 },
];

// Children reveal one after another rather than all at once.
const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.14, delayChildren: 0.15 } },
};
// Standalone variants aren't contextually typed, so the bezier needs the tuple.
const EASE_OUT: [number, number, number, number] = [0.16, 1, 0.3, 1];

const item = {
  hidden: { opacity: 0, y: 26 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE_OUT } },
};

export default function SplashScreen() {
  return (
    <Screen gradient className="items-center justify-center relative overflow-hidden">
      <motion.div
        className="absolute inset-0"
        animate={{ opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      >
        <GlowOrb className="top-16 left-8 w-72 h-72 opacity-25" />
        <GlowOrb className="bottom-28 right-4 w-56 h-56 opacity-15" color={COLORS.gold} />
      </motion.div>

      {FLOATERS.map((f) => (
        <motion.span
          key={f.emoji}
          className="absolute text-3xl pointer-events-none select-none"
          style={{ left: f.left, bottom: -60 }}
          animate={{ y: [0, -620], opacity: [0, 0.5, 0.5, 0], rotate: [0, 18, -12, 0] }}
          transition={{
            duration: f.duration,
            delay: f.delay,
            repeat: Infinity,
            ease: "linear",
          }}
        >
          {f.emoji}
        </motion.span>
      ))}

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="flex flex-col items-center gap-7 z-10 px-8 text-center"
      >
        <motion.div variants={item} className="relative">
          <motion.div
            className="absolute inset-0 m-auto rounded-full"
            style={{ width: 120, height: 120, background: GOLD_GRAD, filter: "blur(30px)" }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="w-28 h-28 rounded-[36px] flex items-center justify-center text-6xl shadow-2xl relative"
            style={{ background: GOLD_GRAD }}
            animate={{ y: [0, -12, 0], rotate: [0, 3, -3, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          >
            🍽️
          </motion.div>
        </motion.div>

        <motion.div variants={item}>
          <h1
            className="text-5xl font-black text-white tracking-tight mb-3"
            style={DISPLAY_FONT}
          >
            Kya Khaoon
          </h1>
          <motion.p
            className="text-white/45 text-base italic font-medium"
            animate={{ opacity: [0.45, 0.85, 0.45] }}
            transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut" }}
          >
            What should I eat today?
          </motion.p>
        </motion.div>

        <motion.div variants={item}>
          <motion.div
            animate={{ scale: [1, 1.04, 1] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
          >
            {/* Device sign-in already happened silently, so there's no login
                step — straight to connecting Swiggy. */}
            <Link
              to="/connect"
              className="mt-4 px-10 py-4 rounded-2xl text-white font-black text-lg flex items-center gap-3 shadow-2xl active:scale-95 transition-transform"
              style={{ background: ORANGE_GRAD }}
            >
              Let&apos;s Begin
              <motion.span
                animate={{ x: [0, 5, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                className="flex"
              >
                <ArrowRight size={20} />
              </motion.span>
            </Link>
          </motion.div>
        </motion.div>
      </motion.div>
    </Screen>
  );
}
