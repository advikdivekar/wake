import { useEffect, useRef } from "react";
import { api, getMode } from "../lib/api";
import { Reveal, SplitWords } from "../components/ui";

// Ofrenda finale: marigold petals drifting through candlelight (canvas, pauses off-screen).
function Petals() {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current!, ctx = cv.getContext("2d")!;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let W = 0, H = 0, raf = 0, visible = false;
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const resize = () => { W = cv.clientWidth; H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); };
    resize();
    const P = Array.from({ length: 90 }, () => ({ x: Math.random(), y: Math.random(), r: 3 + Math.random() * 6, s: 0.15 + Math.random() * 0.45, a: Math.random() * 6.28, w: 0.5 + Math.random() * 1.5, hue: Math.random() }));
    const frame = () => {
      ctx.clearRect(0, 0, W, H);
      for (const p of P) {
        p.y += p.s / H * 2.2; p.a += 0.01 * p.w; p.x += Math.sin(p.a) * 0.0006;
        if (p.y > 1.05) { p.y = -0.05; p.x = Math.random(); }
        const x = p.x * W, y = p.y * H;
        ctx.save(); ctx.translate(x, y); ctx.rotate(p.a);
        ctx.fillStyle = p.hue < 0.7 ? `rgba(232,163,61,${0.55 + p.hue * 0.3})` : `rgba(210,89,43,0.7)`;
        ctx.shadowColor = "rgba(232,163,61,.8)"; ctx.shadowBlur = 10;
        ctx.beginPath(); ctx.ellipse(0, 0, p.r, p.r * 0.55, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      }
      if (visible && !reduce) raf = requestAnimationFrame(frame);
    };
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; cancelAnimationFrame(raf); if (visible) frame(); });
    io.observe(cv); window.addEventListener("resize", resize);
    if (reduce) frame();
    return () => { io.disconnect(); cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, []);
  return <canvas ref={ref} className="pointer-events-none absolute inset-0 h-full w-full" />;
}

export default function Finale() {
  const live = getMode() === "live";
  return (
    <section id="finale" className="relative overflow-hidden px-5 pb-16 pt-40 md:px-10">
      <Petals />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-2/3 bg-gradient-to-t from-marigold/10 via-ember/5 to-transparent" />
      <div className="relative mx-auto max-w-4xl text-center">
        <div className="pointer-events-none absolute -inset-x-24 -inset-y-16 -z-10 rounded-[50%] bg-void/55 blur-3xl" />
        <div className="eyebrow mb-8">vii · ofrenda</div>
        <h2 className="display text-[clamp(2.6rem,7vw,6.5rem)] font-[250] leading-[0.95] text-candle">
          <SplitWords text="Its mission ended." /><br /><span className="italic text-marigold candle-glow"><SplitWords text="Its memories did not." delay={0.4} /></span>
        </h2>
        <Reveal delay={0.6}>
          <p className="mx-auto mt-10 max-w-2xl text-[15px] leading-relaxed text-bone-dim">
            Take the archive with you: documents (where licences allow), extracted records, investigation cards, analyst feedback, predictions and every evaluation file, bundled with a manifest.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {live ? <a href={api.exportUrl()} className="btn btn-primary">Export the mission memory archive</a>
              : <span className="btn btn-ghost cursor-not-allowed opacity-70" title="Run the backend (make api) to export">Export needs the live backend (make api)</span>}
            <a href="https://github.com/advikdivekar/the-last-satellite" className="btn btn-ghost" target="_blank" rel="noreferrer">Source on GitHub</a>
          </div>
        </Reveal>
      </div>
      <footer className="relative mx-auto mt-32 max-w-[1300px] rounded-2xl border border-candle/10 bg-void/80 p-6 text-[12px] leading-relaxed text-mute backdrop-blur-md">
        <div className="grid gap-6 md:grid-cols-3">
          <p>Archival analysis of the public <a className="text-bone-dim hover:text-marigold" href="https://doi.org/10.5281/zenodo.12588359">OPSSAT-AD</a> dataset (CC-BY-4.0; code MIT). OPS-SAT re-entered on 22 May 2024. Nothing here is live telemetry.</p>
          <p>Telemetry analyser: TabPFN v2 weights (Prior Labs License, Apache-2.0 + attribution). <em>Built with TabPFN.</em> Interpreter: Qwen3-8B (Apache-2.0) + LoRA trained on Tinker's hosted service; inference runs locally.</p>
          <p>Earth: NASA Blue Marble / Black Marble; cloud and specular maps from the three.js examples (MIT). Root causes are shown only when a source states them. Otherwise: unknown.</p>
        </div>
      </footer>
    </section>
  );
}
