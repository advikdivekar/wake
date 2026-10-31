import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api, Channel, Series } from "../lib/api";
import SignalCanvas from "../components/SignalCanvas";
import { Glass, Reveal, SectionHead } from "../components/ui";

export default function Observatory() {
  const [chs, setChs] = useState<Channel[]>([]);
  const [ch, setCh] = useState("CADC0872");
  const [s, setS] = useState<Series | null>(null);
  useEffect(() => { api.channels().then(setChs).catch(() => {}); }, []);
  useEffect(() => { setS(null); api.telemetry(ch).then(setS).catch(() => {}); }, [ch]);
  const cur = chs.find((c) => c.channel === ch);
  return (
    <section id="observatory" className="relative px-5 py-32 md:px-10">
      <SectionHead eyebrow="ii · signal observatory" title="Nine instruments, recorded until they fell silent."
        lede="Three magnetometers and six photodiodes, exactly as archived in OPSSAT-AD (CC-BY-4.0). Ember bands are runs of exact zeros, dark voids are sampling gaps, pale dots are prominent peaks. Nothing is smoothed." />
      <Reveal>
        <Glass className="mx-auto max-w-[1300px] overflow-hidden p-3 md:p-5">
          <div className="flex flex-wrap gap-1.5 p-2">
            {chs.map((c) => (
              <button key={c.channel} onClick={() => setCh(c.channel)}
                className={`relative rounded-full px-3.5 py-2 text-left transition ${ch === c.channel ? "text-void" : "text-bone-dim hover:text-candle"}`}>
                {ch === c.channel && <motion.span layoutId="chpill" className="absolute inset-0 rounded-full bg-marigold" transition={{ type: "spring", stiffness: 380, damping: 32 }} />}
                <span className="relative mono text-[11px] tracking-wider">{c.channel_name}</span>
                <span className={`relative ml-2 text-[10px] ${ch === c.channel ? "text-void/70" : "text-mute"}`}>{c.kind === "magnetometer" ? "MAG" : "PD"}</span>
              </button>
            ))}
          </div>
          <div className="scanline relative mt-2 rounded-2xl border border-line bg-void/70 p-2">
            <SignalCanvas series={s} height={340} animateKey={ch} segmentBands accent={cur?.kind === "photodiode" ? "#e8a33d" : "#7fb7be"} />
          </div>
          <div className="grid grid-cols-2 gap-px pt-3 md:grid-cols-5">
            {[
              ["channel", cur ? `${cur.channel} · ${cur.channel_name}` : "…"],
              ["sensor", cur?.kind ?? "…"],
              ["archived segments", cur ? String(cur.n_segments) : "…"],
              ["anomalous (train)", cur ? `${(cur.anomaly_rate_train * 100).toFixed(1)}%` : "…"],
              ["points shown", s ? `${s.v.length.toLocaleString()}${s.downsampled ? " (downsampled)" : ""}` : "…"],
            ].map(([k, v]) => (
              <div key={k} className="px-3 py-2"><div className="mono text-[9.5px] uppercase tracking-[0.22em] text-mute">{k}</div><div className="mono mt-0.5 text-[13px] text-candle">{v}</div></div>
            ))}
          </div>
        </Glass>
      </Reveal>
    </section>
  );
}
