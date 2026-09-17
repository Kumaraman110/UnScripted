#!/usr/bin/env node
// UNSCRIPTED capability bridge: stdio MCP server -> local performance server.
// Zero dependencies. Newline-delimited JSON-RPC over stdio.
const BASE = process.env.UNSCRIPTED_URL || 'http://127.0.0.1:8787';
const RUN = process.env.UNSCRIPTED_RUN || '';
const KEY = process.env.UNSCRIPTED_KEY || '';
const q = (p) => `${BASE}${p}${KEY ? `?k=${encodeURIComponent(KEY)}` : ''}`;
let buf = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buf += chunk;
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (line) handle(line);
  }
});
function send(obj) { process.stdout.write(JSON.stringify(obj) + '\n'); }
async function handle(line) {
  let msg;
  try { msg = JSON.parse(line); } catch { return; }
  const { id, method, params } = msg;
  if (id === undefined) return; // notification
  try {
    if (method === 'initialize') {
      return send({ jsonrpc: '2.0', id, result: {
        protocolVersion: (params && params.protocolVersion) || '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'unscripted', version: '1.0.0' } } });
    }
    if (method === 'ping') return send({ jsonrpc: '2.0', id, result: {} });
    if (method === 'tools/list') {
      const r = await fetch(q('/api/tools'));
      const tools = await r.json();
      return send({ jsonrpc: '2.0', id, result: { tools } });
    }
    if (method === 'tools/call') {
      const r = await fetch(q('/api/cap'), { method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ run: RUN, name: params.name, arguments: params.arguments || {} }) });
      const out = await r.json();
      return send({ jsonrpc: '2.0', id, result: { content: [{ type: 'text', text: out.text || JSON.stringify(out) }], isError: !!out.error } });
    }
    send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Unknown method ${method}` } });
  } catch (e) {
    send({ jsonrpc: '2.0', id, error: { code: -32000, message: String(e && e.message || e) } });
  }
}
