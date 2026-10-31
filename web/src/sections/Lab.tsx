import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import { Counter, Glass, Reveal, SectionHead, ease } from "../components/ui";

const NICE: Record<string, string> = { "tabpfn-v2": "TabPFN-v2", rf: "Random Forest", xgboost: "XGBoost", lightgbm: "LightGBM", lr: "Logistic Reg.", iforest: "Isolation Forest", rule: "Zero-fraction rule" };
const nice = (m: string) => NICE[m.split(":")[0]] ?? m;
const S1 = "#e8a33d", S2 = "#7fb7be", S3 = "#d2592b", GRAY = "#4a4550";

type Row = { name: string; auprc: number; f1: number; mcc: number; kind: "ours" | "published"; hero?: boolean };

function parsePublished(md: string): Row[] {
  return md.split("\n").filter((l) => l.includes("(published")).map((l) => {
    const c = l.split("|").map((x) => x.trim()).filter(Boolean);
    return { name: c[0].replace(/\s*\(published[^)]*\)/, "").trim() + " · paper", auprc: +c[1], f1: +c[3], mcc: +c[6], kind: "published" as const };
  });
}

export default function Lab() {
  const [E, setE] = useState<Record<string, any> | null>(null);
  useEffect(() => { api.evaluations().then(setE).catch(() => {}); }, []);
  if (!E) return <section id="lab" className="px-5 py-32 text-center"><div className="mono text-xs text-mute">loading the laboratory…</div></section>;
  const tab = E["tabpfn_test_results.json"]?.models?.[0];
  const tA = E["tinker_eval_A.json"], tD = E["tinker_eval_D.json"];
  const cost = E["tinker_cost.json"]?.total_est_usd;
  const off = E["offline_inference.json"];
  const fp = tab?.confusion?.[0]?.[1], fn = tab?.confusion?.[1]?.[0];
  return (
    <section id="lab" className="relative px-5 py-32 md:px-10">
      <SectionHead eyebrow="vi · model laboratory" title="Measured, not promised."
        lede="Every number on this page is read from the evaluation files the pipeline wrote (evaluations/*.json). The official test split was run once per final configuration, and each run is logged. Published results are quoted from Ruszczak et al., Sci Data 2025, Table 3." />

      <div className="mx-auto grid max-w-[1300px] grid-cols-2 gap-3 md:grid-cols-4">
        {[
          { k: "TabPFN AUCPR · test", v: tab?.auprc, d: 3, sub: "best published: 0.979" },
          { k: "TabPFN F1 · test", v: tab?.f1, d: 3, sub: "best published: 0.946" },
          { k: "Interpreter · task A", v: tA?.tuned?.field_exact_match * 100, d: 1, suf: "%", sub: `base model: ${(tA?.base?.field_exact_match * 100).toFixed(1)}%` },
          { k: "Tinker spend · everything", v: cost, d: 2, pre: "$", sub: "token count × list price" },
        ].map((s, i) => (
          <Reveal key={s.k} delay={i * 0.08}>
            <Glass className="h-full p-5">
              <div className="mono text-[10px] uppercase tracking-[0.2em] text-mute">{s.k}</div>
              <div className="display mt-2 text-5xl font-light text-candle">{s.v !== undefined ? <Counter value={s.v} decimals={s.d} prefix={s.pre} suffix={s.suf} /> : "—"}</div>
              <div className="mt-1 text-[12px] text-bone-dim">{s.sub}</div>
            </Glass>
          </Reveal>
        ))}
      </div>
      {tab && <Reveal><p className="display mx-auto mt-8 max-w-3xl text-center text-xl italic text-bone-dim">
        {fp} false alarm{fp === 1 ? "" : "s"} and {fn} missed anomalies across {E["tabpfn_test_results.json"].n_test} archived segments. Brier score {tab.brier.toFixed(4)}.
      </p></Reveal>}

      <Bench E={E} />
      <div className="mx-auto mt-6 grid max-w-[1300px] gap-6 lg:grid-cols-2">
        <PRCurves E={E} />
        <Threshold E={E} />
      </div>
      <div className="mx-auto mt-6 grid max-w-[1300px] gap-6 lg:grid-cols-[1fr_1.2fr]">
        <Calibration E={E} />
        <Importance E={E} />
      </div>

      <div className="mx-auto mt-24 max-w-[1300px]">
        <div className="mb-10 text-center"><div className="eyebrow">the interpreter · tinker</div>
          <div className="display mx-auto mt-3 max-w-3xl text-3xl font-light text-candle md:text-5xl">A small model, taught to copy instead of invent.</div></div>
        <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <Dumbbell E={E} />
          <LearningCurve E={E} />
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-3">
          <Glass className="p-6">
            <div className="eyebrow">task A · fine-tuned</div>
            <div className="mt-4 space-y-3">
              {[["valid schema", tA?.tuned?.valid_schema_rate], ["evidence copied verbatim", tA?.tuned?.evidence_fidelity], ["whole record exactly right", tA?.tuned?.record_exact_match], ["correct use of “unknown”", tA?.tuned?.null_correctness]].map(([k, v]) => (
                <div key={k as string}>
                  <div className="flex justify-between text-[13px]"><span className="text-bone-dim">{k}</span><span className="mono text-candle">{((v as number) * 100).toFixed(1)}%</span></div>
                  <div className="mt-1 h-1.5 rounded bg-candle/10"><motion.div initial={{ width: 0 }} whileInView={{ width: `${(v as number) * 100}%` }} viewport={{ once: true }} transition={{ duration: 1.4, ease }} className="h-full rounded bg-marigold" /></div>
                </div>
              ))}
              <div className="flex justify-between border-t border-line pt-3 text-[13px]"><span className="text-bone-dim">unsupported root causes</span><span className="mono text-good">{tA?.tuned?.unsupported_root_causes}</span></div>
            </div>
          </Glass>
          <Glass className="p-6">
            <div className="eyebrow">offline · no tinker, no key</div>
            <div className="display mt-3 text-5xl font-light text-candle"><Counter value={(off?.field_agreement_with_tinker_bf16_outputs ?? 0) * 100} decimals={0} suffix="%" /></div>
            <p className="mt-2 text-[13px] leading-relaxed text-bone-dim">field-for-field agreement between the adapter running locally in llama.cpp (Q4_K_M base + GGUF LoRA, HF offline, no API key) and the same checkpoint sampled on Tinker. Local exact match {(off?.task_A?.field_exact_match * 100).toFixed(1)}% on {off?.n_passages} held-out passages, {off?.seconds_per_passage}s each on a laptop.</p>
          </Glass>
          <Glass className="p-6">
            <div className="eyebrow">where the ${cost?.toFixed(2)} went</div>
            <div className="mt-4 space-y-1.5">
              {(E["tinker_cost.json"]?.jobs ?? []).map((j: any, i: number) => (
                <div key={i} className="flex justify-between gap-3 text-[12px]"><span className="truncate text-bone-dim">{j.job.replace("train:", "train · ").replace("eval:", "eval · ")}</span><span className="mono shrink-0 text-candle">${j.est_usd.toFixed(3)}</span></div>
              ))}
            </div>
          </Glass>
        </div>
        <Reveal><p className="mx-auto mt-8 max-w-3xl text-center text-[13.5px] leading-relaxed text-mute">
          Honest edges: the 95% task-A target was not reached on test ({(tA?.tuned?.field_exact_match * 100).toFixed(1)}%). Terminology citations (task C) regressed after tuning. The offline adapter is the 200-example sibling of the evaluated model, because Tinker sampler checkpoints cannot be downloaded. Investigation notes (task D) went from {(tD?.base?.all_checks * 100).toFixed(0)}% to {(tD?.tuned?.all_checks * 100).toFixed(0)}% passing every check.
        </p></Reveal>
      </div>
    </section>
  );
}

function Bench({ E }: { E: Record<string, any> }) {
  const [metric, setMetric] = useState<"auprc" | "f1" | "mcc">("auprc");
  const [set, setSet] = useState<"selected" | "base18">("selected");
  const rows: Row[] = useMemo(() => {
    const pub = parsePublished(E["ours_vs_published.md"]?.markdown ?? "");
    const ours = set === "selected"
      ? [...E["tabpfn_test_results.json"].models, ...E["baselines_test_results.json"].models.filter((m: any) => !m.model.startsWith("rule"))]
      : E["ablation_base18_test.json"].models;
    return [...ours.map((m: any) => ({ name: nice(m.model), auprc: m.auprc, f1: m.f1, mcc: m.mcc, kind: "ours" as const, hero: m.model.startsWith("tabpfn") })), ...pub]
      .sort((a, b) => b[metric] - a[metric]);
  }, [E, metric, set]);
  const lo = metric === "auprc" ? 0.3 : 0.0;
  return (
    <Reveal>
      <Glass className="mx-auto mt-14 max-w-[1300px] p-5 md:p-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><div className="eyebrow">against the published bar · official test split</div>
            <div className="display mt-2 text-3xl text-candle">{set === "selected" ? "Our selected features" : "Like-for-like: the paper's 18 features only"}</div></div>
          <div className="flex flex-wrap gap-1.5">
            {(["selected", "base18"] as const).map((s) => <button key={s} onClick={() => setSet(s)} className={`chip ${set === s ? "!border-marigold !text-marigold" : ""}`}>{s === "selected" ? "selected features" : "18 published features"}</button>)}
            <span className="w-3" />
            {(["auprc", "f1", "mcc"] as const).map((m) => <button key={m} onClick={() => setMetric(m)} className={`chip ${metric === m ? "!border-signal !text-signal" : ""}`}>{m}</button>)}
          </div>
        </div>
        <div className="mt-7 space-y-2">
          <AnimatePresence>
            {rows.map((r) => (
              <motion.div layout key={r.name} transition={{ layout: { duration: 0.7, ease } }} className="grid grid-cols-[9.5rem_1fr_3.5rem] items-center gap-3 md:grid-cols-[14rem_1fr_4rem]">
                <span className={`truncate text-[13px] ${r.hero ? "text-marigold" : r.kind === "published" ? "italic text-bone-dim" : "text-bone"}`}>{r.name}</span>
                <span className="relative h-6 overflow-hidden rounded-md bg-candle/[0.04]">
                  <motion.span className="absolute left-0 top-0 h-full rounded-md" initial={{ width: 0 }} animate={{ width: `${Math.max(0, (r[metric] - lo) / (1 - lo)) * 100}%` }} transition={{ duration: 1.1, ease }}
                    style={{ background: r.hero ? `linear-gradient(90deg, ${S1}55, ${S1})` : r.kind === "published" ? `repeating-linear-gradient(135deg, ${GRAY} 0 6px, #36323a 6px 12px)` : `linear-gradient(90deg, ${S2}33, ${S2}aa)`, boxShadow: r.hero ? `0 0 24px ${S1}88` : "none" }} />
                </span>
                <span className="mono text-right text-[13px] text-candle">{r[metric].toFixed(3)}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
        <div className="mono mt-5 flex flex-wrap gap-5 text-[10.5px] text-mute">
          <span><span className="mr-1.5 inline-block h-2 w-4 rounded-sm" style={{ background: S1 }} />TabPFN (ours)</span>
          <span><span className="mr-1.5 inline-block h-2 w-4 rounded-sm" style={{ background: S2 }} />baselines (ours, same split, same features)</span>
          <span><span className="mr-1.5 inline-block h-2 w-4 rounded-sm" style={{ background: `repeating-linear-gradient(135deg, ${GRAY} 0 3px, #36323a 3px 6px)` }} />published (Sci Data 2025, Table 3)</span>
          <span>axis starts at {lo}</span>
        </div>
      </Glass>
    </Reveal>
  );
}

function PRCurves({ E }: { E: Record<string, any> }) {
  const curves: Record<string, { precision: number; recall: number }[]> = E["pr_curve.json"]?.curves ?? {};
  const [hover, setHover] = useState<string | null>(null);
  const W = 520, H = 340, P = 40;
  const x = (r: number) => P + r * (W - P - 12), y = (p: number) => H - P - ((p - 0.3) / 0.7) * (H - P - 12);
  const colorOf = (m: string) => (m.startsWith("tabpfn") ? S1 : m.startsWith("rf") ? S2 : m.startsWith("xgboost") ? S3 : GRAY);
  const order = Object.keys(curves).sort((a) => (a.startsWith("tabpfn") ? 1 : -1));
  return (
    <Reveal>
      <Glass className="h-full p-5 md:p-6">
        <div className="eyebrow">precision–recall · test split</div>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full">
          {[0.4, 0.6, 0.8, 1].map((t) => <g key={t}><line x1={P} x2={W - 12} y1={y(t)} y2={y(t)} stroke="rgba(246,231,193,.06)" /><text x={P - 8} y={y(t)} fill="#7d766d" fontSize={10} textAnchor="end" dominantBaseline="middle" fontFamily="JetBrains Mono">{t}</text></g>)}
          {[0, 0.5, 1].map((t) => <text key={t} x={x(t)} y={H - P + 18} fill="#7d766d" fontSize={10} textAnchor="middle" fontFamily="JetBrains Mono">{t}</text>)}
          <text x={(W + P) / 2} y={H - 6} fill="#7d766d" fontSize={10} textAnchor="middle" fontFamily="JetBrains Mono">recall</text>
          {order.map((m) => {
            const pts = curves[m].filter((p) => p.precision >= 0.3);
            const d = pts.map((p, i) => `${i ? "L" : "M"}${x(p.recall).toFixed(1)},${y(p.precision).toFixed(1)}`).join(" ");
            const on = hover === null || hover === m;
            return <motion.path key={m} d={d} fill="none" stroke={colorOf(m)} strokeWidth={m.startsWith("tabpfn") ? 2.5 : 1.6} strokeOpacity={on ? 1 : 0.15}
              initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 2, ease }}
              onMouseEnter={() => setHover(m)} onMouseLeave={() => setHover(null)} style={{ cursor: "pointer" }} />;
          })}
        </svg>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {order.slice().reverse().map((m) => (
            <button key={m} onMouseEnter={() => setHover(m)} onMouseLeave={() => setHover(null)} className="mono text-[10.5px] text-bone-dim hover:text-candle">
              <span className="mr-1.5 inline-block h-[2px] w-4 align-middle" style={{ background: colorOf(m) }} />{nice(m)}
            </button>
          ))}
        </div>
      </Glass>
    </Reveal>
  );
}

function Threshold({ E }: { E: Record<string, any> }) {
  const rows = (E["threshold_tradeoff.csv"]?.rows ?? []).map((r: any) => ({ t: +r.threshold, missed: +r.missed_anomalies, fa: +r.false_alerts, p: +r.precision, r: +r.recall }));
  const th = E["thresholds.json"];
  const [i, setI] = useState(() => Math.max(0, rows.findIndex((r: any) => Math.abs(r.t - (th?.f1 ?? 0.5)) < 1e-3)));
  const cur = rows[i] ?? rows[0];
  if (!cur) return null;
  const maxV = Math.max(...rows.map((r: any) => Math.max(r.missed, r.fa)));
  return (
    <Reveal delay={0.1}>
      <Glass className="h-full p-5 md:p-6">
        <div className="eyebrow">the trade-off you choose · training out-of-fold</div>
        <div className="mt-5 grid grid-cols-2 gap-4">
          <div><div className="mono text-[10px] uppercase tracking-[0.2em] text-mute">missed anomalies</div><motion.div key={cur.missed} initial={{ y: -8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="display text-6xl font-light text-ember">{cur.missed}</motion.div></div>
          <div><div className="mono text-[10px] uppercase tracking-[0.2em] text-mute">false alerts</div><motion.div key={cur.fa} initial={{ y: -8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="display text-6xl font-light text-signal">{cur.fa}</motion.div></div>
        </div>
        <div className="mt-5 flex h-28 items-end gap-[3px]">
          {rows.map((r: any, k: number) => (
            <button key={k} onClick={() => setI(k)} className="group relative flex h-full flex-1 flex-col justify-end gap-[2px]">
              <span className="rounded-t-sm transition" style={{ height: `${(r.fa / maxV) * 50}%`, background: k === i ? S2 : "#7fb7be44" }} />
              <span className="rounded-b-sm transition" style={{ height: `${(r.missed / maxV) * 50}%`, background: k === i ? S3 : "#d2592b44" }} />
            </button>
          ))}
        </div>
        <input type="range" min={0} max={rows.length - 1} value={i} onChange={(e) => setI(+e.target.value)} className="mt-4" />
        <div className="mono mt-2 flex justify-between text-[11px] text-bone-dim">
          <span>threshold <span className="text-candle">{cur.t.toFixed(2)}</span></span>
          <span>precision <span className="text-candle">{cur.p.toFixed(3)}</span></span>
          <span>recall <span className="text-candle">{cur.r.toFixed(3)}</span></span>
        </div>
        <div className="mono mt-3 text-[10.5px] text-mute">console bands: queue ≥ {th?.low} · prioritise ≥ {th?.high} · headline metrics at max-F1 {th?.f1}</div>
      </Glass>
    </Reveal>
  );
}

function Calibration({ E }: { E: Record<string, any> }) {
  const c = E["calibration.json"]; if (!c) return null;
  const W = 360, H = 300, P = 36, x = (v: number) => P + v * (W - P - 10), y = (v: number) => H - P - v * (H - P - 10);
  return (
    <Reveal>
      <Glass className="h-full p-5 md:p-6">
        <div className="eyebrow">calibration · test split</div>
        <div className="mono mt-1 text-[11px] text-mute">Brier {c.brier.toFixed(4)} · the probability drives the queue, so it has to mean what it says</div>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full">
          <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke="rgba(246,231,193,.25)" strokeDasharray="4 5" />
          {[0, 0.5, 1].map((t) => <g key={t}><text x={x(t)} y={H - P + 16} fill="#7d766d" fontSize={10} textAnchor="middle" fontFamily="JetBrains Mono">{t}</text><text x={P - 8} y={y(t)} fill="#7d766d" fontSize={10} textAnchor="end" dominantBaseline="middle" fontFamily="JetBrains Mono">{t}</text></g>)}
          <motion.polyline fill="none" stroke={S1} strokeWidth={2} points={c.bins.map((b: any) => `${x(b.p_mean)},${y(b.frac_pos)}`).join(" ")} initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.6, ease }} />
          {c.bins.map((b: any, i: number) => <circle key={i} cx={x(b.p_mean)} cy={y(b.frac_pos)} r={5} fill={S1} stroke="#0b0a0d" strokeWidth={2} />)}
        </svg>
      </Glass>
    </Reveal>
  );
}

function Importance({ E }: { E: Record<string, any> }) {
  const f = (E["feature_importance.json"]?.features ?? []).slice(0, 10);
  const max = Math.max(...f.map((x: any) => x.importance), 1e-6);
  return (
    <Reveal delay={0.1}>
      <Glass className="h-full p-5 md:p-6">
        <div className="eyebrow">what TabPFN listens to · permutation importance</div>
        <div className="mono mt-1 text-[11px] text-mute">AUPRC drop when a feature is shuffled (held-out training fold)</div>
        <div className="mt-5 space-y-2.5">
          {f.map((x: any, i: number) => (
            <div key={x.feature} className="grid grid-cols-[10rem_1fr_3.5rem] items-center gap-3">
              <span className="mono truncate text-[11.5px] text-bone">{x.feature}</span>
              <span className="h-2.5 rounded-full bg-candle/[0.05]"><motion.span initial={{ width: 0 }} whileInView={{ width: `${Math.max(0, x.importance / max) * 100}%` }} viewport={{ once: true }} transition={{ delay: i * 0.06, duration: 1.1, ease }}
                className="block h-full rounded-full" style={{ background: `linear-gradient(90deg, ${S2}55, ${S2})` }} /></span>
              <span className="mono text-right text-[11px] text-mute">{x.importance.toFixed(3)}</span>
            </div>
          ))}
        </div>
      </Glass>
    </Reveal>
  );
}

function Dumbbell({ E }: { E: Record<string, any> }) {
  const tasks = [
    ["A", "Record extraction · field exact match", "field_exact_match"],
    ["B", "Timeline · event vs publication dates", "both_correct"],
    ["C", "Terminology · correct citation", "overall"],
    ["D", "Investigation note · all checks pass", "all_checks"],
  ] as const;
  return (
    <Reveal>
      <Glass className="h-full p-5 md:p-7">
        <div className="eyebrow">base Qwen3-8B → fine-tuned · held-out test documents</div>
        <div className="mono mt-1 text-[11px] text-mute">same prompt, same parser, same validator · paired exact McNemar test</div>
        <div className="mt-6 space-y-6">
          {tasks.map(([t, label, key]) => {
            const e = E[`tinker_eval_${t}.json`]; if (!e) return null;
            const b = e.base[key], u = e.tuned[key], better = u >= b;
            return (
              <div key={t}>
                <div className="flex flex-wrap justify-between gap-2 text-[13px]"><span className="text-bone"><span className="mono mr-2 text-marigold">{t}</span>{label}</span>
                  <span className="mono text-[11px] text-mute">p = {Number(e.paired.exact_p).toPrecision(2)}</span></div>
                <div className="relative mt-3 h-6">
                  <div className="absolute top-1/2 h-px w-full bg-candle/10" />
                  <motion.div className="absolute top-1/2 h-[3px] -translate-y-1/2 rounded" style={{ background: better ? S1 : S3, left: `${Math.min(b, u) * 100}%` }}
                    initial={{ width: 0 }} whileInView={{ width: `${Math.abs(u - b) * 100}%` }} viewport={{ once: true }} transition={{ duration: 1.3, ease }} />
                  <span className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-bone-dim bg-void" style={{ left: `${b * 100}%` }} />
                  <motion.span className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full" style={{ background: better ? S1 : S3, boxShadow: `0 0 18px ${better ? S1 : S3}` }}
                    initial={{ left: `${b * 100}%` }} whileInView={{ left: `${u * 100}%` }} viewport={{ once: true }} transition={{ duration: 1.3, ease }} />
                </div>
                <div className="mono mt-1 flex justify-between text-[11px]"><span className="text-mute">base {(b * 100).toFixed(1)}%</span><span className={better ? "text-marigold" : "text-ember"}>tuned {(u * 100).toFixed(1)}%{!better && " · regressed"}</span></div>
              </div>
            );
          })}
        </div>
      </Glass>
    </Reveal>
  );
}

function LearningCurve({ E }: { E: Record<string, any> }) {
  const lc = E["tinker_learning_curve.json"]; if (!lc) return null;
  const pts = lc.points.filter((p: any) => p.run.startsWith("lc-") || p.run === "final-v2").sort((a: any, b: any) => a.n_examples - b.n_examples);
  const W = 460, H = 300, P = 40, lo = 0.6;
  const x = (n: number) => P + (n / 460) * (W - P - 20), y = (v: number) => H - P - ((v - lo) / (1 - lo)) * (H - P - 14);
  const base = lc.base_model_val_exact_match_local;
  return (
    <Reveal delay={0.1}>
      <Glass className="h-full p-5 md:p-7">
        <div className="eyebrow">learning curve · validation · accuracy per dollar</div>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-4 w-full">
          {[0.7, 0.8, 0.9, 1].map((t) => <g key={t}><line x1={P} x2={W - 10} y1={y(t)} y2={y(t)} stroke="rgba(246,231,193,.06)" /><text x={P - 8} y={y(t)} fill="#7d766d" fontSize={10} textAnchor="end" dominantBaseline="middle" fontFamily="JetBrains Mono">{t}</text></g>)}
          <line x1={P} x2={W - 10} y1={y(0.95)} y2={y(0.95)} stroke={S3} strokeDasharray="3 4" /><text x={W - 12} y={y(0.95) - 6} fill={S3} fontSize={10} textAnchor="end" fontFamily="JetBrains Mono">95% target</text>
          {base && <><line x1={P} x2={W - 10} y1={y(base)} y2={y(base)} stroke="#7d766d" strokeDasharray="5 5" /><text x={P + 4} y={y(base) - 6} fill="#7d766d" fontSize={10} fontFamily="JetBrains Mono">base model {base.toFixed(3)}</text></>}
          <motion.polyline fill="none" stroke={S1} strokeWidth={2.2} points={pts.map((p: any) => `${x(p.n_examples)},${y(p.val_exact_match)}`).join(" ")} initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.8, ease }} />
          {pts.map((p: any) => (
            <g key={p.run}>
              <circle cx={x(p.n_examples)} cy={y(p.val_exact_match)} r={5.5} fill={S1} stroke="#0b0a0d" strokeWidth={2} />
              <text x={x(p.n_examples)} y={y(p.val_exact_match) + 20} fill="#ede6da" fontSize={10.5} textAnchor="middle" fontFamily="JetBrains Mono">{p.val_exact_match.toFixed(3)}</text>
              <text x={x(p.n_examples)} y={y(p.val_exact_match) + 33} fill="#7d766d" fontSize={9.5} textAnchor="middle" fontFamily="JetBrains Mono">${p.cost_usd.toFixed(3)}</text>
            </g>
          ))}
          {[50, 100, 200, 445].map((n) => <text key={n} x={x(n)} y={H - P + 18} fill="#7d766d" fontSize={10} textAnchor="middle" fontFamily="JetBrains Mono">{n}</text>)}
          <text x={(W + P) / 2} y={H - 4} fill="#7d766d" fontSize={10} textAnchor="middle" fontFamily="JetBrains Mono">training examples (3 epochs)</text>
        </svg>
        <div className="mono mt-1 text-[10.5px] text-mute">50/100/200 trained on spec-v1 labels, scored on v2 gold · 445 trained on v2</div>
      </Glass>
    </Reveal>
  );
}
