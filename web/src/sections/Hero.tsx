import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { ease } from "../components/ui";

export default function Hero() {
  const [m, setM] = useState<any>(null);
  useEffect(() => { api.mission().then(setM).catch(() => {}); }, []);
  const ds = m?.datasets?.[0];
  const stats = [
    ["Last transmission", "22 May 2024"],
    ["Archived segments", ds ? ds.segments.toLocaleString() : "…"],
    ["Telemetry channels", m ? String(m.channels.length) : "…"],
    ["Official split", ds ? `${ds.train.toLocaleString()} / ${ds.test}` : "…"],
  ];
  return (
    <section id="top" className="relative flex min-h-[100svh] flex-col justify-end px-5 pb-14 pt-32 md:px-10">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-void via-void/20 to-transparent" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-void/85 via-void/30 to-transparent" />
      <div className="relative mx-auto w-full max-w-[1400px]">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4, duration: 1.4 }} className="eyebrow mb-6">
          ESA · OPS-SAT · 2019 – 2024 · archival mission memory engine
        </motion.div>
        <h1 className="display max-w-[14ch] text-[clamp(3.2rem,10vw,9.5rem)] font-[250] leading-[0.88] text-candle">
          {["The", "Last", "Satellite"].map((w, i) => (
            <span key={w} className="mr-[0.22em] inline-block overflow-hidden align-bottom">
              <motion.span className={`inline-block ${i === 2 ? "italic text-marigold candle-glow" : ""}`} initial={{ y: "105%", rotate: 4 }}
                animate={{ y: 0, rotate: 0 }} transition={{ delay: 0.5 + i * 0.14, duration: 1.4, ease }}>{w}</motion.span>
            </span>
          ))}
        </h1>
        <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.2, duration: 1.2, ease }}
          className="display mt-8 max-w-xl text-2xl font-light italic text-bone md:text-3xl">
          Its mission ended. Its memories did not.
        </motion.p>
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.6, duration: 1.2 }}
          className="mt-5 max-w-xl text-[15px] leading-relaxed text-bone-dim">
          OPS-SAT was ESA's flying laboratory, until the atmosphere took it back. This console reads what it left behind:
          <span className="text-signal"> TabPFN</span> listens to its archived telemetry, a
          <span className="text-marigold"> Tinker-tuned interpreter</span> reads its documents, and nothing is ever claimed that the archive cannot show.
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.9, duration: 1 }} className="mt-9 flex flex-wrap gap-3">
          <a href="#seance" className="btn btn-primary">Hear the signal that should not be there →</a>
          <a href="#lab" className="btn btn-ghost">See the numbers</a>
        </motion.div>
        <motion.dl initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2.3, duration: 1.2 }}
          className="mt-16 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-candle/10 bg-candle/10 md:grid-cols-4">
          {stats.map(([k, v]) => (
            <div key={k} className="bg-void/70 px-5 py-4 backdrop-blur-md">
              <dt className="mono text-[10px] uppercase tracking-[0.22em] text-mute">{k}</dt>
              <dd className="display mt-1 text-2xl text-candle">{v}</dd>
            </div>
          ))}
        </motion.dl>
      </div>
      <motion.div animate={{ y: [0, 8, 0] }} transition={{ repeat: Infinity, duration: 2.4 }} className="mono absolute bottom-5 left-1/2 -translate-x-1/2 text-[10px] uppercase tracking-[0.3em] text-mute">
        scroll · the orbit decays
      </motion.div>
    </section>
  );
}
