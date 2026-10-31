import { animate, motion, useInView, useMotionValue, useTransform } from "framer-motion";
import { ReactNode, useEffect, useRef, useState } from "react";
import { getMode, Mode, onMode } from "../lib/api";

export const ease = [0.16, 1, 0.3, 1] as const;

export function Reveal({ children, delay = 0, y = 28, className = "" }: { children: ReactNode; delay?: number; y?: number; className?: string }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y, filter: "blur(8px)" }} whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-12% 0px" }} transition={{ duration: 1.1, delay, ease }}>
      {children}
    </motion.div>
  );
}

export function SplitWords({ text, className = "", delay = 0 }: { text: string; className?: string; delay?: number }) {
  // the parent observes visibility (children are clipped, so they can't be observed themselves)
  return (
    <motion.span className={className} aria-label={text} initial="hide" whileInView="show" viewport={{ once: true, margin: "-8% 0px" }}
      variants={{ show: { transition: { staggerChildren: 0.06, delayChildren: delay } } }}>
      {text.split(" ").map((w, i) => (
        <span key={i} className="inline-block overflow-hidden pb-[0.08em] align-bottom" aria-hidden>
          <motion.span className="inline-block" variants={{ hide: { y: "110%" }, show: { y: 0, transition: { duration: 1.1, ease } } }}>{w}&nbsp;</motion.span>
        </span>
      ))}
    </motion.span>
  );
}

export function Counter({ value, decimals = 3, prefix = "", suffix = "", className = "" }: { value: number; decimals?: number; prefix?: string; suffix?: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const mv = useMotionValue(0);
  const text = useTransform(mv, (v) => `${prefix}${v.toFixed(decimals)}${suffix}`);
  useEffect(() => { if (inView) animate(mv, value, { duration: 2.2, ease }); }, [inView, value, mv]);
  return <motion.span ref={ref} className={className}>{text}</motion.span>;
}

export function ModeBadge() {
  const [mode, setMode] = useState<Mode | null>(getMode());
  useEffect(() => onMode(setMode), []);
  if (!mode) return null;
  return (
    <span className={`chip ${mode === "live" ? "!border-good/50 !text-good" : "!border-marigold/40 !text-marigold"}`}
      title={mode === "live" ? "Connected to the FastAPI backend: every panel is computed now." : "No backend reachable: showing an archived snapshot of real API responses (scripts/export_snapshot.py)."}>
      <span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${mode === "live" ? "bg-good animate-pulse" : "bg-marigold"}`} />
      {mode === "live" ? "live backend" : "archived snapshot"}
    </span>
  );
}

export function SectionHead({ eyebrow, title, lede, id }: { eyebrow: string; title: string; lede?: ReactNode; id?: string }) {
  return (
    <div id={id} className="mx-auto mb-14 max-w-3xl text-center">
      <Reveal><div className="eyebrow mb-5">{eyebrow}</div></Reveal>
      <h2 className="display text-4xl font-light leading-[1.05] text-candle md:text-6xl"><SplitWords text={title} /></h2>
      {lede && <Reveal delay={0.25}><p className="mx-auto mt-6 max-w-2xl text-[15px] leading-relaxed text-bone-dim">{lede}</p></Reveal>}
    </div>
  );
}

export function Glass({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`glass rounded-[22px] ${className}`}>{children}</div>;
}
