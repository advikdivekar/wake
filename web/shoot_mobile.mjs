import { chromium } from "playwright-core";
const out = process.argv[2];
const b = await chromium.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", args: ["--use-angle=metal"] });
const p = await b.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
await p.goto("http://localhost:4173/", { waitUntil: "networkidle" }); await p.waitForTimeout(3500);
await p.screenshot({ path: `${out}/m_hero.png` });
for (const id of ["seance", "lab"]) { await p.evaluate((id) => document.getElementById(id)?.scrollIntoView(), id); await p.waitForTimeout(2500); await p.screenshot({ path: `${out}/m_${id}.png` }); }
const w = await p.evaluate(() => document.documentElement.scrollWidth); console.log("scrollWidth", w);
await b.close();
