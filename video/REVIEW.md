# REVIEW: The Last Satellite, FINAL (renders/final.mp4)

**Output:** 70.0 s · 1920×1080 · 30 fps · H.264 + AAC. Audio is −13.9 LUFS integrated, −1.4 dBTP true peak (loudnorm pass), so nothing clips.

## Arc (the second reference's language: kinetic word captions built over real footage, one italic marigold hero word, cuts every 0.5–2 s)
| Time | Beat |
|---|---|
| 0–6 | Cold open: segment #1579's real readings, typed. Values from the live API `/segments/1579`. |
| 6–12 | Chaos (the nine real channels): 2,123 signals → 9 instruments → 1 question → title card + "ESA OPS-SAT · re-entered 22 May 2024". |
| 12–17 | Converge: #204's real waveform branches into its measured and cited facts (`/demo/204/steps`). |
| 17–20 | Ring counts to TabPFN's 1.000; the camera dives through it into the live console. |
| 20–49 | Real console takes, recorded live against `make api` and the llama.cpp adapter: hero, Observatory channel switch, #204 TRUE POSITIVE, #1579 MISSED ANOMALY, queue card on WHAT IS NOT KNOWN, the Mission Memory "missing from the archive" panel. |
| 49–53 | Proof: AUCPR 0.996 vs 0.979 published; 0.989 on the paper's own 18 features; 1 false alarm · 3 missed · of 529. |
| 53–56 | Lab, framed on the bar chart. |
| 56–62 | Tinker. **Lead: 65.3% → 93.0% (validation) · $0.83 all-in.** Then held-out test 72.2% → 86.3%, evidence quoted verbatim 81% → 100%, 0 invented root causes. **Red failure:** "Terminology citations: 96.2% → 82.7%. We show it." |
| 62–65 | Slot-roll claim: measured, / cited, / or marked unknown. |
| 65–70 | End card: the console's mark, "The Last Satellite", "Its mission ended. Its memories did not.", small credits, seeded marigold petals. |

## Numbers (all verified in this session)
- tinker_learning_curve.json: 0.6533 → 0.930
- tinker_cost.json: 0.8308
- tinker_eval_A.json: 0.7222 → 0.8628; evidence_fidelity 0.8108 → 1.0; unsupported_root_causes 0
- tinker_eval_C.json: 0.9615 → 0.8269
- tabpfn_test_results.json: AUPRC 0.9959; confusion [[415, 1], [3, 110]]
- ablation_base18_test.json: AUPRC 0.9888

## Music (credit)
Three cues were generated locally for this film with **Meta MusicGen-medium** (facebook/musicgen-medium, via Hugging Face transformers), from prompts written for it:
- A1: dark pulse
- B2: driving build
- C1: swell, ending quiet

**Licence caveat:** MusicGen's weights are CC-BY-NC 4.0. That suits a non-commercial DEV post, but it is not a royalty-free library track. Swap it if the video will be used commercially. Credit line: "Music generated with MusicGen (Meta AI)".

**Not listened to.** I can't hear audio, so it was only measured (loudness, peak, spectral balance).

SFX come from the HyperFrames bundled library. Every effect sits on an on-screen action.

## Dropped
- **Vertical 1080×1920:** no time inside the 20-minute limit.
- **Beat-locked cuts:** cuts follow on-screen actions, not a measured beat grid.
- **Confirm:** not in any take; the drawer scrolled past it. The queue beat lands on WHAT IS NOT KNOWN instead.
- **Royalty-free library music:** no library source was reachable; I used MusicGen, see the caveat above.

## Weakest
- The queue caption "Unknown stays unknown." sits over busy card text; it is legible only thanks to its shadow.
- The lab beat is short (2.8 s).

## Update: voiceover, softer low end, new waves
- **Voiceover.** 13 lines spoken by Kokoro-82M (voice `bm_george`, local, free), scripted in `assets/vo/script.tsv`.
  - Captions are rebuilt from the spoken lines in the reel's style (words build, one italic marigold hero word). The claim and end-card lines aren't captioned, because the screen already shows them.
  - Measured: voice sections −12.8 LUFS vs bed-only −20.8 LUFS, so the voice sits about 8 LU above the music.
- **The "vibration".** It was the four bass-impact tails plus the music's sub drone.
  - Beds are high-passed at 80 Hz with a −6 dB bass shelf and ducked to 0.2.
  - Impacts are high-passed at 150 Hz with shortened tails; the error tones are halved.
  - Sub-100 Hz share of the mix went from 22.6% to 1.4%.
- **Waves (first 12 s).**
  - Cold open: segment #1579's real 31-sample trace draws as the readings print, landing on the zero run in ember.
  - Chaos: each channel draws on staggered, scrolls at its own depth and speed, and folds into the centre line one by one. A bottom scrim keeps the captions readable over it.
- **Still open.** Nobody has listened to the voice or music; I can only measure them. The Tinker lead line sits over the planet's ring in the illustration: readable, but busy.
- Final: 70.0 s, 1920×1080, 30 fps, −14.0 LUFS integrated, −1.5 dBTP true peak.
