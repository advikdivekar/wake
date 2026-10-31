"""Writes the screen-recording scenes (hero, hide, miss, queue, lab, memory, finale) from one table.

Every shot is a real take of the live console (web/record_demo.mjs → assets/clips/*.mp4, 2560×1440,
recorded at 1600×900 CSS px). The cursor clicks where the recorder clicked: assets/data/clicks_*.json
gives CSS px and seconds; ×1.2 maps CSS px to the 1920×1080 frame.
Re-run after editing: python3 build_clip_scenes.py
"""
import json, pathlib

ROOT = pathlib.Path(__file__).parent
K = 1.2  # CSS px (1600×900) → frame px (1920×1080)


def clicks(take):
    return {c["label"].replace(" ", ""): c for c in json.loads((ROOT / f"assets/data/clicks_{take}.json").read_text())}


def at(take, label, mstart, shot_start):
    """(local time, frame x, frame y) of a recorded click inside a shot."""
    c = clicks(take)[label]
    return (round(shot_start + c["t"] - mstart, 3), round(c["x"] * K, 1), round(c["y"] * K, 1))


FONTS = """
    @font-face { font-family: "Fraunces"; src: url("assets/fonts/fraunces.woff2") format("woff2"); font-weight: 100 900; font-style: normal; }
    @font-face { font-family: "Fraunces"; src: url("assets/fonts/fraunces-italic.woff2") format("woff2"); font-weight: 100 900; font-style: italic; }"""

CURSOR_SVG = (
    '<svg width="56" height="56" viewBox="0 0 28 28"><path d="M3 2 L3 22 L8.6 17.2 L12.4 25.4 L16 23.8 L12.3 15.8 L19.6 15.6 Z" '
    'fill="#ede6da" stroke="#050507" stroke-width="1.6" stroke-linejoin="round"/></svg>'
)

# ------------------------------------------------------------------------------------------------
# scene table. cam keys: (t, scale, focus_x, focus_y, dur) — dur 0 means "set" at t.
# type cards: (start, dur, html, style) with style in words | letters | grey
S204, S1579, Q, MEM, LAB = "reveal_204", "seance_1579", "queue", "memory", "lab"
SCENES = {
    "hero": {
        "dur": 4.4,
        "shots": [{"clip": "hero", "start": 0, "dur": 4.4, "mstart": 0.7, "cam": [(0, 1.0, 960, 540, 0), (2.2, 1.25, 700, 420, 0.5)]}],
        "dip": 4.27,
    },
    "hide": {
        "dur": 8.2,
        "type": [(0, 1.3, "Hide the *label.*", "words")],
        "shots": [
            {"clip": S204, "start": 1.3, "dur": 1.7, "mstart": 0.6, "cam": [(1.3, 1.25, 760, 430, 0)],
             "cursor": {"from": (980, 760), "clicks": [at(S204, "candle0", 0.6, 1.3)]}},
            {"clip": S204, "start": 3.0, "dur": 2.8, "mstart": 10.8, "cam": [(3.0, 1.0, 960, 540, 0), (3.45, 1.9, 1396, 380, 0.55)]},
            {"clip": S204, "start": 5.8, "dur": 2.4, "mstart": 13.6, "cam": [(5.8, 1.5, 1394, 760, 0), (6.55, 2.1, 1394, 905, 0.5)],
             "cursor": {"from": (1640, 1020), "clicks": [at(S204, "Revealthetruth", 13.6, 5.8)]}},
        ],
    },
    "miss": {
        "dur": 4.4,
        "type": [(0, 1.8, "The one it !missed.!", "grey")],
        "shots": [
            {"clip": S1579, "start": 1.8, "dur": 2.6, "mstart": 11.9, "cam": [(1.8, 1.6, 1394, 640, 0), (3.0, 2.1, 1394, 890, 0.5)],
             "cursor": {"from": (1660, 1010), "clicks": [at(S1579, "Revealthetruth", 11.9, 1.8)]}, "whip_out": 4.22},
        ],
    },
    "queue": {
        "dur": 4.8,
        "shots": [
            {"clip": Q, "start": 0, "dur": 2.2, "mstart": 2.0, "cam": [(0, 1.0, 960, 540, 0), (0.75, 1.35, 960, 640, 0.5)],
             "cursor": {"from": (1040, 600), "clicks": [at(Q, "queuerow#204", 2.0, 0)]}, "whip_in": 0},
            {"clip": Q, "start": 2.2, "dur": 2.6, "mstart": 13.7, "cam": [(2.2, 1.0, 960, 540, 0), (2.75, 1.9, 1150, 700, 0.55)]},
        ],
    },
    "lab": {
        "dur": 2.8,
        "shots": [{"clip": LAB, "start": 0, "dur": 2.8, "mstart": 9.1, "cam": [(0, 1.0, 960, 540, 0), (0.6, 1.35, 960, 700, 0.6)]}],
    },
    "memory": {
        "dur": 4.6,
        "type": [(0, 1.2, "Ask the *archive.*", "letters")],
        "shots": [
            {"clip": MEM, "start": 1.2, "dur": 1.5, "mstart": 2.4, "cam": [(1.2, 1.7, 700, 170, 0)]},
            {"clip": MEM, "start": 2.7, "dur": 1.9, "mstart": 7.6, "cam": [(2.7, 1.3, 960, 420, 0), (3.35, 1.9, 1350, 260, 0.55)]},
        ],
    },
    "obs": {
        "dur": 2.6,
        "shots": [{"clip": "observatory", "start": 0, "dur": 2.6, "mstart": 1.4, "cam": [(0, 1.15, 960, 640, 0)],
                   "cursor": {"from": (1200, 820), "clicks": [at("observatory", "I_PD3_THETA", 1.4, 0)]}}],
    },
    "finale": {
        "dur": 2.4,
        "shots": [{"clip": "finale", "start": 0, "dur": 2.4, "mstart": 0.6, "cam": [(0, 1.0, 960, 540, 0)]}],
        "dip": 2.25,
    },
}


def cam_xy(s, fx, fy):
    x = min(0, max(1920 - 1920 * s, 960 - fx * s))
    y = min(0, max(1080 - 1080 * s, 540 - fy * s))
    return round(x, 1), round(y, 1)


def build(name, sc):
    p = name[:3]
    markup, js = [], []
    z = 1
    for i, sh in enumerate(sc["shots"]):
        cid = f"{p}-cam{i}"
        vid = f"{p}-v{i}"
        cur = f"{p}-cur{i}"
        inner = (f'      <video id="{vid}" class="clip shot-video" data-start="{sh["start"]}" data-duration="{sh["dur"]}" '
                 f'data-media-start="{sh["mstart"]}" data-track-index="{i + 1}" src="assets/clips/{sh["clip"]}.mp4" muted playsinline></video>')
        if "cursor" in sh:
            inner += (f'\n      <div id="{cur}" class="clip cursor" data-start="{sh["start"]}" data-duration="{sh["dur"]}" data-track-index="{i + 10}">'
                      f'<div class="cursor-in">{CURSOR_SVG}</div></div>')
        markup.append(f'    <div id="{cid}" class="cam" style="z-index:{z}" data-layout-allow-overflow>\n{inner}\n    </div>')
        z += 1
        # camera
        for (t, s, fx, fy, d) in sh["cam"]:
            x, y = cam_xy(s, fx, fy)
            if d == 0:
                js.append(f'    tl.set("#{cid}", {{ scale: {s}, x: {x}, y: {y} }}, {t});')
                if "cursor" in sh:
                    js.append(f'    tl.set("#{cur} .cursor-in", {{ scale: {round(1 / s, 4)} }}, {t});')
            else:
                js.append(f'    tl.to("#{cid}", {{ scale: {s}, x: {x}, y: {y}, duration: {d}, ease: "power3.inOut" }}, {t});')
                if "cursor" in sh:
                    js.append(f'    tl.to("#{cur} .cursor-in", {{ scale: {round(1 / s, 4)}, duration: {d}, ease: "power3.inOut" }}, {t});')
        if sh.get("whip_in") is not None:
            t = sh["whip_in"]
            js.append(f'    tl.fromTo("#{vid}", {{ filter: "blur(16px)", x: 260 }}, {{ filter: "blur(0px)", x: 0, duration: 0.22, ease: "power3.out" }}, {t});')
        if sh.get("whip_out") is not None:
            t = sh["whip_out"]
            js.append(f'    tl.to("#{vid}", {{ filter: "blur(16px)", x: -260, duration: 0.18, ease: "power3.in" }}, {t});')
        # cursor: glide to each recorded click, press on the click's frame
        if "cursor" in sh:
            fx, fy = sh["cursor"]["from"]
            js.append(f'    tl.set("#{cur}", {{ x: {fx}, y: {fy} }}, {sh["start"]});')
            js.append(f'    tl.fromTo("#{cur} .cursor-in", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12 }}, {sh["start"]});')
            for (t, x, y) in sh["cursor"]["clicks"]:
                move = max(0.22, min(0.55, t - sh["start"] - 0.08))
                js.append(f'    tl.to("#{cur}", {{ x: {x}, y: {y}, duration: {move}, ease: "power2.inOut" }}, {round(t - move - 0.06, 3)});')
                js.append(f'    tl.to("#{cur} svg", {{ scale: 0.8, duration: 0.07, ease: "power2.in", transformOrigin: "6px 4px" }}, {round(t - 0.04, 3)});')
                js.append(f'    tl.to("#{cur} svg", {{ scale: 1, duration: 0.16, ease: "power2.out" }}, {round(t + 0.04, 3)});')
    # type cards: their own ground, never over the footage
    for j, (t, d, html, style) in enumerate(sc.get("type", [])):
        tid = f"{p}-type{j}"
        def tok(w):
            if w.startswith("*") and w.endswith("*"): return f'<span class="acc"><em>{w[1:-1]}</em></span>'
            if w.startswith("!") and w.endswith("!"): return f'<span class="acc"><em class="alert">{w[1:-1]}</em></span>'
            return f"<span>{w}</span>"
        body = " ".join(tok(w) for w in html.split(" "))
        markup.append(f'    <div id="{tid}" class="clip typecard" style="z-index:{z + 5}" data-start="{t}" data-duration="{d}" data-track-index="20"><div class="type-line">{body}</div></div>')
        sel = f"#{tid} .type-line span"
        if style == "words":
            js.append(f'    tl.fromTo("{sel}", {{ opacity: 0, filter: "blur(8px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.16, stagger: 0.08, ease: "power2.out" }}, {t + 0.02});')
        elif style == "grey":
            js.append(f'    tl.fromTo("{sel}", {{ color: "#2c2830" }}, {{ color: "#f6e7c1", duration: 0.18, stagger: 0.085, ease: "none" }}, {t + 0.08});')
            js.append(f'    tl.fromTo("#{tid} .type-line em", {{ color: "#2c2830" }}, {{ color: "#e05252", duration: 0.18, ease: "none" }}, {t + 0.5});')
        elif style == "letters":
            js.append(f'    tl.fromTo("#{tid} .type-line .ch", {{ opacity: 0.25, filter: "blur(4px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.14, stagger: 0.035, ease: "power2.out" }}, {t + 0.08});')
        js.append(f'    tl.to("{sel if style != "letters" else f"#{tid} .type-line"}", {{ opacity: 0, filter: "blur(8px)", duration: 0.16, stagger: 0.02, ease: "power2.in" }}, {round(t + d - 0.2, 3)});')
    if "dip" in sc:
        markup.append(f'    <div id="{p}-dip" class="dip" style="z-index:{z + 9}" data-layout-ignore></div>')
        js.append(f'    tl.fromTo("#{p}-dip", {{ opacity: 0 }}, {{ opacity: 0.45, duration: 0.1, ease: "none" }}, {sc["dip"]});')

    letters_js = ""
    if any(s == "letters" for (_, _, _, s) in sc.get("type", [])):
        # split letter-style type into .ch spans once, before the timeline is built (static, seek-safe)
        letters_js = """    document.querySelectorAll(".typecard .type-line").forEach((el) => {
      if (el.querySelector(".ch")) return;
      const walk = (node) => [...node.childNodes].forEach((n) => {
        if (n.nodeType === 3) { const f = document.createDocumentFragment(); [...n.textContent].forEach((c) => { const s = document.createElement("span"); s.className = "ch"; s.textContent = c === " " ? "\u00a0" : c; f.appendChild(s); }); n.replaceWith(f); }
        else walk(n);
      });
      walk(el);
    });
"""
    return f"""<template>
  <style>{FONTS}
    #root {{ position: absolute; inset: 0; background: #050507; overflow: hidden; }}
    .cam {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 0 0; }}
    .shot-video {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; object-fit: cover; background: #050507; }}
    .cursor {{ position: absolute; left: 0; top: 0; width: 1px; height: 1px; z-index: 5; }}
    .cursor-in {{ position: absolute; left: -6px; top: -4px; transform-origin: 6px 4px; }}
    .cursor-in svg {{ display: block; filter: drop-shadow(0 6px 10px rgba(0,0,0,0.55)); }}
    .typecard {{ position: absolute; inset: 0; background: #050507; display: flex; align-items: center; justify-content: center; }}
    .type-line {{ font-family: "Fraunces", serif; font-weight: 300; font-size: 168px; letter-spacing: -0.025em; color: #f6e7c1; white-space: nowrap; }}
    .type-line span {{ display: inline-block; }}
    .type-line em {{ font-style: italic; color: #e8a33d; }}
    .type-line em.alert {{ color: #e05252; }}
    .dip {{ position: absolute; inset: 0; background: #000; opacity: 0; pointer-events: none; }}
  </style>
  <div id="root" data-composition-id="{name}" data-width="1920" data-height="1080">
{chr(10).join(markup)}
  </div>
  <script>
{letters_js}    const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
    window.__timelines["{name}"] = tl;
  </script>
</template>
"""


for name, sc in SCENES.items():
    (ROOT / f"compositions/{name}.html").write_text(build(name, sc))
    print("wrote", name)
