"""Writes compositions/chaos.html and compositions/converge.html with the REAL OPS-SAT telemetry
paths embedded (assets/data/signals.json, exported from the live API: /channels/<ch>/telemetry and
/demo/204/steps). Re-run after editing the templates below: python3 build_data_scenes.py"""
import json, pathlib

ROOT = pathlib.Path(__file__).parent
S = json.loads((ROOT / "assets/data/signals.json").read_text())

FONTS = """
    @font-face { font-family: "Fraunces"; src: url("assets/fonts/fraunces.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
    @font-face { font-family: "Fraunces"; src: url("assets/fonts/fraunces-italic.woff2") format("woff2"); font-weight: 100 900; font-style: italic; }"""

# ---------------------------------------------------------------- chaos
colors = ["#7fb7be", "#7fb7be", "#7fb7be", "#f6e7c1", "#7fb7be", "#e8a33d", "#7fb7be", "#f6e7c1", "#7fb7be"]
paths = "\n".join(
    f'          <path id="chaos-tr{i}" d="{t["d"]}" stroke="{colors[i]}" />' for i, t in enumerate(S["traces"])
)
chaos = f"""<template>
  <style>{FONTS}
    #root {{ position: absolute; inset: 0; background: #050507; overflow: hidden; }}
    #chaos-field {{ position: absolute; left: 0; top: 0; width: 3840px; height: 1080px; }}
    #chaos-field svg {{ position: absolute; left: 0; top: 0; width: 3840px; height: 1080px; overflow: visible; }}
    #chaos-field path {{ fill: none; stroke-width: 2.2; stroke-linejoin: round; opacity: 0.55; }}
    #chaos-line {{ position: absolute; left: 0; top: 539px; width: 1920px; height: 3px; background: #f6e7c1; opacity: 0; }}
    .chaos-phrase {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; display: flex; align-items: center; justify-content: center; gap: 34px;
      font-family: "Fraunces", serif; font-weight: 300; font-size: 148px; letter-spacing: -0.02em; color: #f6e7c1; white-space: nowrap; }}
    .chaos-phrase .hl {{ background: #e8a33d; color: #050507; padding: 0 26px 10px; border-radius: 6px; font-weight: 400; }}
    .chaos-phrase em {{ font-style: italic; color: #e8a33d; }}
    .chaos-phrase span {{ display: inline-block; }}
    #chaos-shade {{ position: absolute; left: 0; top: 330px; width: 1920px; height: 420px;
      background: radial-gradient(ellipse 52% 50% at 50% 50%, rgba(5,5,7,0.92) 0%, rgba(5,5,7,0.75) 55%, rgba(5,5,7,0) 100%); }}
  </style>
  <div id="root" data-composition-id="chaos" data-width="1920" data-height="1080">
    <div id="chaos-field" data-layout-allow-overflow data-layout-ignore>
      <svg viewBox="0 0 3840 1080">
{paths}
      </svg>
    </div>
    <div id="chaos-line" data-layout-ignore></div>
    <div id="chaos-shade" data-layout-ignore></div>
    <div id="chaos-p1" class="chaos-phrase clip" data-start="0" data-duration="1.75" data-track-index="2"><span class="hl">2,123</span><span>signals.</span></div>
    <div id="chaos-p2" class="chaos-phrase clip" data-start="1.6" data-duration="1.75" data-track-index="3"><span class="hl">303,493</span><span>samples.</span></div>
    <div id="chaos-p3" class="chaos-phrase clip" data-start="3.2" data-duration="1.4" data-track-index="4"><span class="hl">nine</span><span>instruments.</span></div>
    <div id="chaos-p4" class="chaos-phrase clip" data-start="4.45" data-duration="1.0" data-track-index="5"><span>one</span><span><em>silent</em></span><span>satellite.</span></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    // telemetry scrolls at constant speed: the motion is the data arriving
    tl.fromTo("#chaos-field", {{ x: 0 }}, {{ x: -1500, duration: 6.2, ease: "none" }}, 0);
    // phrases: frame 0 already shows the first one (thumbnail); later ones blur in word by word
    const phraseIn = (id, t) => tl.fromTo(`${{id}} span`, {{ opacity: 0, filter: "blur(10px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.16, stagger: 0.067, ease: "power2.out" }}, t);
    const phraseOut = (id, t) => tl.to(`${{id}} span`, {{ opacity: 0, filter: "blur(10px)", duration: 0.14, stagger: 0.03, ease: "power2.in" }}, t);
    tl.fromTo("#chaos-p1 span", {{ opacity: 1 }}, {{ opacity: 1, duration: 0.01 }}, 0);
    phraseOut("#chaos-p1", 1.58);
    phraseIn("#chaos-p2", 1.62); phraseOut("#chaos-p2", 3.18);
    phraseIn("#chaos-p3", 3.22); phraseOut("#chaos-p3", 4.43);
    phraseIn("#chaos-p4", 4.47);
    // collapse: every channel folds into one line (the object becomes the next world)
    tl.to("#chaos-p4 span", {{ opacity: 0, filter: "blur(12px)", duration: 0.2, stagger: 0.04, ease: "power2.in" }}, 5.25);
    tl.to("#chaos-shade", {{ opacity: 0, duration: 0.3 }}, 5.2);
    tl.to("#chaos-field svg", {{ scaleY: 0.004, transformOrigin: "50% 540px", duration: 0.55, ease: "power3.in" }}, 5.35);
    tl.to("#chaos-field path", {{ opacity: 1, duration: 0.3 }}, 5.4);
    tl.fromTo("#chaos-line", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12 }}, 5.85);
    tl.to("#chaos-field", {{ opacity: 0, duration: 0.15 }}, 5.9);
    window.__timelines["chaos"] = tl;
  </script>
</template>
"""
(ROOT / "compositions/chaos.html").write_text(chaos)

# ---------------------------------------------------------------- converge
(zx0, zy0), (zx1, zy1) = S["zero"]
nodes = [  # every label is from the live API's /demo/204/steps response
    (1010, 215, "16 exact zeros", "measured"),
    (1090, 380, "2 prominent peaks", "measured"),
    (1130, 550, "largest jump: z +3.67", "measured"),
    (1090, 720, "OPSSAT-AD paper, §Data Records", "cited"),
    (1010, 885, "5 of 5 look-alikes: anomalous", "measured"),
]
bx, by = zx1, zy1
branches, labels = [], []
for i, (nx, ny, text, kind) in enumerate(nodes):
    branches.append(f'        <path id="conv-br{i}" class="conv-br" d="M{bx},{by} C{bx + 70},{by} {nx - 110},{ny} {nx},{ny}" />')
    tagc = "#e8a33d" if kind == "cited" else "#7fb7be"
    labels.append(
        f'    <div id="conv-n{i}" class="conv-node" style="left:{nx}px; top:{ny}px;" data-layout-allow-overflow>'
        f'<i class="conv-dot"></i><span class="conv-txt">{text}</span><span class="conv-tag" style="color:{tagc}; border-color:{tagc}">{kind}</span></div>'
    )
converge = f"""<template>
  <style>{FONTS}
    #root {{ position: absolute; inset: 0; background: #050507; overflow: hidden; }}
    #conv-svg {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; overflow: visible; }}
    #conv-wave {{ fill: none; stroke: #f6e7c1; stroke-width: 3.2; stroke-linejoin: round; }}
    #conv-zero {{ fill: none; stroke: #e8a33d; stroke-width: 9; stroke-linecap: round; }}
    .conv-br {{ fill: none; stroke: rgba(246,231,193,0.55); stroke-width: 2; }}
    #conv-meta {{ position: absolute; left: 110px; top: 150px; font-family: "JetBrains Mono", monospace; font-size: 28px; letter-spacing: 0.12em;
      text-transform: uppercase; color: #b9b1a4; }}
    #conv-meta b {{ color: #e8a33d; font-weight: 500; }}
    #conv-q {{ position: absolute; left: 110px; top: 820px; font-family: "Fraunces", serif; font-weight: 300; font-size: 64px; letter-spacing: -0.02em; color: #f6e7c1; }}
    #conv-q em {{ color: #e8a33d; }}
    .conv-node {{ position: absolute; display: flex; align-items: center; gap: 16px; transform: translate(-12px, -50%); white-space: nowrap; }}
    .conv-dot {{ width: 24px; height: 24px; border-radius: 50%; background: #050507; border: 3px solid #f6e7c1; flex: none; }}
    .conv-txt {{ font-family: "Inter", sans-serif; font-size: 32px; color: #ede6da; }}
    .conv-tag {{ font-family: "JetBrains Mono", monospace; font-size: 28px; letter-spacing: 0.1em; text-transform: uppercase; border: 1.5px solid; border-radius: 999px; padding: 4px 12px; }}
    #conv-pulse {{ position: absolute; left: 0; top: 0; width: 22px; height: 22px; margin: -11px 0 0 -11px; border-radius: 50%; background: #e8a33d; }}
  </style>
  <div id="root" data-composition-id="converge" data-width="1920" data-height="1080">
    <svg id="conv-svg" viewBox="0 0 1920 1080" data-layout-ignore>
      <path id="conv-wave" d="{S['seg']}" />
      <path id="conv-zero" d="M{zx0},{zy0} L{zx1},{zy1}" />
{chr(10).join(branches)}
    </svg>
    <div id="conv-meta">segment <b>#204</b> · CADC0872 · magnetometer · 2022-06-02 · label hidden</div>
    <div id="conv-q">Is this one <em>wrong?</em></div>
{chr(10).join(labels)}
    <div id="conv-pulse" data-layout-ignore></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    const wave = document.querySelector("#conv-wave");
    const L = wave.getTotalLength();
    tl.fromTo(wave, {{ strokeDasharray: L, strokeDashoffset: L }}, {{ strokeDashoffset: 0, duration: 1.5, ease: "power2.inOut" }}, 0);
    tl.fromTo("#conv-meta", {{ opacity: 0, filter: "blur(8px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.2, ease: "power2.out" }}, 0.15);
    tl.fromTo("#conv-q", {{ opacity: 0, filter: "blur(8px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.2, ease: "power2.out" }}, 0.9);
    // a pulse runs the real waveform and stops on the zero run
    const proxy = {{ p: 0 }};
    const zeroFrac = {zx1 - S['seg_x'][0]} / {S['seg_x'][1] - S['seg_x'][0]};
    const place = () => {{ const pt = wave.getPointAtLength(L * proxy.p); gsap.set("#conv-pulse", {{ x: pt.x, y: pt.y }}); }};
    tl.fromTo("#conv-pulse", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.1 }}, 0.2);
    tl.fromTo(proxy, {{ p: 0 }}, {{ p: zeroFrac, duration: 1.45, ease: "power2.inOut", onUpdate: place }}, 0.2);
    tl.fromTo("#conv-zero", {{ opacity: 0, strokeWidth: 3 }}, {{ opacity: 1, strokeWidth: 9, duration: 0.25, ease: "expo.out" }}, 1.6);
    tl.to("#conv-q", {{ opacity: 0, filter: "blur(8px)", duration: 0.18 }}, 3.95);
    // five branches: what the engine measured and what the archive says
    document.querySelectorAll(".conv-br").forEach((b, i) => {{
      const l = b.getTotalLength();
      tl.fromTo(b, {{ strokeDasharray: l, strokeDashoffset: l }}, {{ strokeDashoffset: 0, duration: 0.45, ease: "power3.out" }}, 1.55 + i * 0.12);
      tl.fromTo(`#conv-n${{i}} .conv-dot`, {{ scale: 0 }}, {{ scale: 1, duration: 0.35, ease: "back.out(2)" }}, 1.85 + i * 0.12);
      tl.fromTo(`#conv-n${{i}} .conv-txt, #conv-n${{i}} .conv-tag`, {{ opacity: 0, filter: "blur(6px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.16, stagger: 0.07, ease: "power2.out" }}, 1.9 + i * 0.12);
      // retract into the zero run
      tl.to(`#conv-n${{i}}`, {{ opacity: 0, filter: "blur(8px)", duration: 0.18 }}, 4.2 + i * 0.03);
      tl.to(b, {{ strokeDashoffset: l, duration: 0.35, ease: "power3.in" }}, 4.25 + i * 0.03);
    }});
    tl.to("#conv-wave, #conv-meta", {{ opacity: 0, duration: 0.2 }}, 4.3);
    tl.to("#conv-zero", {{ opacity: 0, duration: 0.15 }}, 4.4);
    // the pulse carries the segment to the centre: it becomes the ring
    tl.to("#conv-pulse", {{ x: 960, y: 540, scale: 1.6, duration: 0.36, ease: "power3.inOut" }}, 4.42);
    window.__timelines["converge"] = tl;
  </script>
</template>
"""
(ROOT / "compositions/converge.html").write_text(converge)
print("wrote chaos.html, converge.html")
