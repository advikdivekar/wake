// Visual QA: scroll through the site in real Chrome and screenshot each section.
import { chromium } from "playwright-core";
const out = process.argv[2], url = process.argv[3] ?? "http://localhost:4173/";
const browser = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", args: ["--use-angle=metal", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(3500);
await page.screenshot({ path: `${out}/s0_hero.png` });
for (const id of ["elegy", "observatory", "seance", "queue", "memory", "lab", "finale"]) {
  await page.evaluate((id) => document.getElementById(id)?.scrollIntoView({ block: "start" }), id);
  await page.waitForTimeout(2600);
  await page.screenshot({ path: `${out}/s_${id}.png` });
}
// interactions: start guided demo on first candle, jump to the card step, reveal
await page.evaluate(() => document.getElementById("seance")?.scrollIntoView());
await page.waitForTimeout(1500);
const candles = await page.$$("#seance button.group");
if (candles[0]) { await candles[0].click(); await page.waitForTimeout(5000); await page.screenshot({ path: `${out}/i_demo_step1.png` });
  const steps = await page.$$("#seance-stage button.group"); if (steps[2]) { await steps[2].click(); await page.waitForTimeout(3500); await page.screenshot({ path: `${out}/i_demo_ring.png` }); }
  if (steps[5]) { await steps[5].click(); await page.waitForTimeout(2500);
    const rv = await page.$("text=Reveal the truth"); if (rv) { await rv.click(); await page.waitForTimeout(2000); }
    await page.screenshot({ path: `${out}/i_demo_card.png`, fullPage: false }); } }
// queue drawer
await page.evaluate(() => document.getElementById("queue")?.scrollIntoView()); await page.waitForTimeout(1500);
const rows = await page.$$("#queue button.grid"); if (rows[0]) { await rows[0].click(); await page.waitForTimeout(3000); await page.screenshot({ path: `${out}/i_queue_open.png` }); }
// memory ask
await page.evaluate(() => document.getElementById("memory")?.scrollIntoView()); await page.waitForTimeout(1500);
const chips = await page.$$("#memory button.chip"); if (chips[1]) { await chips[1].click(); await page.waitForTimeout(3500); await page.screenshot({ path: `${out}/i_memory.png` }); }
console.log(JSON.stringify({ errors: errors.slice(0, 10) }));
await browser.close();
