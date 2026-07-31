import { chromium } from 'playwright';
import { spawn } from 'child_process';
const CHROME = process.env.CHROME_BIN || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const srv = spawn('node', ['client/serve.mjs'], { cwd: '/home/user/unlimitless-horizons', stdio: 'inherit' });
await new Promise(r => setTimeout(r, 2500));
const b = await chromium.launch({ executablePath: CHROME,
  args: ['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--no-sandbox','--disable-dev-shm-usage'] });
const p = await b.newPage({ viewport: { width: 1600, height: 900 } });
p.on('pageerror', e => console.log('ERR', e.message));
await p.goto('http://localhost:8080/');
try { await p.waitForFunction(() => document.body.innerText.includes('venues'), { timeout: 180000 }); } catch(e){ console.log('no status'); }
await new Promise(r => setTimeout(r, 6000));
console.log('STATUS:', await p.evaluate(() => document.body.innerText.slice(0,200)));
await p.screenshot({ path: '/tmp/claude-0/-home-user-unlimitless-horizons/624af48b-b9c8-56c5-846a-941fe6b9da69/scratchpad/arrival_now.png' });
await b.close(); srv.kill(); process.exit(0);
