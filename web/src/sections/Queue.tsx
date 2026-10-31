import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { api, Card, Segment, Series } from "../lib/api";
import SignalCanvas from "../components/SignalCanvas";
import InvestigationCard from "../components/Card";
import { Glass, Reveal, SectionHead, ease } from "../components/ui";

const tone: Record<string, string> = { prioritise: "#d2592b", queue: "#e8a33d", archive: "#7fb7be" };

export default function Queue() {
  const [rows, setRows] = useState<Segment[]>([]);
  const [filter, setFilter] = useState<"all" | "prioritise" | "queue" | "archive">("prioritise");
  const [open, setOpen] = useState<number | null>(null);
  useEffect(() => { api.queue().then(setRows).catch(() => {}); }, []);
  const counts = useMemo(() => rows.reduce((a, r) => { a[r.decision ?? "archive"] = (a[r.decision ?? "archive"] ?? 0) + 1; return a; }, {} as Record<string, number>), [rows]);
  const shown = rows.filter((r) => filter === "all" || r.decision === filter).slice(0, 40);
  return (
    <section id="queue" className="relative px-5 py-32 md:px-10">
      <SectionHead eyebrow="iv · investigation queue" title="529 archived segments, ranked by how wrong they look."
        lede="TabPFN's probability decides the queue: prioritise, queue, or let it rest in the archive. Thresholds were chosen on training data only. Open any segment to see its card, then confirm, reject or investigate. Your verdict is stored as feedback." />
      <Reveal>
        <Glass className="mx-auto max-w-[1300px] p-3 md:p-5">
          <div className="flex flex-wrap items-center gap-2 p-2">
            {(["prioritise", "queue", "archive", "all"] as const).map((f) => (
              <button key={f} onClick={() => setFilter(f)} className={`chip transition ${filter === f ? "!border-marigold !text-marigold" : "hover:!text-candle"}`}>
                {f} {f !== "all" ? `· ${counts[f] ?? 0}` : `· ${rows.length}`}
              </button>
            ))}
            <span className="mono ml-auto text-[10.5px] text-mute">labels hidden · showing up to 40</span>
          </div>
          <div className="divide-y divide-line/70">
            {shown.map((r, i) => (
              <div key={r.segment_id}>
                <motion.button layout onClick={() => setOpen(open === r.segment_id ? null : r.segment_id)}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: Math.min(i * 0.02, 0.4) }}
                  className="grid w-full grid-cols-[3.5rem_1fr_auto] items-center gap-4 px-3 py-3 text-left transition hover:bg-candle/[0.03] md:grid-cols-[4rem_10rem_1fr_6rem_7rem]">
                  <span className="mono text-[11px] text-mute">#{i + 1}</span>
                  <span className="hidden md:block"><span className="display text-lg text-candle">{r.segment_id}</span><span className="mono ml-2 text-[10.5px] text-mute">{r.channel_name}</span></span>
                  <span className="relative h-2 overflow-hidden rounded-full bg-candle/[0.06]">
                    <motion.span initial={{ width: 0 }} whileInView={{ width: `${(r.probability ?? 0) * 100}%` }} viewport={{ once: true }} transition={{ duration: 1.2, ease }}
                      className="absolute left-0 top-0 h-full rounded-full" style={{ background: tone[r.decision ?? "archive"], boxShadow: `0 0 16px ${tone[r.decision ?? "archive"]}` }} />
                  </span>
                  <span className="mono text-right text-[13px] text-candle">{(r.probability ?? 0).toFixed(3)}</span>
                  <span className="hidden text-right md:block"><span className="chip" style={{ color: tone[r.decision ?? "archive"], borderColor: tone[r.decision ?? "archive"] + "66" }}>{r.decision}</span></span>
                </motion.button>
                <AnimatePresence>{open === r.segment_id && <Drawer id={r.segment_id} />}</AnimatePresence>
              </div>
            ))}
          </div>
        </Glass>
      </Reveal>
    </section>
  );
}

function Drawer({ id }: { id: number }) {
  const [s, setS] = useState<Series | null>(null);
  const [card, setCard] = useState<Card | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    api.segment(id).then((x) => setS(x.series)).catch(() => setErr(true));
    api.investigate(id).then((c) => {
      let st: string | null = null; try { st = localStorage.getItem(`fb:${id}`); } catch { /* ignore */ }
      setCard(st ? { ...c, review_status: st } : c);
    }).catch(() => setErr(true));
  }, [id]);
  const act = async (a: "confirm" | "reject" | "investigate") => { if (card) setCard(await api.feedback(card, a)); };
  return (
    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.6, ease }} className="overflow-hidden">
      <div className="space-y-4 px-2 pb-6 pt-2 md:px-4">
        {err && <div className="mono rounded-xl border border-line p-4 text-xs text-mute">This segment's card isn't in the archived snapshot. Run the backend (<span className="text-candle">make api</span>) to investigate any segment live.</div>}
        {s && <div className="rounded-2xl border border-line bg-void/70 p-2"><SignalCanvas series={s} height={170} animateKey={id} /></div>}
        {card && (
          <>
            <InvestigationCard card={card} />
            <div className="flex flex-wrap gap-2">
              <button onClick={() => act("confirm")} className="btn btn-ghost !border-good/40 !text-good">✓ Confirm anomaly</button>
              <button onClick={() => act("reject")} className="btn btn-ghost">✕ Reject</button>
              <button onClick={() => act("investigate")} className="btn btn-ghost !border-marigold/40 !text-marigold">◎ Investigate further</button>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}
