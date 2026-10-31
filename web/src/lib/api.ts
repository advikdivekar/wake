// Data layer: talks to the live FastAPI backend if reachable, otherwise reads the archived snapshot of
// REAL API responses shipped in /snapshot (exported by scripts/export_snapshot.py). The UI always says which.
const API = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";
const SNAP = `${import.meta.env.BASE_URL}snapshot`;

export type Mode = "live" | "snapshot";
let mode: Mode | null = null;
const listeners = new Set<(m: Mode) => void>();

let probing: Promise<Mode> | null = null;
export function detectMode(): Promise<Mode> {
  if (mode) return Promise.resolve(mode);
  if (!probing) probing = probe();
  return probing;
}
async function probe(): Promise<Mode> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 1200);
    const r = await fetch(`${API}/health`, { signal: ctrl.signal });
    clearTimeout(t);
    mode = r.ok ? "live" : "snapshot";
  } catch {
    mode = "snapshot";
  }
  listeners.forEach((l) => l(mode!));
  return mode;
}
export const onMode = (fn: (m: Mode) => void) => { listeners.add(fn); return () => { listeners.delete(fn); }; };
export const getMode = () => mode;

const cache = new Map<string, Promise<unknown>>();
async function snap<T>(name: string): Promise<T> {
  if (!cache.has(name)) cache.set(name, fetch(`${SNAP}/${name}.json`).then((r) => { if (!r.ok) throw new Error(`snapshot ${name} missing`); return r.json(); }));
  return cache.get(name) as Promise<T>;
}
async function live<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, { headers: { "content-type": "application/json" }, ...init });
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json();
}

// ---- types (mirror app/api/schemas.py) ---------------------------------------------------
export interface Citation { doc_id: string; chunk_id: string | null; title: string; url?: string; location?: string; excerpt: string; score?: number; license?: string; }
export interface Segment { segment_id: number; channel: string; channel_name: string; channel_kind: string; split: string; sampling: number; n_points: number; start: string; end: string; label: number | null; probability?: number; decision?: string; review_status?: string; }
export interface Series { segment_id: number | null; t: string[]; v: number[]; gaps: { start: string; end: string; seconds: number }[]; zero_runs: { start_idx: number; end_idx: number }[]; peaks_idx: number[]; segments?: { segment_id: number; start: string; end: string; split: string }[]; downsampled?: boolean; }
export interface Contributor { feature: string; value: number; z: number; importance: number; plain: string; }
export interface Prediction { segment_id: number | null; probability: number; decision: "prioritise" | "queue" | "archive"; thresholds: { high: number; low: number }; model: string; contributors: Contributor[]; }
export interface Similar { segment_id: number; distance: number; label: number; channel: string; note: string; }
export interface Known { statement: string; basis: "measured" | "cited"; citations: Citation[]; }
export interface Card { card_id: string; segment_id: number; created_at: string; prediction: Prediction; signal_evidence: Record<string, number | boolean>; historical_context: Similar[]; documents: Citation[]; known: Known[]; unknown: string[]; suggested_action: string; summary: string; summary_model: string; review_status: string; ground_truth: number | null; }
export interface DemoSteps { segment: Segment; series: Series; features: { features: Record<string, number | string>; published_18: string[]; extras: string[] }; prediction: Prediction; citations: Citation[]; similar: Similar[]; card: Card; }
export interface Reveal { segment_id: number; label: number; case: "TP" | "TN" | "FP" | "FN"; predicted: number; probability: number; threshold: number; }
export interface AskAnswer { question: string; answer: string; citations: Citation[]; missing: string[]; model: string; }
export interface TimelineItem { date: string; date_kind: "event" | "publication"; approx: string | null; title: string; citation: Citation | null; measured: string | null; }
export interface Channel { channel: string; channel_name: string; kind: string; n_segments: number; anomaly_rate_train: number; }
export interface Doc { doc_id: string; title: string; url: string; license: string; category: string; stored_mode: string; publication_date: string; n_chunks: number; }

// ---- endpoints -------------------------------------------------------------------------------
const m = async () => (await detectMode()) === "live";
export const api = {
  mission: async () => ((await m()) ? live<any>("/mission") : snap<any>("mission")),
  channels: async () => ((await m()) ? live<Channel[]>("/channels") : snap<Channel[]>("channels")),
  timeline: async () => ((await m()) ? live<TimelineItem[]>("/memory/timeline") : snap<TimelineItem[]>("timeline")),
  documents: async () => ((await m()) ? live<Doc[]>("/documents") : snap<Doc[]>("documents")),
  telemetry: async (ch: string) => ((await m()) ? live<Series>(`/channels/${ch}/telemetry?max_points=2500`) : snap<Series>(`telemetry/${ch}`)),
  queue: async () => ((await m()) ? live<Segment[]>("/segments?split=test&sort=probability&limit=600") : snap<Segment[]>("segments_test")),
  demo: async () => ((await m()) ? live<{ segment_id: number; blurb: string }[]>("/demo") : snap<{ segment_id: number; blurb: string }[]>("demo")),
  demoSteps: async (id: number) => ((await m()) ? live<DemoSteps>(`/demo/${id}/steps`) : snap<DemoSteps>(`demo/${id}_steps`)),
  demoReveal: async (id: number) => ((await m()) ? live<Reveal>(`/demo/${id}/reveal`) : snap<Reveal>(`demo/${id}_reveal`)),
  segment: async (id: number) => ((await m()) ? live<{ segment: Segment; series: Series }>(`/segments/${id}`) : snap<{ segment: Segment; series: Series }>(`segment/${id}`)),
  investigate: async (id: number) => ((await m()) ? live<Card>("/investigations", { method: "POST", body: JSON.stringify({ segment_id: id, use_lm: true }) }) : snap<Card>(`card/${id}`)),
  feedback: async (card: Card, action: "confirm" | "reject" | "investigate", note = "") => {
    if (await m()) return live<Card>(`/investigations/${card.card_id}/feedback`, { method: "POST", body: JSON.stringify({ action, note }) });
    const status = { confirm: "confirmed", reject: "rejected", investigate: "investigating" }[action];
    try { localStorage.setItem(`fb:${card.segment_id}`, status); } catch { /* storage unavailable */ }
    return { ...card, review_status: status };
  },
  ask: async (q: string): Promise<AskAnswer> => {
    if (await m()) return live<AskAnswer>("/memory/ask", { method: "POST", body: JSON.stringify({ question: q, k: 6 }) });
    const all = await snap<AskAnswer[]>("ask");
    return all.find((a) => a.question === q) ?? { question: q, answer: "This archived snapshot only holds the suggested questions. Run the backend (make api) to ask anything.", citations: [], missing: ["Live archive search is unavailable in the static snapshot."], model: "snapshot" };
  },
  askSuggestions: async () => (await snap<AskAnswer[]>("ask")).map((a) => a.question),
  extract: async (text: string) => {
    if (await m()) return live<any>("/memory/extract", { method: "POST", body: JSON.stringify({ text }) });
    const all = await snap<{ text: string; record: any }[]>("extract");
    return all.find((e) => e.text === text)?.record ?? null;
  },
  extractExamples: async () => (await snap<{ text: string; record: any }[]>("extract")).map((e) => e.text),
  evaluations: async (): Promise<Record<string, any>> => {
    if (await m()) {
      const idx = await live<{ name: string }[]>("/evaluations");
      const out: Record<string, any> = {};
      await Promise.all(idx.filter((i) => /\.(json|csv|md)$/.test(i.name)).map(async (i) => { out[i.name] = await live(`/evaluations/${i.name}`); }));
      return out;
    }
    return snap<Record<string, any>>("evaluations");
  },
  exportUrl: () => `${API}/export`,
};
