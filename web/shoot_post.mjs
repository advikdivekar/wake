// Post screenshots: missed-anomaly reveal, and the honest "unknown" answer in Mission Memory.
import { chromium } from "playwright-core";
const out = process.argv[2];
const b = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", args: ["--use-angle=metal"] });
const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
await p.goto("http://localhost:4173/", { waitUntil: "networkidle" }); await p.waitForTimeout(2500);
await p.evaluate(() => document.getElementById("seance")?.scrollIntoView()); await p.waitForTimeout(1500);
const candles = await p.$$("#seance button.group");
for (const c of candles) { if ((await c.innerText()).includes("1579")) { await c.click(); break; } }
await p.waitForTimeout(4000);
const steps = await p.$$("#seance-stage button.group"); await steps[5].click(); await p.waitForTimeout(2500);
await p.waitForSelector("text=Reveal the truth", { timeout: 15000 }); await p.click("text=Reveal the truth"); await p.waitForSelector("text=ground truth", { timeout: 15000 }); await p.waitForTimeout(1800);
await p.evaluate(() => { const el = document.querySelector("#seance-stage"); window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY + 120); }); await p.waitForTimeout(1500);
await p.screenshot({ path: `${out}/03b-missed-anomaly-reveal.png` });
await p.evaluate(() => document.getElementById("memory")?.scrollIntoView()); await p.waitForTimeout(1500);
for (const c of await p.$$("#memory button.chip")) { if ((await c.innerText()).includes("zero values")) { await c.click(); break; } }
await p.waitForTimeout(4000);
await p.evaluate(() => window.scrollBy(0, 330)); await p.waitForTimeout(1200);
await p.screenshot({ path: `${out}/05-memory-unknown.png` });
await b.close();
