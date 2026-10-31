import { animate, motion, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";

// Probability ring with the queue thresholds marked. Color is by decision band, labelled in text too.
export default function Ring({ p, high, low, size = 220, label = "P(anomalous)" }: { p: number; high: number; low: number; size?: number; label?: string }) {
  const R = size / 2 - 14, C = 2 * Math.PI * R;
  const mv = useMotionValue(0);
  const dash = useTransform(mv, (v) => `${v * C} ${C}`);
  const txt = useTransform(mv, (v) => v.toFixed(3));
  useEffect(() => { mv.set(0); const a = animate(mv, p, { duration: 2.4, ease: [0.16, 1, 0.3, 1] }); return () => a.stop(); }, [p, mv]);
  const color = p >= high ? "#d2592b" : p >= low ? "#e8a33d" : "#7fb7be";
  const tick = (v: number, name: string) => {
    const a = v * 2 * Math.PI - Math.PI / 2, x1 = size / 2 + Math.cos(a) * (R - 12), y1 = size / 2 + Math.sin(a) * (R - 12), x2 = size / 2 + Math.cos(a) * (R + 12), y2 = size / 2 + Math.sin(a) * (R + 12);
    const lx = size / 2 + Math.cos(a) * (R + 30), ly = size / 2 + Math.sin(a) * (R + 26);
    return <g key={name}><line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#f6e7c1" strokeOpacity={0.5} strokeWidth={1.5} />
      <text x={lx} y={ly} fill="#7d766d" fontSize={9} fontFamily="JetBrains Mono" textAnchor={Math.cos(a) < -0.3 ? "end" : Math.cos(a) > 0.3 ? "start" : "middle"} dominantBaseline="middle">{name}</text></g>;
  };
  return (
    <div className="relative" style={{ width: size + 120, height: size + 60 }}>
      <svg width={size + 120} height={size + 60} viewBox={`-60 -30 ${size + 120} ${size + 60}`} className="overflow-visible">
        <defs><filter id="glow"><feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        <circle cx={size / 2} cy={size / 2} r={R} fill="none" stroke="rgba(246,231,193,0.08)" strokeWidth={10} />
        <motion.circle cx={size / 2} cy={size / 2} r={R} fill="none" stroke={color} strokeWidth={10} strokeLinecap="round"
          style={{ strokeDasharray: dash }} transform={`rotate(-90 ${size / 2} ${size / 2})`} filter="url(#glow)" />
        {tick(low, `queue ${low}`)}{tick(high, `prioritise ${high}`)}
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <motion.div className="display text-5xl font-light text-candle">{txt}</motion.div>
          <div className="mono mt-1 text-[10px] uppercase tracking-[0.22em] text-mute">{label}</div>
        </div>
      </div>
    </div>
  );
}
