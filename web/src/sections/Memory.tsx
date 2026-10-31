import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { api, AskAnswer, getMode } from "../lib/api";
import { CitationChip } from "../components/Card";
import { Glass, Reveal, SectionHead, ease } from "../components/ui";

function Typed({ text }: { text: string }) {
  const [n, setN] = useState(0);
  useEffect(() => { setN(0); const id = setInterval(() => setN((x) => (x >= text.length ? (clearInterval(id), x) : x + 3)), 12); return () => clearInterval(id); }, [text]);
  return <>{text.slice(0, n)}<span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse bg-marigold" /></>;
}

const FIELDS = ["channel_id", "sensor_type", "units", "event_date", "observation", "operational_response", "root_cause", "evidence_excerpt"];

export default function Memory() {
  const [sugs, setSugs] = useState<string[]>([]);
  const [q, setQ] = useState("");
  const [a, setA] = useState<AskAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [exs, setExs] = useState<string[]>([]);
  const [txt, setTxt] = useState("");
  const [rec, setRec] = useState<any>(null);
  useEffect(() => { api.askSuggestions().then((s) => { setSugs(s); }).catch(() => {}); api.extractExamples().then((e) => { setExs(e); setTxt(e[0] ?? ""); }).catch(() => {}); }, []);
  const ask = async (question: string) => { setQ(question); setBusy(true); setA(null); try { setA(await api.ask(question)); } finally { setBusy(false); } };
  const extract = async (t: string) => { setTxt(t); setRec(null); setRec(await api.extract(t)); };
  return (
    <section id="memory" className="relative px-5 py-32 md:px-10">
      <SectionHead eyebrow="v · mission memory" title="Ask the archive. It will tell you what it does not know."
        lede="Hybrid retrieval (SQLite FTS5 + local embeddings) over 20 public sources, licence-aware. Every answer carries citations, and the panel on the right lists what is missing from the archive instead of filling the gap with a guess." />
      <div className="mx-auto grid max-w-[1300px] gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Reveal>
          <Glass className="p-5 md:p-7">
            <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) ask(q.trim()); }} className="flex gap-2">
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Why did OPS-SAT re-enter early?"
                className="w-full rounded-full border border-line bg-void/70 px-5 py-3 text-[14px] text-candle outline-none placeholder:text-mute focus:border-marigold/60" />
              <button className="btn btn-primary shrink-0" disabled={busy}>{busy ? "…" : "Ask"}</button>
            </form>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {sugs.map((s) => <button key={s} onClick={() => ask(s)} className="chip !normal-case !tracking-normal hover:!text-marigold">{s}</button>)}
            </div>
            {getMode() === "snapshot" && <div className="mono mt-3 text-[10.5px] text-mute">snapshot mode: suggested questions are archived real answers; free-form questions need the backend.</div>}
            <AnimatePresence mode="wait">
              {a && (
                <motion.div key={a.question} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.6, ease }} className="mt-7">
                  <div className="mono mb-2 text-[10px] uppercase tracking-[0.22em] text-mute">answer · {a.model}</div>
                  <p className="display text-xl font-light leading-relaxed text-candle"><Typed text={a.answer} /></p>
                  <div className="mt-5 grid gap-2.5 md:grid-cols-2">{a.citations.map((c, i) => <CitationChip key={i} c={c} i={i} />)}</div>
                </motion.div>
              )}
            </AnimatePresence>
          </Glass>
        </Reveal>
        <Reveal delay={0.15}>
          <div className="relative h-full overflow-hidden rounded-[22px] border border-ember/25 bg-gradient-to-b from-ember/10 to-void/80 p-6">
            <div className="pointer-events-none absolute -left-10 top-10 h-40 w-40 rounded-full bg-ember/20 blur-3xl" />
            <div className="eyebrow !text-ember">missing from the archive</div>
            <div className="mt-4 space-y-3">
              {(a?.missing.length ? a.missing : ["Ask something. If the archive is silent, it will say so here."]).map((m, i) => (
                <motion.p key={m + i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.2 }} className="flicker display text-lg italic leading-snug text-bone">{m}</motion.p>
              ))}
            </div>
          </div>
        </Reveal>
      </div>

      <Reveal>
        <Glass className="mx-auto mt-6 max-w-[1300px] p-5 md:p-7">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <div className="eyebrow">the interpreter · task A</div>
              <div className="display mt-1 text-2xl text-candle">Passage in. Verifiable record out.</div>
            </div>
            <div className="flex flex-wrap gap-1.5">{exs.map((e, i) => <button key={i} onClick={() => extract(e)} className="chip hover:!text-marigold">example {i + 1}</button>)}</div>
          </div>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            <div>
              <textarea value={txt} onChange={(e) => setTxt(e.target.value)} rows={6} className="w-full resize-none rounded-2xl border border-line bg-void/70 p-4 text-[14px] leading-relaxed text-candle outline-none focus:border-marigold/60" />
              <button onClick={() => extract(txt)} className="btn btn-primary mt-3">Extract record</button>
              <p className="mt-3 text-[12.5px] leading-relaxed text-mute">Qwen3-8B + a LoRA trained on Tinker. Every text field must be copied verbatim; a hedged cause becomes “unknown”; channel IDs and dates are cross-checked by an independent regex reader that never saw the model.</p>
            </div>
            <div className="rounded-2xl border border-line bg-void/60 p-4">
              {!rec ? <div className="mono grid h-full place-items-center py-10 text-xs text-mute">choose an example or extract</div> : (
                <div className="space-y-1.5">
                  {FIELDS.map((f, i) => {
                    const v = rec[f]; const unknown = v === null || v === undefined || v === "";
                    return (
                      <motion.div key={f} initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.06 }} className="grid grid-cols-[9.5rem_1fr] gap-3 border-b border-line/60 py-1.5 last:border-0">
                        <span className="mono text-[10.5px] uppercase tracking-[0.12em] text-mute">{f}</span>
                        <span className={`text-[13px] leading-snug ${unknown ? "italic text-ember/80" : "text-candle"}`}>{unknown ? "unknown" : String(v)}</span>
                      </motion.div>
                    );
                  })}
                  <div className="mono pt-2 text-[10.5px] text-mute">model: {rec.model}</div>
                  {rec.validator_flags?.length > 0 && <div className="mono text-[10.5px] text-marigold">validator: {rec.validator_flags.join(" · ")}</div>}
                </div>
              )}
            </div>
          </div>
        </Glass>
      </Reveal>
    </section>
  );
}
