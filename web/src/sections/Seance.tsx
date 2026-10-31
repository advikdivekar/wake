import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { api, DemoSteps, Reveal as RevealT } from "../lib/api";
import SignalCanvas from "../components/SignalCanvas";
import Ring from "../components/Ring";
import InvestigationCard, { CitationChip } from "../components/Card";
import { Glass, SectionHead, ease } from "../components/ui";

const STEPS = ["The signal", "Measured", "TabPFN", "Memory", "Resemblance", "The card"] as const;
const CASE: Record<string, { label: string; tone: string; line: string }> = {
  TP: { label: "TRUE POSITIVE", tone: "text-ember border-ember", line: "It was an anomaly, and the console flagged it." },
  TN: { label: "TRUE NEGATIVE", tone: "text-signal border-signal", line: "It was nominal, and the console let it rest." },
  FP: { label: "FALSE ALARM", tone: "text-marigold border-marigold", line: "Nominal, but flagged. We keep this one in the record." },
  FN: { label: "MISSED ANOMALY", tone: "text-alert border-alert", line: "An anomaly the model did not catch. Shown, not hidden." },
};

export default function Seance() {
  const [demo, setDemo] = useState<{ segment_id: number; blurb: string }[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [d, setD] = useState<DemoSteps | null>(null);
  const [step, setStep] = useState(0);
  const [auto, setAuto] = useState(false);
  const [rev, setRev] = useState<RevealT | null>(null);
  const timer = useRef<number>();
  useEffect(() => { api.demo().then((x) => { setDemo(x); }).catch(() => {}); }, []);
  useEffect(() => {
    if (sel === null) return;
    setD(null); setRev(null); setStep(0);
    api.demoSteps(sel).then(setD).catch(() => {});
  }, [sel]);
  useEffect(() => {
    window.clearTimeout(timer.current);
    if (auto && d && step < STEPS.length - 1) timer.current = window.setTimeout(() => setStep((s) => s + 1), step === 0 ? 4200 : 3600);
    if (auto && step === STEPS.length - 1) setAuto(false);
    return () => window.clearTimeout(timer.current);
  }, [auto, step, d]);
  const start = (id: number) => { setSel(id); setAuto(true); setTimeout(() => { const el = document.getElementById("seance-stage"); if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 90, behavior: "smooth" }); }, 60); };
  const doReveal = () => sel !== null && api.demoReveal(sel).then(setRev);

  const feats = d ? Object.entries(d.features.features).filter(([k]) => d.features.published_18.includes(k)) : [];
  return (
    <section id="seance" className="relative px-5 py-32 md:px-10">
      <SectionHead eyebrow="iii · the signal that should not be there" title="Pick a candle. Hide the truth. Listen."
        lede="Six real segments from the official test split. Their labels are hidden from you and from the model. Step through what the engine sees, then reveal what actually happened, including the false alarm and the anomaly it missed." />
      <div className="mx-auto grid max-w-[1300px] grid-cols-2 gap-3 md:grid-cols-6">
        {demo.map((x, i) => (
          <motion.button key={x.segment_id} onClick={() => start(x.segment_id)} whileHover={{ y: -6 }}
            initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08, duration: 0.9, ease }}
            className={`group relative overflow-hidden rounded-2xl border p-4 text-left transition ${sel === x.segment_id ? "border-marigold/70 bg-marigold/10" : "border-candle/10 bg-ash/50 hover:border-candle/30"}`}>
            <div className="relative mx-auto mb-4 mt-2 h-14 w-3 rounded-sm bg-gradient-to-b from-candle to-bone-dim/60">
              <motion.div animate={{ scaleY: [1, 1.15, 0.95, 1.1, 1], x: [0, 1, -1, 0] }} transition={{ repeat: Infinity, duration: 1.8 + i * 0.2 }}
                className="absolute -top-5 left-1/2 h-5 w-3 -translate-x-1/2 rounded-[50%_50%_50%_50%/60%_60%_40%_40%] bg-gradient-to-t from-marigold via-candle to-white shadow-[0_0_24px_8px_rgba(232,163,61,.45)]" />
            </div>
            <div className="mono text-[10px] uppercase tracking-[0.2em] text-mute">segment</div>
            <div className="display text-2xl text-candle">#{x.segment_id}</div>
            <div className="mt-1 text-[11.5px] leading-snug text-bone-dim">{x.blurb}</div>
          </motion.button>
        ))}
      </div>

      <div id="seance-stage" className="mx-auto mt-10 max-w-[1300px] scroll-mt-24">
        <AnimatePresence mode="wait">
          {sel !== null && (
            <motion.div key={sel} initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.8, ease }}>
              <Glass className="p-4 md:p-7">
                {/* stepper */}
                <div className="mb-6 flex flex-wrap items-center gap-2">
                  {STEPS.map((s, i) => (
                    <button key={s} onClick={() => { setAuto(false); setStep(i); }} className="group relative flex items-center gap-2 pr-2">
                      <span className={`mono grid h-7 w-7 place-items-center rounded-full border text-[11px] transition ${i <= step ? "border-marigold bg-marigold text-void" : "border-line text-mute"}`}>{i + 1}</span>
                      <span className={`text-[12.5px] ${i === step ? "text-candle" : "text-mute group-hover:text-bone"}`}>{s}</span>
                      {i < STEPS.length - 1 && <span className="ml-1 hidden h-px w-6 bg-line md:block" />}
                    </button>
                  ))}
                  <div className="ml-auto flex gap-2">
                    <button onClick={() => setAuto((a) => !a)} className="btn btn-ghost !py-1.5 text-xs">{auto ? "❚❚ pause" : "▶ guided"}</button>
                    <button onClick={() => { setAuto(false); setStep((s) => Math.min(s + 1, STEPS.length - 1)); }} className="btn btn-ghost !py-1.5 text-xs">next →</button>
                  </div>
                </div>
                {!d ? <div className="mono py-24 text-center text-xs text-mute">opening the archive…</div> : (
                  <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr]">
                    <div className="space-y-5">
                      <div className="rounded-2xl border border-line bg-void/70 p-3">
                        <div className="mono flex flex-wrap justify-between gap-2 px-1 pb-2 text-[10.5px] uppercase tracking-[0.18em] text-mute">
                          <span>{d.segment.channel} · {d.segment.channel_name} · {d.segment.channel_kind}</span>
                          <span>{d.segment.start.slice(0, 19).replace("T", " ")} · {d.segment.n_points} pts · label hidden</span>
                        </div>
                        <SignalCanvas series={d.series} height={240} animateKey={sel} accent="#f6e7c1" />
                      </div>
                      <AnimatePresence mode="wait">
                        {step === 1 && (
                          <motion.div key="f" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-2 gap-2 md:grid-cols-3">
                            {feats.map(([k, v], i) => (
                              <motion.div key={k} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                                className="rounded-lg border border-line bg-ash/50 px-3 py-2">
                                <div className="mono truncate text-[9.5px] uppercase tracking-[0.14em] text-mute">{k}</div>
                                <div className="mono text-[13px] text-candle">{typeof v === "number" ? (Math.abs(v) < 0.01 && v !== 0 ? v.toExponential(2) : +v.toFixed(3)) : v}</div>
                              </motion.div>
                            ))}
                          </motion.div>
                        )}
                        {step === 3 && (
                          <motion.div key="m" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid gap-3 md:grid-cols-2">
                            {d.citations.slice(0, 4).map((c, i) => (
                              <motion.div key={c.chunk_id} initial={{ opacity: 0, y: 24, rotate: -1.5 }} animate={{ opacity: 1, y: 0, rotate: 0 }} transition={{ delay: i * 0.18, duration: 0.8, ease }}>
                                <CitationChip c={c} i={i} />
                              </motion.div>
                            ))}
                          </motion.div>
                        )}
                        {step === 4 && (
                          <motion.div key="r" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                            <Constellation sim={d.similar} />
                          </motion.div>
                        )}
                        {step === 5 && <motion.div key="c" initial={{ opacity: 0 }} animate={{ opacity: 1 }}><InvestigationCard card={d.card} compact /></motion.div>}
                      </AnimatePresence>
                    </div>
                    <div className="flex flex-col items-center justify-start gap-6">
                      <AnimatePresence>
                        {step >= 2 ? (
                          <motion.div key="ring" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.9, ease }} className="flex flex-col items-center">
                            <Ring p={d.prediction.probability} high={d.prediction.thresholds.high} low={d.prediction.thresholds.low} />
                            <div className="mono mt-2 text-[10.5px] uppercase tracking-[0.2em] text-mute">{d.prediction.model}</div>
                            <div className="mt-5 w-full space-y-2">
                              <div className="mono text-[10px] uppercase tracking-[0.22em] text-mute">top measured characteristics</div>
                              {d.prediction.contributors.map((c, i) => (
                                <motion.div key={c.feature} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 + i * 0.1 }}
                                  className="flex items-center gap-3 text-[12.5px]">
                                  <span className="w-40 shrink-0 text-bone-dim">{c.plain}</span>
                                  <span className="relative h-1.5 flex-1 overflow-hidden rounded bg-candle/10">
                                    <motion.span initial={{ width: 0 }} animate={{ width: `${Math.min(100, Math.abs(c.z) * 12)}%` }} transition={{ delay: 0.7 + i * 0.1, duration: 1.2, ease }}
                                      className={`absolute left-0 top-0 h-full rounded ${c.z >= 0 ? "bg-marigold" : "bg-signal"}`} />
                                  </span>
                                  <span className="mono w-14 text-right text-[11px] text-mute">z {c.z > 0 ? "+" : ""}{c.z}</span>
                                </motion.div>
                              ))}
                            </div>
                          </motion.div>
                        ) : (
                          <motion.div key="wait" exit={{ opacity: 0 }} className="display mt-16 max-w-xs text-center text-2xl italic leading-snug text-bone-dim">
                            {step === 0 ? "A segment from the archive. No label. No context. Just the signal." : "Eighteen published features, reproduced from the raw samples."}
                          </motion.div>
                        )}
                      </AnimatePresence>
                      {step === STEPS.length - 1 && (
                        <div className="mt-2 w-full text-center">
                          {!rev ? (
                            <motion.button initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={doReveal} className="btn btn-primary">Reveal the truth</motion.button>
                          ) : (
                            <motion.div initial={{ rotateX: 90, opacity: 0 }} animate={{ rotateX: 0, opacity: 1 }} transition={{ duration: 0.9, ease }} style={{ transformPerspective: 800 }}
                              className={`mx-auto max-w-sm rounded-2xl border-2 bg-void/80 p-5 ${CASE[rev.case].tone}`}>
                              <div className="mono text-[11px] uppercase tracking-[0.3em]">ground truth: {rev.label ? "anomalous" : "nominal"}</div>
                              <div className="display mt-1 text-4xl">{CASE[rev.case].label}</div>
                              <div className="mt-2 text-[13px] text-bone-dim">{CASE[rev.case].line}</div>
                              <div className="mono mt-3 text-[10.5px] text-mute">p = {rev.probability.toFixed(3)} vs max-F1 threshold {rev.threshold.toFixed(3)} (chosen on training data)</div>
                            </motion.div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </Glass>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

function Constellation({ sim }: { sim: DemoSteps["similar"] }) {
  const W = 560, H = 240, cx = W / 2, cy = H / 2;
  const maxD = Math.max(...sim.map((s) => s.distance), 1);
  return (
    <div className="rounded-2xl border border-line bg-void/70 p-4">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {[0.35, 0.7, 1].map((r) => <circle key={r} cx={cx} cy={cy} r={r * 105} fill="none" stroke="rgba(246,231,193,.06)" />)}
        {sim.map((s, i) => {
          const a = (i / sim.length) * Math.PI * 2 - Math.PI / 2, r = 30 + (s.distance / maxD) * 75;
          const x = cx + Math.cos(a) * r * 2.1, y = cy + Math.sin(a) * r;
          return (
            <g key={s.segment_id}>
              <motion.line x1={cx} y1={cy} x2={x} y2={y} stroke="rgba(246,231,193,.18)" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ delay: i * 0.15, duration: 0.8 }} />
              <motion.circle cx={x} cy={y} r={7} fill={s.label ? "#d2592b" : "#7fb7be"} stroke="#050507" strokeWidth={2} initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.3 + i * 0.15 }} />
              <text x={x} y={y - 13} textAnchor="middle" fill="#b9b1a4" fontSize={10} fontFamily="JetBrains Mono">#{s.segment_id} · d {s.distance}</text>
            </g>
          );
        })}
        <circle cx={cx} cy={cy} r={9} fill="#f6e7c1" /><circle cx={cx} cy={cy} r={16} fill="none" stroke="#e8a33d" strokeOpacity={0.6} />
      </svg>
      <div className="mono mt-2 flex flex-wrap gap-4 text-[10.5px] text-mute">
        <span><span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-ember" />labelled anomalous</span>
        <span><span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-signal" />labelled nominal</span>
        <span className="text-bone-dim">{sim[0]?.note}</span>
      </div>
    </div>
  );
}
