// Screenshot a URL via Chrome DevTools Protocol (Node 22 has global WebSocket). Usage: node shot.js <url> <out.png> <w> <h>
const [url, out, w = '1600', h = '900'] = process.argv.slice(2);
const fs = require('fs'); const { spawn } = require('child_process');
const CH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const port = 9333 + Math.floor(Math.random() * 100);
const chrome = spawn(CH, ['--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars', `--remote-debugging-port=${port}`, `--window-size=${w},${h}`, '--user-data-dir=/tmp/unscripted-chrome-' + port, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  let ver; for (let i = 0; i < 40; i++) { try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; } catch { await sleep(250); } }
  if (!ver) throw new Error('chrome did not start');
  const ws = new WebSocket(ver.webSocketDebuggerUrl); let id = 0; const waits = {};
  ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && waits[m.id]) waits[m.id](m); };
  const send = (method, params = {}, sessionId) => new Promise(r => { const i = ++id; waits[i] = r; ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
  await new Promise(r => ws.onopen = r);
  const ct = await send("Target.createTarget", { url: "about:blank", newWindow: true, width: +w, height: +h }); if (!ct.result) { console.error(JSON.stringify(ct)); } const { targetId } = ct.result;
  const { result: { sessionId } } = await send('Target.attachToTarget', { targetId, flatten: true });
  await send('Emulation.setDeviceMetricsOverride', { width: +w, height: +h, deviceScaleFactor: 1, mobile: +w < 600 }, sessionId);
  await send('Page.navigate', { url }, sessionId);
  await sleep(2500);
  const shot = await send('Page.captureScreenshot', { format: 'png' }, sessionId);
  fs.writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
  console.log('saved', out, fs.statSync(out).size);
  ws.close(); chrome.kill('SIGKILL'); process.exit(0);
})().catch(e => { console.error(e.message); chrome.kill('SIGKILL'); process.exit(1); });
