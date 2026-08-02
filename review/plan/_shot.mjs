// Screenshot the master plan so it can actually be looked at.
//   node review/plan/_shot.mjs docs/plan/hearthmere-plan.svg review/plan/plan.png [px]
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const svg = fs.readFileSync(process.argv[2], 'utf8');
const px = Number(process.argv[4] || 1800);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: px, height: Math.round(px * 1160 / 1120) } });
await page.setContent('<body style="margin:0">' + svg.replace(/width="[^"]*" height="[^"]*"/, 'width="100%" height="100%"') + '</body>');
await page.screenshot({ path: process.argv[3] });
await browser.close();
