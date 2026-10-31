import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api, TimelineItem } from "../lib/api";
import { Reveal, SectionHead, ease } from "../components/ui";

const fmt = (d: string, approx: string | null) => approx ?? new Date(d + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

export default function Elegy() {
  const [items, setItems] = useState<TimelineItem[]>([]);
  useEffect(() => { api.timeline().then(setItems).catch(() => {}); }, []);
  return (
    <section id="elegy" className="relative px-5 py-32 md:px-10">
      <SectionHead eyebrow="i · the last transmission" title="Every date here is a quote you can check."
        lede={<>Event dates and publication dates are kept apart, because the day something happened is not the day someone wrote it down. Each entry below is verified <em>verbatim</em> against the stored source before it is allowed on this page.</>} />
      <div className="relative mx-auto max-w-4xl">
        <div className="absolute bottom-0 left-[19px] top-0 w-px bg-gradient-to-b from-transparent via-candle/25 to-ember/70 md:left-1/2" />
        {items.map((it, i) => {
          const right = i % 2 === 1;
          const reentry = it.date === "2024-05-22";
          return (
            <motion.div key={i} initial={{ opacity: 0, y: 40 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-15% 0px" }}
              transition={{ duration: 1, ease }} className={`relative mb-10 pl-12 md:w-1/2 md:pl-0 ${right ? "md:ml-auto md:pl-12" : "md:pr-12 md:text-right"}`}>
              <span className={`absolute top-2 h-[11px] w-[11px] rounded-full ${reentry ? "bg-ember shadow-[0_0_24px_6px_rgba(210,89,43,.6)]" : it.date_kind === "event" ? "bg-marigold" : "border border-candle/60 bg-void"} left-[14px] ${right ? "md:-left-[5.5px]" : "md:left-auto md:-right-[5.5px]"}`} />
              <div className="mono text-[11px] uppercase tracking-[0.2em] text-mute">
                {fmt(it.date, it.approx)} · <span className={it.date_kind === "event" ? "text-marigold" : "text-signal"}>{it.date_kind === "event" ? "event date" : "publication date"}</span>
              </div>
              <div className={`display mt-1.5 text-2xl leading-tight ${reentry ? "text-ember candle-glow" : "text-candle"}`}>{it.title}</div>
              {it.citation?.excerpt && <p className="mt-2 text-[13.5px] italic leading-snug text-bone-dim">“{it.citation.excerpt}”</p>}
              <div className="mono mt-2 text-[10.5px] text-mute">
                {it.citation ? <a className="hover:text-marigold" href={it.citation.url} target="_blank" rel="noreferrer">{it.citation.doc_id} · {it.citation.license}</a> : <span>measured · {it.measured}</span>}
              </div>
            </motion.div>
          );
        })}
        <Reveal><p className="display mx-auto mt-16 max-w-xl text-center text-xl italic text-bone-dim">
          The archive disagrees with itself: one source puts the successor's launch in “late 2025”, another in 2027. We show the conflict. We don't pick a side.
        </p></Reveal>
      </div>
    </section>
  );
}
