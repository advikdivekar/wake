import { motion } from "framer-motion";
import type { Card as CardT, Citation } from "../lib/api";
import { ease } from "./ui";

export function CitationChip({ c, i }: { c: Citation; i?: number }) {
  return (
    <a href={c.url} target="_blank" rel="noreferrer" className="group block rounded-xl border border-line bg-ash/60 p-3.5 transition hover:border-marigold/40">
      <div className="mono mb-1.5 flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.14em] text-mute">
        <span className="truncate">{i !== undefined && <span className="text-marigold">[{i + 1}] </span>}{c.doc_id}</span>
        <span className="shrink-0">{c.license}</span>
      </div>
      <p className="text-[13px] leading-snug text-bone">“{c.excerpt.length > 260 ? c.excerpt.slice(0, 260) + "…" : c.excerpt}”</p>
      <div className="mt-2 truncate text-[11px] text-mute group-hover:text-marigold">{c.title} · {c.location}</div>
    </a>
  );
}

const decisionTone: Record<string, string> = { prioritise: "text-ember border-ember/40", queue: "text-marigold border-marigold/40", archive: "text-signal border-signal/40" };

export default function InvestigationCard({ card, compact = false }: { card: CardT; compact?: boolean }) {
  const llm = !card.summary_model.startsWith("template");
  const rejected = card.summary_model.includes("rejected");
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, ease }}
      className="relative overflow-hidden rounded-[22px] border border-candle/10 bg-gradient-to-b from-ash-2/90 to-night/95 p-6 md:p-7">
      <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-marigold/10 blur-3xl" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="eyebrow !text-[10px]">investigation card · {card.card_id}</div>
          <div className="display mt-1 text-2xl text-candle">Segment {card.segment_id}</div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`chip ${decisionTone[card.prediction.decision]}`}>{card.prediction.decision}</span>
          <span className="chip">p = {card.prediction.probability.toFixed(3)}</span>
          {card.review_status !== "unreviewed" && <span className="chip !border-good/40 !text-good">{card.review_status}</span>}
        </div>
      </div>
      <div className={`mt-6 grid gap-6 ${compact ? "" : "md:grid-cols-2"}`}>
        <div>
          <div className="mono mb-3 text-[10px] uppercase tracking-[0.24em] text-good">what is known</div>
          <ul className="space-y-2.5">
            {card.known.map((k, i) => (
              <motion.li key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 + i * 0.08, duration: 0.6, ease }}
                className="flex gap-3 text-[13.5px] leading-snug text-bone">
                <span className={`mono mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[9.5px] uppercase ${k.basis === "measured" ? "bg-signal/15 text-signal" : "bg-marigold/15 text-marigold"}`}>{k.basis}</span>
                <span>{k.statement}</span>
              </motion.li>
            ))}
          </ul>
        </div>
        <div>
          <div className="mono mb-3 text-[10px] uppercase tracking-[0.24em] text-ember">what is NOT known</div>
          <ul className="space-y-2.5">
            {card.unknown.map((u, i) => (
              <li key={i} className="flicker flex gap-3 text-[13.5px] leading-snug text-bone-dim"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ember" />{u}</li>
            ))}
          </ul>
          <div className="mt-6 rounded-xl border border-line bg-void/50 p-4">
            <div className="mono mb-2 flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-mute">
              summary ·
              <span className={llm ? "text-marigold" : rejected ? "text-ember" : "text-mute"}>
                {llm ? "written by the fine-tuned interpreter (local)" : rejected ? "interpreter output rejected by validator → deterministic template" : "deterministic template"}
              </span>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-bone">{card.summary}</pre>
          </div>
          <div className="mt-4 text-[13px] text-candle"><span className="mono mr-2 text-[10px] uppercase tracking-[0.2em] text-mute">suggested action</span>{card.suggested_action}</div>
        </div>
      </div>
    </motion.div>
  );
}
