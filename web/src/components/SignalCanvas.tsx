import { useEffect, useRef, useState } from "react";
import type { Series } from "../lib/api";

// Oscilloscope-style renderer for archived telemetry: glowing trace, ember zero-runs, dashed gap voids,
// animated draw-in, hover readout. Values are drawn exactly as recorded (no smoothing).
export default function SignalCanvas({ series, height = 260, animateKey, accent = "#7fb7be", segmentBands = false }:
  { series: Series | null; height?: number; animateKey?: string | number; accent?: string; segmentBands?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<{ x: number; i: number } | null>(null);
  const prog = useRef(0);
  const times = useRef<number[]>([]);

  useEffect(() => {
    if (!series || !ref.current || !wrap.current) return;
    const cv = ref.current, ctx = cv.getContext("2d")!;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0; prog.current = 0;
    const v = series.v, n = v.length;
    times.current = series.t.map((t) => Date.parse(t));
    const lo = Math.min(...v), hi = Math.max(...v), pad = (hi - lo || 1) * 0.12;
    const draw = () => {
      const W = wrap.current!.clientWidth, H = height;
      cv.width = W * dpr; cv.height = H * dpr; cv.style.width = W + "px"; cv.style.height = H + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      const X = (i: number) => 8 + (i / Math.max(n - 1, 1)) * (W - 16);
      const Y = (y: number) => H - 14 - ((y - lo + pad) / (hi - lo + 2 * pad)) * (H - 28);
      // grid
      ctx.strokeStyle = "rgba(246,231,193,0.05)"; ctx.lineWidth = 1;
      for (let g = 1; g < 6; g++) { const yy = (H / 6) * g; ctx.beginPath(); ctx.moveTo(0, yy); ctx.lineTo(W, yy); ctx.stroke(); }
      for (let g = 1; g < 12; g++) { const xx = (W / 12) * g; ctx.beginPath(); ctx.moveTo(xx, 0); ctx.lineTo(xx, H); ctx.stroke(); }
      // zero line
      if (lo < 0 && hi > 0) { ctx.strokeStyle = "rgba(246,231,193,0.12)"; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(W, Y(0)); ctx.stroke(); ctx.setLineDash([]); }
      // segment bands (channel view)
      if (segmentBands && series.segments && n > 1) {
        // bands are placed by sample index (same axis as the trace), via binary search on timestamps
        const ts = times.current;
        const idx = (iso: string) => { const q = Date.parse(iso); let lo = 0, hi = n - 1; while (lo < hi) { const m = (lo + hi) >> 1; ts[m] < q ? (lo = m + 1) : (hi = m); } return lo; };
        series.segments.forEach((s, k) => {
          const a = X(idx(s.start)), b = X(idx(s.end));
          ctx.fillStyle = k % 2 ? "rgba(246,231,193,0.018)" : "rgba(246,231,193,0.035)"; ctx.fillRect(a, 0, Math.max(b - a, 1), H);
        });
      }
      // zero runs
      series.zero_runs.forEach((z) => {
        const a = X(z.start_idx), b = X(z.end_idx);
        const g = ctx.createLinearGradient(0, 0, 0, H); g.addColorStop(0, "rgba(210,89,43,0.0)"); g.addColorStop(0.5, "rgba(210,89,43,0.28)"); g.addColorStop(1, "rgba(210,89,43,0.0)");
        ctx.fillStyle = g; ctx.fillRect(a - 2, 0, Math.max(b - a + 4, 3), H);
      });
      // gaps
      const tIndex = new Map(series.t.map((t, i) => [t, i]));
      (series.downsampled ? [] : series.gaps).forEach((gp) => {
        const i = tIndex.get(gp.end); if (i === undefined) return;
        const a = X(i - 1), b = X(i);
        ctx.fillStyle = "rgba(5,5,7,0.65)"; ctx.fillRect(a, 0, Math.max(b - a, 2), H);
        ctx.strokeStyle = "rgba(246,231,193,0.35)"; ctx.setLineDash([3, 4]);
        ctx.beginPath(); ctx.moveTo(a, 0); ctx.lineTo(a, H); ctx.moveTo(b, 0); ctx.lineTo(b, H); ctx.stroke(); ctx.setLineDash([]);
      });
      // trace (animated reveal)
      const upto = Math.max(2, Math.floor(n * prog.current));
      for (const [w, a] of [[7, 0.08], [3.5, 0.18], [1.4, 1]] as const) {
        ctx.strokeStyle = accent; ctx.globalAlpha = a; ctx.lineWidth = w; ctx.lineJoin = "round"; ctx.beginPath();
        for (let i = 0; i < upto; i++) { const x = X(i), y = Y(v[i]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      // peaks
      series.peaks_idx.forEach((i) => { if (i < upto) { ctx.fillStyle = "#f6e7c1"; ctx.beginPath(); ctx.arc(X(i), Y(v[i]), 2.6, 0, Math.PI * 2); ctx.fill(); } });
      // write head
      if (prog.current < 1) { const x = X(upto - 1), y = Y(v[upto - 1]); ctx.fillStyle = "#fff"; ctx.shadowColor = accent; ctx.shadowBlur = 18; ctx.beginPath(); ctx.arc(x, y, 3.2, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0; }
    };
    const tick = () => { prog.current = Math.min(1, prog.current + 0.012 + (1 - prog.current) * 0.03); draw(); if (prog.current < 1) raf = requestAnimationFrame(tick); };
    tick();
    const ro = new ResizeObserver(draw); ro.observe(wrap.current);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, [series, animateKey, height, accent, segmentBands]);

  const onMove = (e: React.MouseEvent) => {
    if (!series || !wrap.current) return;
    const r = wrap.current.getBoundingClientRect(); const x = e.clientX - r.left;
    const i = Math.round(((x - 8) / (r.width - 16)) * (series.v.length - 1));
    if (i >= 0 && i < series.v.length) setHover({ x, i }); else setHover(null);
  };
  return (
    <div ref={wrap} className="relative w-full cursor-crosshair" style={{ height }} onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <canvas ref={ref} className="block" />
      {hover && series && (
        <>
          <div className="pointer-events-none absolute top-0 h-full w-px bg-candle/30" style={{ left: hover.x }} />
          <div className="mono pointer-events-none absolute top-2 z-10 rounded-md border border-line bg-void/90 px-2.5 py-1.5 text-[11px] text-bone"
            style={{ left: Math.min(hover.x + 10, (wrap.current?.clientWidth ?? 300) - 190) }}>
            <div className="text-mute">{series.t[hover.i]?.replace("T", " ").replace(".000Z", "Z")}</div>
            <div>value <span className="text-candle">{series.v[hover.i]?.toExponential(3)}</span></div>
          </div>
        </>
      )}
      {!series && <div className="mono absolute inset-0 grid place-items-center text-xs text-mute">receiving archived transmission…</div>}
    </div>
  );
}
