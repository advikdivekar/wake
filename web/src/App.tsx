import { lazy, Suspense, useEffect } from "react";
import Lenis from "lenis";
import { detectMode } from "./lib/api";
import { scrollState } from "./lib/scroll";
import Nav from "./sections/Nav";
import Hero from "./sections/Hero";
import Elegy from "./sections/Elegy";
import Observatory from "./sections/Observatory";
import Seance from "./sections/Seance";
import Queue from "./sections/Queue";
import Memory from "./sections/Memory";
import Lab from "./sections/Lab";
import Finale from "./sections/Finale";

const Scene = lazy(() => import("./three/Scene"));

export default function App() {
  useEffect(() => {
    detectMode();
    const lenis = new Lenis({ duration: 1.25, easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), smoothWheel: true });
    lenis.on("scroll", (e: any) => { scrollState.progress = e.progress ?? 0; scrollState.velocity = e.velocity ?? 0; });
    let raf = 0; const loop = (t: number) => { lenis.raf(t); raf = requestAnimationFrame(loop); }; raf = requestAnimationFrame(loop);
    const onClick = (e: MouseEvent) => {
      const a = (e.target as HTMLElement).closest("a[href^='#']") as HTMLAnchorElement | null;
      if (a) { e.preventDefault(); lenis.scrollTo(a.getAttribute("href")!, { offset: -70, duration: 1.8 }); }
    };
    document.addEventListener("click", onClick);
    return () => { cancelAnimationFrame(raf); lenis.destroy(); document.removeEventListener("click", onClick); };
  }, []);
  return (
    <div className="grain">
      <Suspense fallback={null}><Scene /></Suspense>
      <Nav />
      <main className="relative z-10">
        <Hero />
        <div className="relative bg-gradient-to-b from-transparent via-void/85 to-void/60">
          <Elegy />
          <Observatory />
          <Seance />
          <Queue />
          <Memory />
          <Lab />
        </div>
        <Finale />
      </main>
    </div>
  );
}
