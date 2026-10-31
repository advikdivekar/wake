import { motion, useScroll, useSpring } from "framer-motion";
import { ModeBadge } from "../components/ui";

const links = [["#elegy", "Elegy"], ["#observatory", "Observatory"], ["#seance", "The Signal"], ["#queue", "Queue"], ["#memory", "Memory"], ["#lab", "Laboratory"]];
export default function Nav() {
  const { scrollYProgress } = useScroll();
  const w = useSpring(scrollYProgress, { stiffness: 120, damping: 30 });
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-candle/[0.06] bg-void/70 backdrop-blur-xl">
      <motion.div className="h-px origin-left bg-gradient-to-r from-marigold via-candle to-ember" style={{ scaleX: w }} />
      <nav className="mx-auto flex max-w-[1400px] items-center justify-between px-5 py-4 md:px-8">
        <a href="#top" className="flex items-center gap-2.5">
          <span className="relative grid h-7 w-7 place-items-center">
            <span className="absolute h-2.5 w-2.5 rounded-full bg-marigold shadow-[0_0_18px_rgba(232,163,61,.9)]" />
            <span className="absolute h-7 w-7 -rotate-[25deg] rounded-[50%] border border-candle/50" style={{ transform: "rotate(-25deg) scaleY(.4)" }} />
          </span>
          <span className="display text-[15px] tracking-tight text-candle">The Last Satellite</span>
        </a>
        <div className="hidden items-center gap-6 lg:flex">
          {links.map(([h, l]) => <a key={h} href={h} className="mono text-[11px] uppercase tracking-[0.2em] text-bone-dim transition hover:text-marigold">{l}</a>)}
        </div>
        <ModeBadge />
      </nav>
    </header>
  );
}
