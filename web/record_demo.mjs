// Record real clips of the live console (CDP screencast → JPEG frames + timestamps) for the demo film.
// Usage: node record_demo.mjs <outDir> [url]
// Each take writes <outDir>/<take>/frame_XXXXX.jpg, frames.txt (ffconcat with real durations) and clicks.json
// (click points in CSS px and seconds from the take's start), so the film can draw a cursor on the real clicks.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const out = process.argv[2];
const url = process.argv[3] ?? "http://localhost:4173/";
const ONLY = (process.env.TAKES ?? "").split(",").filter(Boolean);
const want = (n) => !ONLY.length || ONLY.includes(n);
const W = 1600, H = 900, DPR = 1.6;
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  args: ["--use-angle=metal", "--ignore-gpu-blocklist", "--hide-scrollbars"],
});
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DPR });
const page = await ctx.newPage();
const cdp = await ctx.newCDPSession(page);
const wait = (ms) => page.waitForTimeout(ms);

let take = null;
cdp.on("Page.screencastFrame", async (f) => {
  cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
  if (!take) return;
  const n = take.frames.length;
  const file = `frame_${String(n).padStart(5, "0")}.jpg`;
  fs.writeFileSync(path.join(take.dir, file), Buffer.from(f.data, "base64"));
  take.frames.push({ file, t: f.metadata.timestamp });
});

async function start(name) {
  const dir = path.join(out, name);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  take = { name, dir, frames: [], clicks: [], t0: Date.now() / 1000 };
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 88, maxWidth: W * DPR, maxHeight: H * DPR, everyNthFrame: 1 });
  await wait(300);
}
async function stop() {
  await wait(200);
  await cdp.send("Page.stopScreencast");
  const t = take; take = null;
  const end = Date.now() / 1000;
  let txt = "ffconcat version 1.0\n";
  t.frames.forEach((fr, i) => {
    const next = i + 1 < t.frames.length ? t.frames[i + 1].t : end;
    txt += `file ${fr.file}\nduration ${Math.max(0.001, next - fr.t).toFixed(4)}\n`;
  });
  if (t.frames.length) txt += `file ${t.frames.at(-1).file}\n`;
  fs.writeFileSync(path.join(t.dir, "frames.txt"), txt);
  const first = t.frames[0]?.t ?? t.t0;
  fs.writeFileSync(path.join(t.dir, "clicks.json"), JSON.stringify(t.clicks.map((c) => ({ ...c, t: +(c.t - first).toFixed(3) })), null, 1));
  console.log(`${t.name}: ${t.frames.length} frames, ${(end - first).toFixed(1)} s`);
}
// Glide the (invisible) mouse to an element, log the click, click it.
async function click(locator, label) {
  const el = typeof locator === "string" ? page.locator(locator).first() : locator;
  await el.scrollIntoViewIfNeeded().catch(() => {});
  const b = await el.boundingBox();
  if (!b) { console.log("no box for", label); return; }
  const x = b.x + b.width / 2, y = b.y + b.height / 2;
  await page.mouse.move(x, y, { steps: 12 });
  await wait(250);
  if (take) take.clicks.push({ label, x: +x.toFixed(1), y: +y.toFixed(1), w: W, h: H, t: Date.now() / 1000 });
  await page.mouse.click(x, y);
}
// Smooth scroll through Lenis with wheel ticks until the section's top reaches `offset`.
async function glideTo(id, offset = 70, ms = 1800) {
  const top = await page.evaluate((id) => document.getElementById(id).getBoundingClientRect().top, id);
  const dist = top - offset, ticks = Math.max(1, Math.round(ms / 40));
  for (let i = 0; i < ticks; i++) { await page.mouse.wheel(0, dist / ticks); await wait(40); }
  await wait(900);
}
async function jumpTo(id, offset = 70) {
  await page.evaluate(([id, o]) => { const el = document.getElementById(id); window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - o); }, [id, offset]);
  await wait(1500);
}

await page.goto(url, { waitUntil: "networkidle" });
await page.mouse.move(W - 40, H - 40);
const candles = page.locator("#seance button.group");
const reveal = page.locator("text=Reveal the truth");
const stepBtns = page.locator("#seance-stage button.group");
// warm the live endpoints so the first request in a take is not a cold start
await page.evaluate(() => Promise.all([204, 1579].map((id) => fetch(`http://localhost:8000/demo/${id}/steps`))));
await page.evaluate(() => fetch("http://localhost:8000/investigations", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ segment_id: 204, use_lm: true }) }));
// 0. confirm live mode
const live = await page.evaluate(() => fetch("http://localhost:8000/health").then((r) => r.ok).catch(() => false));
console.log("live backend:", live);
await page.reload({ waitUntil: "domcontentloaded" });

if (want("hero")) {
// 1. hero: title animation + Earth
await start("hero");
await wait(7000);
await stop();

}
if (want("scroll_elegy")) {
// 2. scroll from hero into the elegy timeline (the orbit decays)
await start("scroll_elegy");
await glideTo("elegy", 70, 2600);
await wait(2500);
await stop();

}
if (want("observatory")) {
// 3. observatory: nine instruments
await jumpTo("observatory", 60);
await start("observatory");
await wait(1500);
const chans = page.locator("#observatory button");
await click(chans.nth(4), "I_PD3_THETA"); await wait(2600);
await click(chans.nth(1), "magnetometer"); await wait(2600);
await stop();

}
if (want("seance_204")) {
// 4. the signal: candle #204, guided run to the card, reveal
await jumpTo("seance", 60);
await start("seance_204");
await wait(1200);
await click(candles.nth(0), "candle #204");
await wait(24500);
if (await reveal.count()) { await click(reveal, "Reveal the truth"); await wait(3500); }
await stop();

}
for (const [name, idx] of [["reveal_204", 0], ["seance_1579", 5]]) {
  if (!want(name)) continue;
  await jumpTo("seance", 60);
  await page.evaluate(() => { const el = document.getElementById("seance"); window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + 380); });
  await wait(1200);
  await candles.nth(idx).click({ trial: true }).catch(() => {});
  await start(name);
  await wait(800);
  await click(candles.nth(idx), `candle ${idx}`);
  // wait for the live steps to arrive (the stage leaves "opening the archive…")
  await page.locator("#seance-stage canvas").first().waitFor({ timeout: 45000 }).catch(() => {});
  await wait(1500);
  await click(stepBtns.nth(5), "step: The card");
  await reveal.first().waitFor({ timeout: 20000 }).catch(() => {});
  await wait(2200);
  if (await reveal.count()) { await click(reveal.first(), "Reveal the truth"); await wait(3800); }
  await stop();
}
if (want("queue")) {
// 6. queue: open #204, confirm
await jumpTo("queue", 60);
await start("queue");
await wait(1500);
await click(page.locator("#queue button.grid").first(), "queue row #204");
const confirm = page.locator("text=Confirm anomaly");
await confirm.first().waitFor({ timeout: 30000 }).catch(() => {});
await wait(1200);
for (let i = 0; i < 20; i++) { await page.mouse.wheel(0, 18); await wait(40); }
await wait(900);
if (await confirm.count()) { await click(confirm, "Confirm anomaly"); await wait(2800); }
await stop();

}
if (want("memory")) {
// 7. memory: type a question, ask the live archive
await page.evaluate(() => { const el = document.querySelector("#memory input"); window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 140); });
await wait(1500);
await start("memory");
await wait(1000);
const input = page.locator("#memory input").first();
await click(input, "ask box");
await page.keyboard.type("What caused the zero values on the magnetometer channels?", { delay: 38 });
await wait(400);
await page.keyboard.press("Enter");
await wait(7000);
await stop();

}
if (want("lab")) {
// 8. laboratory: toggle the paper's own 18 features, then the Tinker section
await jumpTo("lab", 60);
await start("lab");
await wait(2000);
const base18 = page.locator("text=18 published features");
await base18.first().scrollIntoViewIfNeeded();
await wait(1200);
await click(base18.first(), "18 published features"); await wait(2500);
await click(page.locator("text=selected features").first(), "selected features"); await wait(2000);
await page.mouse.wheel(0, 700); await wait(2500);
await stop();

}
if (want("finale")) {
// 9. finale
await jumpTo("finale", 0);
await start("finale");
await wait(7000);
await stop();

}
await browser.close();
