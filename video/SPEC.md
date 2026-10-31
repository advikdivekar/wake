# SPEC: The Last Satellite, product demo film

GOAL:    The viewer leaves knowing that this console reads a dead satellite's telemetry and documents, beats the published benchmark, and says out loud what it does not know.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    63.1 s x 30 = 1893 frames. Music bed ~104 BPM (17.3 frames per beat), generated locally with MusicGen.
LOOK:    The console's own system, taken from web/src/index.css.
         ground void #050507 (night #0b0a0d for panels); ink candle #f6e7c1, bone #ede6da, mute #7d766d;
         accent marigold #e8a33d on one word or object per shot (the highlight block, the ring, 0.996, the mark);
         ember #d2592b for the ring arc; signal #7fb7be for raw traces; alert #e05252 only for the miss and the regression; good #6fbf8a only for checks.
         Display: Fraunces 300, -2% tracking, 120–260 px; italic marigold for one word. Labels: JetBrains Mono 500, 24–30 px, +12% tracking.
         Medium: real screen recordings of the live console (2560×1440 captures), shown at 1.2× (full frame) and punched to 1.6–2.2× on the control in use.
         Light and depth: no glow and no bloom. Panels get a 0 40 120 rgba(0,0,0,.6) shadow. The console's own 5% grain is in the footage.
OBJECTS: telemetry traces (real OPS-SAT samples, drawn as polylines); segment #204's waveform with its 16-sample zero run; the probability ring (the console's Ring, rebuilt 2×);
         the cursor (a 56 px arrow, bone with a void outline) that clicks where the recorder clicked; the results window (evaluations/tinker_eval_*.json rows); the mark (amber dot + tilted orbit from the console's favicon).
MOTION:  arrivals expo.out 0.5–0.8 s; camera punch-ins power3.inOut 0.5 s; zoom-through power3.in 0.55 s; exits 0.2 s blur-out.
         Type: per-word blur 6→0 px, 0.067 s apart (chaos); per-letter for the name; slot roll for the claim; grey→ink for the cards.
SHOTS:
  0.0–6.2   chaos: nine real traces scroll across the frame; "2,123 signals" → "303,493 samples" → "one silent satellite", the highlight block jumping word to word; the traces collapse to one line (whoosh).
  6.2–11.0  converge: #204's real waveform draws left→right; a pulse runs along it; at the zero run five branches sprout to measured and cited nodes (pop ×5); the branches retract into one point.
  11.0–14.2 ring: the point opens into the ring; it counts 0.000→1.000, P(anomalous) · TabPFN-v2; the camera dives through the ring's hole (riser → impact; the music opens).
  13.6–19.2 hero: seen through the ring's hole, the live console's title lands over the real Earth.
  19.2–27.4 hide: type "Hide the label." → click candle #204 → punch onto the ring filling → click Reveal → TRUE POSITIVE.
  27.4–31.8 miss: type "The one it missed." → #1579 reveal → MISSED ANOMALY, 0.098; whip out.
  31.8–36.6 queue: open #204 in the 529-row queue → punch onto the card's WHAT IS NOT KNOWN column.
  36.2–39.6 number: marigold iris out of the card, "0.996" AUCPR on the official test split vs 0.979 best published (bass hit).
  39.6–42.4 lab: the console's own KPI row (0.996 / 0.982 / 86.3% / $0.83) and the "18 published features" toggle.
  42.4–49.0 tinker: results window on the satellite illustration; rows tick ✓; task C turns red (regressed) and stays; "$0.83 on Tinker".
  49.0–53.6 memory: "Ask the archive." → the question typed live → the answer with citations and "missing from the archive".
  53.6–56.6 claim: "Every line is measured. / cited. / or marked unknown." (slot roll).
  56.6–59.0 finale: the console's own last frame: "Its mission ended. Its memories did not."
  59.0–63.1 end card: the orbit draws, the amber dot lands, "The Last Satellite" letters in, github.com/advikdivekar/wake holds 2.5 s.
BANNED:  a glow or bloom added on top of the brand; floating particles we add; three cards in a row; KPI grids; a title over a dimmed screenshot; the logo docked in a corner;
         every element fading and sliding up; titles that drift after they land; any number not in evaluations/ or the live API; mentioning how the training data was built; "seamless", "unlock", "in seconds"; text that enters at 20% opacity before its moment (ghosting).
QA:      0.3 (thumbnail: traces + headline), 5.8 (collapse), 9.5 (branches readable), 13.0 (ring 1.000), 16 (title), 25.9 (TRUE POSITIVE), 30.5 (MISSED ANOMALY),
         35.6 (WHAT IS NOT KNOWN), 37.5 (0.996), 46.5 (red C row), 52.5 (missing from archive), 55.5 (claim), 62.5 (end card).
