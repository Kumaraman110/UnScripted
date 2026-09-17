// UNSCRIPTED v2 — local performance server. Node 22, no required deps.
// Fable plans a queue of performer steps ahead of need; reports are checked by Fable-authored code instantly;
// Fable is consulted in the foreground only when a check escalates or the performer reports a problem.
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawn, spawnSync } = require('child_process');
const os = require('os');

const ROOT = __dirname;
const PORT = parseInt(process.env.PORT || '8787', 10);
const MODEL = process.env.FABLE_MODEL || 'claude-opus-5';  // any model your `claude` CLI can run
const EFFORT_PLAN = process.env.FABLE_EFFORT || 'high';
const EFFORT_BG = process.env.FABLE_EFFORT_BG || 'medium';
const WS = path.join(ROOT, 'workspace');
const RUNS = path.join(ROOT, 'runs');
fs.mkdirSync(WS, { recursive: true }); fs.mkdirSync(RUNS, { recursive: true });
// Per-boot key. The stage screen is public; the performer's private surface is not.
// Anyone on the venue wifi can reach this port, so the performer URL carries ?k=<key>.
const KEY = process.env.UNSCRIPTED_KEY || crypto.randomBytes(8).toString('hex');
const KEY_FILE = path.join(RUNS, '.key');
try { fs.writeFileSync(KEY_FILE, KEY, { mode: 0o600 }); } catch { }

function lanIp() {
  for (const [, addrs] of Object.entries(os.networkInterfaces()))
    for (const a of addrs) if (a.family === 'IPv4' && !a.internal) return a.address;
  return '127.0.0.1';
}
const hhmmss = () => new Date().toTimeString().slice(0, 8);
const uid = (p) => p + crypto.randomBytes(3).toString('hex');

// ---------------- state ----------------
let S, P;
function freshState() {
  return {
    phase: 'idle', show_id: null, thinking: false, waiting_for_fable: false, hold_text: null,
    step: null, queue_ahead: 0, props: '', room: '', fable_down: false,
    stage: { title: 'UNSCRIPTED', line: null, prediction: null },
    history: [], closing: null, error: null,
  };
}
function freshPrivate() {
  return { steps: {}, current: null, shown: 0, vars: {}, reports: {}, session: null, running: null, inbox: [], runDir: null, turn: 0, sealed: null, analysis: null, plan_title: null };
}
S = freshState(); P = freshPrivate();

const publicState = () => ({ phase: S.phase, show_id: S.show_id, stage: S.stage, closing: S.closing });
const fullState = () => S;

// ---------------- logging ----------------
function rlog(kind, data) {
  if (!P.runDir) return;
  fs.appendFileSync(path.join(P.runDir, 'events.jsonl'), JSON.stringify({ t: new Date().toISOString(), kind, ...data }) + '\n');
}

// ---------------- SSE ----------------
const clients = { pub: new Set(), perf: new Set() };
function sse(res, set) {
  res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive' });
  res.write('retry: 1500\n\n');
  set.add(res); res.on('close', () => set.delete(res));
  res.write(`event: state\ndata: ${JSON.stringify(set === clients.pub ? publicState() : fullState())}\n\n`);
}
function broadcast() {
  S.queue_ahead = queueAhead();
  const pub = `event: state\ndata: ${JSON.stringify(publicState())}\n\n`;
  const full = `event: state\ndata: ${JSON.stringify(fullState())}\n\n`;
  for (const r of clients.pub) r.write(pub);
  for (const r of clients.perf) r.write(full);
}
setInterval(() => { for (const s of Object.values(clients)) for (const r of s) r.write(': ping\n\n'); }, 15000);

// ---------------- steps ----------------
const NEEDS = ['done', 'report', 'golive'];
function normStep(raw, i, arr) {
  if (!raw || typeof raw.text !== 'string' || !raw.text.trim()) throw new Error(`step ${i} has no text`);
  const id = String(raw.id || uid('s'));
  const needs = NEEDS.includes(raw.needs) ? raw.needs : 'done';
  return {
    id, text: raw.text.trim(), needs, hint: raw.hint || null, hold: raw.hold || null,
    public_line: raw.public_line || null, open_prediction: raw.open_prediction || null, reveal_sealed: !!raw.reveal_sealed,
    on_report_py: raw.on_report_py || null, gate: !!raw.gate, watch: !!raw.watch, end_show: !!raw.end_show, closing: raw.closing || null,
    next: raw.next ? String(raw.next) : (arr && arr[i + 1] ? String(arr[i + 1].id || '') || null : null),
    phase: raw.phase === 'setup' ? 'setup' : 'live',
  };
}
function fill(text) {
  return text.replace(/\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g, (m, k) => (P.vars[k] !== undefined ? String(P.vars[k]) : m));
}
function queueAhead() {
  let n = 0, id = P.current ? (P.steps[P.current] || {}).next : null; const seen = new Set();
  while (id && P.steps[id] && !seen.has(id) && n < 60) { seen.add(id); n++; id = P.steps[id].next; }
  return n;
}
function stepIndex() {
  // A monotonic counter: "step 4 of 4 + what is still queued". Replanning must never
  // make the performer's counter jump backwards mid-show.
  return { index: P.shown || 1, total: (P.shown || 1) + queueAhead() };
}
function setCurrent(id) {
  S.fable_down = false;
  const st = P.steps[id];
  if (!st) { S.step = null; P.current = null; return false; }
  const unfilled = (st.text.match(/\{\{\s*[a-zA-Z0-9_]+\s*\}\}/g) || []).filter(v => fill(v) === v);
  if (unfilled.length) {
    rlog('unfilled_vars', { id: st.id, unfilled });
    P.current = id; S.step = null;
    waitForFable(st.hold);
    S.hold_text = 'Hold the room for a moment — keep everything exactly as it is.';
    fableTurn(`[${hhmmss()}] STOPPED before showing step ${st.id}: its text still contains ${unfilled.join(', ')}, which no check ever set. The performer is holding. Fix it now with direct(...) (a step whose text is complete) or proceed(vars:{...}).`, { effort: EFFORT_PLAN });
    return true;
  }
  P.current = id; P.shown = (P.shown || 0) + 1;
  const { index, total } = stepIndex();
  S.step = { id: st.id, text: fill(st.text), needs: st.needs, hint: st.hint ? fill(st.hint) : null, index, total, phase: st.phase, hold: st.hold ? fill(st.hold) : null };
  S.waiting_for_fable = false; S.hold_text = null;
  if (st.public_line) S.stage.line = { text: fill(st.public_line), time: hhmmss() };
  if (st.open_prediction) S.stage.prediction = { text: fill(st.open_prediction), sealed: false, fingerprint: null, time: hhmmss(), revealed_text: null };
  if (st.reveal_sealed) revealSealed();
  rlog('step_shown', { id: st.id, text: S.step.text, needs: st.needs });
  return true;
}
const stripVars = (t) => String(t || '').replace(/\s*\{\{\s*[a-zA-Z0-9_]+\s*\}\}\s*/g, ' ').replace(/\s+/g, ' ').trim();
function waitForFable(hold) {
  S.waiting_for_fable = true;
  S.hold_text = (hold ? stripVars(fill(hold)) : null) || (S.step && S.step.hold) || 'Keep the room with you: ask the spectator what they think is about to happen, and keep the cards exactly as they are.';
}
function revealSealed() {
  if (!P.sealed) return false;
  // Rebuild the panel if something else (an open prediction) took it over in the meantime.
  if (!S.stage.prediction || !S.stage.prediction.sealed) {
    S.stage.prediction = { text: null, sealed: true, fingerprint: P.sealed.hash.slice(0, 8), time: P.sealed.time || hhmmss(), revealed_text: null };
  }
  S.stage.prediction.revealed_text = P.sealed.text; S.stage.prediction.revealed_time = hhmmss();
  rlog('reveal', { text: P.sealed.text });
  return true;
}

// Run Fable-authored Python on a report. Returns {next?, say?, vars?, escalate?, note?} or {escalate: error}.
function runCheck(code, report, stepId) {
  const env = { ...process.env, REPORT: report, REPORTS: JSON.stringify(P.reports), VARS: JSON.stringify(P.vars), STEP_ID: stepId, PYTHONPATH: WS };
  const preamble = "import os, json, sys\nsys.path.insert(0, os.environ.get('PYTHONPATH','.'))\nimport cards\nREPORT = os.environ.get('REPORT','')\nREPORTS = json.loads(os.environ.get('REPORTS','{}'))\nVARS = json.loads(os.environ.get('VARS','{}'))\nSTEP_ID = os.environ.get('STEP_ID','')\n";
  const r = spawnSync('python3', ['-c', preamble + code], { cwd: WS, env, timeout: 15000, maxBuffer: 1e6, encoding: 'utf8' });
  rlog('check', { step: stepId, report, out: (r.stdout || '').slice(0, 2000), err: (r.stderr || '').slice(0, 1000), status: r.status });
  if (r.status !== 0) return { escalate: `check code failed: ${(r.stderr || r.error && r.error.message || '').trim().slice(-600)}` };
  const lines = (r.stdout || '').trim().split('\n').filter(Boolean);
  if (!lines.length) return { escalate: 'check code printed nothing' };
  try { const o = JSON.parse(lines[lines.length - 1]); return (o && typeof o === 'object') ? o : { escalate: 'check output not an object' }; }
  catch { return { escalate: 'check output was not JSON: ' + lines[lines.length - 1].slice(0, 300) }; }
}

function completeStep(report) {
  const st = P.steps[P.current]; if (!st) return { ok: false, error: 'no current step' };
  const rep = (report || '').trim();
  S.history.unshift({ id: st.id, text: S.step.text, report: rep || null, time: hhmmss() }); S.history = S.history.slice(0, 30);
  if (rep) P.reports[st.id] = rep;
  rlog('step_done', { id: st.id, report: rep });
  if (st.needs === 'golive') { S.phase = 'live'; rlog('golive', {}); }
  let nextId = st.next, say = null, result = null;
  if (st.on_report_py && st.needs === 'report') {
    result = runCheck(st.on_report_py, rep, st.id);
    if (result.vars && typeof result.vars === 'object') Object.assign(P.vars, result.vars);
    if (result.say) { P.vars.say = String(result.say); say = String(result.say); }
    if (result.next) nextId = String(result.next);
    if (result.escalate) {
      waitForFable(st.hold);
      fableTurn(`[${hhmmss()}] NEEDS YOU NOW. Step ${st.id} ("${S.step.text}") got the report: "${rep}". The check said: ${result.escalate}${result.note ? ' | note: ' + result.note : ''}. The performer is meanwhile doing the hold action: "${S.hold_text}". Decide: proceed(next_id, say/vars), direct(...) a fix, or plan(...) a new route. Do it in this turn.`, { effort: EFFORT_PLAN });
      broadcast(); return { ok: true, waiting: true };
    }
  }
  if (st.end_show) { endShow(st.closing || (S.stage.line && S.stage.line.text) || 'Goodnight.'); broadcast(); return { ok: true }; }
  if (st.gate) {
    waitForFable(st.hold);
    fableTurn(`[${hhmmss()}] GATE. Step ${st.id} ("${S.step.text}") completed${rep ? ` with report: "${rep}"` : ''}${say ? ` | check says: ${say}` : ''}${result && result.note ? ' | note: ' + result.note : ''}. The performer is meanwhile doing the hold action: "${S.hold_text}". Verify and then proceed(next_id?) / direct(...) / plan(...) in this turn.`, { effort: EFFORT_PLAN });
    broadcast(); return { ok: true, waiting: true };
  }
  const moved = nextId && setCurrent(nextId);
  if (!moved) { S.step = null; P.current = null; if (S.phase !== 'ended') { waitForFable('Nothing is queued. Keep the spectator engaged: ask what they noticed so far.'); fableTurn(`[${hhmmss()}] The queue ran out after step ${st.id} ("${st.text}")${rep ? ` report: "${rep}"` : ''}. The performer is holding with: "${S.hold_text}". plan(...) the next steps now.`, { effort: EFFORT_PLAN }); } }
  else if (st.needs === 'report' || st.watch || st.needs === 'golive') {
    // background observation — Fable watches, intervenes only if needed
    const cur = S.step ? `Now on step ${S.step.id} ("${S.step.text}"), ${queueAhead()} queued after it.` : 'No step is current.';
    fableTurn(`[${hhmmss()}] ${st.needs === 'golive' ? 'The audience is ready — the performer is LIVE.' : `Step ${st.id} ("${S.history[0].text}") done${rep ? ` with report: "${rep}"` : ''}${say ? ` | check: ${say}` : ''}${result && result.note ? ' | note: ' + result.note : ''}.`} ${cur} Intervene (plan/direct/say_public/seal) only if this changes what should happen; otherwise reply with a few words and nothing else.`, { effort: EFFORT_BG, background: true });
  }
  broadcast(); return { ok: true };
}
function recordHistory(method) {
  try { const hf = path.join(RUNS, 'history.json'); const h = fs.existsSync(hf) ? JSON.parse(fs.readFileSync(hf, 'utf8')) : [];
    if (h.some(x => x.show_id === S.show_id)) return;
    h.push({ show_id: S.show_id, ended: new Date().toISOString(), props: S.props, room: S.room, method, closing: S.closing }); fs.writeFileSync(hf, JSON.stringify(h, null, 1)); } catch (e) { console.error('history', e.message); }
}
function endShow(closing, method) {
  S.phase = 'ended'; S.closing = closing; S.step = null; P.current = null; S.waiting_for_fable = false; S.hold_text = null;
  rlog('end', { closing });
  if (S.history.length >= 3) recordHistory(method || `${P.plan_title || 'untitled'} — ${(P.analysis && P.analysis.impossible_claim) || ''}`.slice(0, 400));
}

// ---------------- capabilities (MCP tools) ----------------
const STEP_SCHEMA = { type: 'object', properties: {
  id: { type: 'string', description: 'Unique short id, e.g. "g3". Later steps may be referenced by id.' },
  text: { type: 'string', description: 'What the performer does now. 1–3 short sentences. Put every line they must say aloud in double quotes. May contain {{var}} placeholders filled from earlier checks.' },
  needs: { type: 'string', enum: ['done', 'report', 'golive'], description: 'done = tap when finished; report = performer must type what happened (give a hint); golive = the barrier between private setup and the live show.' },
  hint: { type: 'string', description: 'For report steps: exactly what to type, e.g. "top card and bottom card, like 7C KD"' },
  phase: { type: 'string', enum: ['setup', 'live'] },
  public_line: { type: 'string', description: 'Optional: text shown on the stage screen when this step starts (Fable\'s public voice). Also what the performer reads aloud in the step text if there is no screen.' },
  open_prediction: { type: 'string', description: 'Optional: an OPEN prediction shown to everyone when this step starts.' },
  reveal_sealed: { type: 'boolean', description: 'Optional: reveal the sealed prediction when this step starts.' },
  on_report_py: { type: 'string', description: 'Optional Python 3 for report steps. Python variables already defined for you: REPORT (str, this report), REPORTS (dict of earlier reports by step id), VARS (dict), STEP_ID; `cards` is already imported. Print ONE JSON object as the last line: {"next": "<step id>", "vars": {"k": "v"}, "note": "for Fable", "escalate": "reason"}. next overrides routing; vars fill {{k}} in later steps; escalate stops the show and calls you.' },
  gate: { type: 'boolean', description: 'If true, after this step completes the performer waits (doing hold) until you proceed/direct/plan. Use sparingly.' },
  hold: { type: 'string', description: 'Stage business the performer does if the show has to wait for you after this step. Always meaningful, never filler.' },
  watch: { type: 'boolean', description: 'Wake you in the background when this done-step completes.' },
  next: { type: 'string', description: 'Next step id (default: the following step in the list).' },
  end_show: { type: 'boolean' }, closing: { type: 'string' },
}, required: ['id', 'text', 'needs'] };

const TOOLS = [
  { name: 'plan', description: 'PLAN — install the performer\'s upcoming steps (replaces everything after the current step; if the show is waiting for you, the new start step becomes current immediately). Include setup steps (phase "setup") before a "golive" barrier when the audience is not yet present. Keep ≥4 live steps queued ahead of the performer at all times. Include your private effect analysis.',
    inputSchema: { type: 'object', properties: {
      title: { type: 'string' },
      analysis: { type: 'object', description: 'PRIVATE. Your honest answers before performing.', properties: {
        impossible_claim: { type: 'string', description: 'What exactly the spectator will believe is impossible (one sentence, in their words).' },
        why_surprising: { type: 'string' }, free_variables: { type: 'string' }, controlled_variables: { type: 'string' },
        evidence_establishes: { type: 'string' }, skeptic_explanation: { type: 'string' }, survives: { type: 'boolean' } },
        required: ['impossible_claim', 'why_surprising', 'free_variables', 'controlled_variables', 'evidence_establishes', 'skeptic_explanation', 'survives'] },
      steps: { type: 'array', items: STEP_SCHEMA, minItems: 1 },
      start_id: { type: 'string', description: 'Id of the first new step (default: first in list).' },
      mode: { type: 'string', enum: ['replace', 'append'], description: 'replace (default): drop all steps after the current one and install these. append: keep the existing queue and attach these after its last step.' },
    }, required: ['steps', 'analysis'] } },
  { name: 'direct', description: 'DIRECT — one immediate step for the performer (inserted right after the current step, or shown now if the show is waiting for you). For live adaptation.',
    inputSchema: { type: 'object', properties: { text: { type: 'string' }, needs: { type: 'string', enum: ['done', 'report'] }, hint: { type: 'string' }, public_line: { type: 'string' }, hold: { type: 'string' }, gate: { type: 'boolean' }, on_report_py: { type: 'string' } }, required: ['text', 'needs'] } },
  { name: 'proceed', description: 'PROCEED — when the show is waiting for you and the plan is still good: continue to the next step (or a specific step id), optionally setting vars used by later steps.',
    inputSchema: { type: 'object', properties: { next_id: { type: 'string' }, vars: { type: 'object' } } } },
  { name: 'say_public', description: 'SAY — put a line on the stage screen (Fable\'s public voice). If there is no screen, also tell the performer to read it in a step.',
    inputSchema: { type: 'object', properties: { text: { type: 'string' } }, required: ['text'] } },
  { name: 'predict_open', description: 'OPEN PREDICTION — show a prediction to everyone NOW, before the event it is about. Only for predictions that are true statements about what the procedure will produce.',
    inputSchema: { type: 'object', properties: { text: { type: 'string' } }, required: ['text'] } },
  { name: 'seal', description: 'SEAL — record a hidden prediction now; the screen shows only "sealed at <time>" and a short fingerprint. Reveal later with reveal (or a step with reveal_sealed). Use only when knowing the text would spoil a free choice; never claim it proves more than that the text existed at that time.',
    inputSchema: { type: 'object', properties: { text: { type: 'string' } }, required: ['text'] } },
  { name: 'reveal', description: 'REVEAL — show the sealed prediction\'s text.', inputSchema: { type: 'object', properties: {} } },
  { name: 'compute', description: 'COMPUTE — run Python 3 privately (stdlib + `import cards`: parse_cards, mate, si_stebbins, riffle, gilbreath_report, …) to design and VERIFY procedures against every possible spectator action before you rely on them. Print results.',
    inputSchema: { type: 'object', properties: { purpose: { type: 'string' }, code: { type: 'string' } }, required: ['code'] } },
  { name: 'end_show', description: 'END — close the show with a public closing line and a PRIVATE one-sentence method note for varying future shows.',
    inputSchema: { type: 'object', properties: { closing: { type: 'string' }, method_summary: { type: 'string' } }, required: ['closing', 'method_summary'] } },
];

function installPlan(a) {
  if (!Array.isArray(a.steps) || !a.steps.length) throw new Error('steps required');
  const withIds = a.steps.map(s => (s && typeof s === 'object') ? { ...s, id: String(s.id || uid('s')) } : s);
  const norm = withIds.map((s, i, arr) => normStep(s, i, arr));
  const startId = a.start_id ? String(a.start_id) : norm[0].id;
  if (!norm.find(s => s.id === startId)) throw new Error('start_id not in steps');
  const append = a.mode === 'append' && P.current && P.steps[P.current];
  if (append) {
    // find the tail of the current chain and attach
    let id = P.current; const seen = new Set();
    while (P.steps[id] && P.steps[id].next && P.steps[P.steps[id].next] && !seen.has(id)) { seen.add(id); id = P.steps[id].next; }
    for (const s of norm) P.steps[s.id] = s;
    P.steps[id].next = startId;
  } else {
    // drop all future steps; keep current (if any)
    const keep = {}; if (P.current && P.steps[P.current]) keep[P.current] = P.steps[P.current];
    P.steps = keep; for (const s of norm) P.steps[s.id] = s;
  }
  P.analysis = a.analysis || P.analysis || null; P.plan_title = a.title || P.plan_title || null;
  rlog('plan', { title: a.title, analysis: a.analysis, steps: norm.map(s => ({ id: s.id, needs: s.needs, phase: s.phase, text: s.text.slice(0, 160), gate: s.gate, has_check: !!s.on_report_py })) });
  if (!P.current || !S.step) { setCurrent(startId); if (S.phase === 'idle') S.phase = 'setup'; }
  else if (append) {
    // Attached at the tail. If the performer is holding, this is also the answer they were waiting for.
    if (S.waiting_for_fable) { const nxt = P.steps[P.current].next; setCurrent(nxt && P.steps[nxt] ? nxt : startId); }
  }
  else if (S.waiting_for_fable) { setCurrent(startId); }
  else { P.steps[P.current].next = startId; }
  const planPhase = norm.some(s => s.phase === 'setup') ? 'setup+live' : 'live';
  return `Plan ${append ? 'appended' : 'installed'} (${norm.length} steps, ${planPhase}). Current step: ${P.current} ("${S.step ? S.step.text.slice(0, 80) : ''}"). Queued ahead: ${queueAhead()}. Step ids: ${norm.map(s => s.id).join(', ')}.`;
}

async function runCapability(name, a) {
  if (S.phase === 'idle' && name !== 'compute') throw new Error('No show started.');
  if (S.phase === 'ended' && !['compute', 'end_show'].includes(name)) throw new Error('Show has ended.');
  rlog('cap', { name, args: name === 'plan' ? { title: a.title, n: (a.steps || []).length } : a });
  switch (name) {
    case 'plan': return installPlan(a);
    case 'direct': {
      const st = normStep({ ...a, id: uid('d'), phase: S.phase === 'setup' ? 'setup' : 'live' }, 0, null);
      if (!P.current || S.waiting_for_fable || !S.step) { st.next = P.current && P.steps[P.current] ? P.steps[P.current].next : null; if (P.current && S.waiting_for_fable) st.next = P.steps[P.current].next; P.steps[st.id] = st; setCurrent(st.id); }
      else { st.next = P.steps[P.current].next; P.steps[st.id] = st; P.steps[P.current].next = st.id; }
      return `Step ${st.id} ${S.step && S.step.id === st.id ? 'is now on the performer\'s screen' : 'inserted right after the current step'}. Queued ahead: ${queueAhead()}.`;
    }
    case 'proceed': {
      if (a.vars && typeof a.vars === 'object') Object.assign(P.vars, a.vars);
      const cur = P.steps[P.current];
      const nextId = a.next_id ? String(a.next_id) : (cur ? cur.next : null);
      if (!S.waiting_for_fable) return `Not waiting; the performer is on step ${P.current}. Use direct or plan to change what comes next.`;
      if (!nextId || !setCurrent(nextId)) throw new Error('no such next step; use plan or direct');
      return `Proceeding. Current step: ${P.current}.`;
    }
    case 'say_public': S.stage.line = { text: a.text, time: hhmmss() }; rlog('say', { text: a.text }); return 'On screen.';
    case 'predict_open': S.stage.prediction = { text: a.text, sealed: false, fingerprint: null, time: hhmmss(), revealed_text: null }; rlog('predict_open', { text: a.text }); return `Open prediction shown at ${hhmmss()}.`;
    case 'seal': {
      const salt = crypto.randomBytes(8).toString('hex'); const hash = crypto.createHash('sha256').update(salt + '|' + a.text).digest('hex');
      P.sealed = { text: a.text, salt, hash, time: hhmmss() }; S.stage.prediction = { text: null, sealed: true, fingerprint: hash.slice(0, 8), time: hhmmss(), revealed_text: null };
      rlog('seal', { text: a.text, hash }); return `Sealed at ${hhmmss()} (fingerprint ${hash.slice(0, 8)}). Reveal with reveal or a step with reveal_sealed.`;
    }
    case 'reveal': return revealSealed() ? 'Revealed.' : 'Nothing was sealed, so there is nothing to reveal.';
    case 'compute': {
      const r = spawnSync('python3', ['-c', a.code], { cwd: WS, env: { ...process.env, PYTHONPATH: WS }, timeout: 25000, maxBuffer: 2e6, encoding: 'utf8' });
      rlog('compute', { purpose: a.purpose, out: (r.stdout || '').slice(0, 3000), err: (r.stderr || '').slice(0, 1500) });
      return ((r.stdout || '').slice(0, 8000) || '(no output)') + (r.stderr ? '\nstderr:\n' + r.stderr.slice(0, 2000) : '');
    }
    case 'end_show': {
      endShow(a.closing, a.method_summary);
      return 'Show ended.';
    }
    default: throw new Error('unknown capability ' + name);
  }
}

// ---------------- Fable turns ----------------
const SYSTEM_FILE = path.join(ROOT, 'magician.md');
function mcpConfig() { return JSON.stringify({ mcpServers: { unscripted: { command: process.execPath, args: [path.join(ROOT, 'mcp.js')], env: { UNSCRIPTED_URL: `http://127.0.0.1:${PORT}`, UNSCRIPTED_RUN: S.show_id || '', UNSCRIPTED_KEY: KEY } } } }); }
function stateLine() {
  return `[NOW ${hhmmss()}] phase=${S.phase}; current step=${S.step ? S.step.id + ' ("' + S.step.text.slice(0, 90) + '")' : 'none'}; waiting_for_fable=${S.waiting_for_fable}; queued ahead=${queueAhead()}.`;
}
function fableTurn(message, opts = {}) {
  if (P.running) {
    P.inbox.push({ message, opts });
    if (!opts.background && P.runningOpts && P.runningOpts.background) { P.killed = true; try { P.running.kill('SIGTERM'); } catch { } }
    return;
  }
  const first = !P.session; if (first) P.session = crypto.randomUUID();
  P.turn++; S.thinking = true; broadcast();
  rlog('fable_in', { turn: P.turn, effort: opts.effort || EFFORT_PLAN, bg: !!opts.background, message });
  const args = ['-p', message, '--model', MODEL, '--effort', opts.effort || EFFORT_PLAN, '--output-format', 'json', '--max-turns', '40',
    '--system-prompt-file', SYSTEM_FILE, '--tools', '', '--setting-sources', '', '--mcp-config', mcpConfig(), '--strict-mcp-config',
    '--allowedTools', 'mcp__unscripted', ...TOOLS.map(t => 'mcp__unscripted__' + t.name), first ? '--session-id' : '--resume', P.session];
  const t0 = Date.now();
  let child;
  try {
    child = spawn('claude', args, { cwd: WS, env: { ...process.env, CLAUDECODE: '', CLAUDE_CODE_ENTRYPOINT: '' }, stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (e) {
    S.thinking = false; S.error = `Fable could not be started (${e.code || e.message}). Is the claude CLI installed and logged in?`;
    console.error('[fable] spawn threw', e.message); rlog('fable_spawn_error', { message: e.message }); broadcast(); return;
  }
  const myP = P;
  child.on('error', (e) => {
    if (myP !== P || myP.running !== child) return;
    console.error('[fable] spawn failed', e.message); rlog('fable_spawn_error', { message: e.message });
    myP.spawnError = `Fable could not be started (${e.code || e.message}). Is the claude CLI installed and logged in?`;
    S.error = myP.spawnError;
  });
  P.running = child; P.runningOpts = opts; P.killed = false; let out = '', err = '';
  child.stdout.on('data', d => out += d); child.stderr.on('data', d => err += d);
  child.on('close', (code) => {
    // A child from a show that has since been reset or replaced must stay silent.
    if (myP !== P || myP.running !== child) { rlog('fable_orphan_exit', { turn: P.turn, code }); return; }
    P.running = null; S.thinking = false; const killed = P.killed; P.killed = false;
    let result = null; try { result = JSON.parse(out); } catch { }
    if (killed) rlog('fable_killed', { turn: P.turn, ms: Date.now() - t0 });
    else rlog('fable_out', { turn: P.turn, code, ms: Date.now() - t0, result: result ? { text: (result.result || '').slice(0, 1500), cost: result.total_cost_usd, turns: result.num_turns, is_error: result.is_error } : { raw: out.slice(0, 1500) }, err: err.slice(0, 1500) });
    if (killed) { /* preempted by a foreground need */ }
    else if (code !== 0 || !result || result.is_error) {
      console.error('[fable] turn failed', code, err.slice(0, 400));
      const why = (result && typeof result.result === 'string' && result.result.trim()) ? result.result.trim().slice(0, 300) : '';
      S.error = myP.spawnError || (why ? `Fable could not answer: ${why}` : 'Fable hit a technical error on its last turn.');
    }
    else S.error = null;
    // A failed turn while the performer is holding would freeze the show. Say so, and
    // let them carry on if there are still steps queued.
    if (!killed && S.error && S.waiting_for_fable && !P.inbox.length && S.phase !== 'ended') {
      const nxt = P.steps[P.current] && P.steps[P.current].next;
      if (nxt && P.steps[nxt]) { S.hold_text = 'Fable could not be reached. There are still steps queued — tap "Carry on without Fable" below.'; S.fable_down = true; }
      else { S.hold_text = 'Fable could not be reached and nothing is queued. Use "Something went wrong" to try again, or end the show.'; S.fable_down = true; }
    }
    if (P.inbox.length && S.phase !== 'ended') {
      const items = P.inbox.splice(0);
      const fg = items.find(i => !i.opts.background);
      const msg = items.map(i => i.message).join('\n\n') + '\n\n' + stateLine();
      broadcast(); return fableTurn(msg, fg ? { effort: EFFORT_PLAN } : { effort: EFFORT_BG, background: true });
    }
    broadcast();
  });
}

function startShow(props, room) {
  S = freshState(); P = freshPrivate();
  S.show_id = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19); S.phase = 'setup'; S.props = props; S.room = room;
  P.runDir = path.join(RUNS, S.show_id); fs.mkdirSync(P.runDir, { recursive: true });
  rlog('start', { props, room, model: MODEL });
  let prior = '';
  try { const h = JSON.parse(fs.readFileSync(path.join(RUNS, 'history.json'), 'utf8')).slice(-5); if (h.length) prior = `\n\nEarlier shows (vary materially — some of this audience may have seen them):\n` + h.map(x => `- ${x.method}`).join('\n'); } catch { }
  waitForFable('Pre-show. Get the props ready and wait for Fable\'s first setup step.');
  broadcast();
  fableTurn(`PRE-SHOW. The audience is NOT present yet; the performer is alone with the props and their phone. You have time now — use it.\n\nProps: ${props || '(none listed)'}\nRoom: ${room || '(no description)'}\nClock: ${hhmmss()}.${prior}\n\nWork in two calls. FIRST, within about a minute: choose the effects for THIS room and plan(...) ONLY the setup steps (phase "setup", including a report step whose check verifies the arrangement) plus the "golive" step — so the performer can start arranging now. SECOND: answer the seven questions honestly, VERIFY every procedure with compute against random spectator behavior, and plan(mode:"append", ...) the complete live steps for the first effect (hints, on_report_py checks that compute everything code can compute, hold texts, public lines, honest-miss branches) and ideally the second effect. Every live report that matters to the outcome must be checked by code. Then stop.`, { effort: EFFORT_PLAN });
}

// ---------------- HTTP ----------------
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' };
function serveFile(res, f) { fs.readFile(f, (e, d) => { if (e) { res.writeHead(404); return res.end('not found'); } res.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); res.end(d); }); }
function body(req) {
  return new Promise(r => {
    let b = '', n = 0, done = false;
    const finish = (v) => { if (!done) { done = true; r(v); } };
    req.setTimeout(10000, () => { req.destroy(); finish(null); });
    req.on('data', d => { n += d.length; if (n > 262144) { req.destroy(); return finish(null); } b += d; });
    req.on('end', () => { try { finish(JSON.parse(b || '{}')); } catch { finish({}); } });
    req.on('error', () => finish(null));
  });
}
function json(res, code, obj) { res.writeHead(code, { 'content-type': 'application/json' }); res.end(JSON.stringify(obj)); }
function isLocal(req) { const a = req.socket.remoteAddress || ''; return a === '127.0.0.1' || a === '::1' || a === '::ffff:127.0.0.1'; }
function keyOk(u) {
  const given = Buffer.from(String(u.searchParams.get('k') || ''));
  const want = Buffer.from(KEY);
  return given.length === want.length && crypto.timingSafeEqual(given, want);
}
// Being on this machine is NOT an authenticator: any page open in a browser here can
// reach 127.0.0.1. Every private route needs the key, and a request a browser made
// from another site is refused outright.
function sameSite(req) { const sf = req.headers['sec-fetch-site']; return !sf || sf === 'same-origin' || sf === 'none'; }
function allowed(req, u) { return keyOk(u) && sameSite(req); }
function deny(res) { res.writeHead(403, { 'content-type': 'text/plain; charset=utf-8' }); res.end('This is the performer\'s page. Open the link printed in the terminal, including the ?k=... part.'); }

http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  const p = u.pathname;
  try {
    if (p === '/' || p === '/stage') return serveFile(res, path.join(ROOT, 'public', 'stage.html'));
    if (p === '/performer') return allowed(req, u) ? serveFile(res, path.join(ROOT, 'public', 'performer.html')) : deny(res);
    if (p.startsWith('/public/')) return serveFile(res, path.join(ROOT, p));
    if (p === '/events') return sse(res, clients.pub);
    if (p === '/performer/events') return allowed(req, u) ? sse(res, clients.perf) : deny(res);
    if (p === '/api/state') return json(res, 200, publicState());
    if (p === '/api/performer/state') return allowed(req, u) ? json(res, 200, fullState()) : deny(res);
    if (p === '/api/tools') return (isLocal(req) && allowed(req, u)) ? json(res, 200, TOOLS) : deny(res);
    if (req.method !== 'POST') { res.writeHead(404); return res.end('not found'); }
    if (!allowed(req, u)) return deny(res);
    if (!String(req.headers['content-type'] || '').toLowerCase().startsWith('application/json')) return deny(res);
    const b = await body(req);
    if (b === null) return json(res, 413, { ok: false, error: 'body too large' });
    if (p === '/api/cap') {
      if (!isLocal(req)) return deny(res);
      if (b.name !== 'compute' && (!S.show_id || b.run !== S.show_id)) { rlog('stale_cap', { name: b.name, run: b.run }); return json(res, 200, { error: true, text: 'This show is over or was reset. Stop; do nothing further.' }); }
      try { const text = await runCapability(b.name, b.arguments || {}); broadcast(); return json(res, 200, { text }); }
      catch (e) { return json(res, 200, { error: true, text: 'Capability error: ' + e.message }); }
    }
    if (p === '/api/show/start') { if (S.phase === 'setup' || S.phase === 'live') return json(res, 400, { ok: false, error: 'a show is running' });
      try { if (P.running) P.running.kill('SIGKILL'); } catch { } startShow(String(b.props || ''), String(b.room || '')); return json(res, 200, { ok: true, show_id: S.show_id }); }
    if (p === '/api/show/reset') { try { if (P.running) P.running.kill('SIGKILL'); } catch { } rlog('reset', {}); S = freshState(); P = freshPrivate(); broadcast(); return json(res, 200, { ok: true }); }
    if (S.phase !== 'setup' && S.phase !== 'live') return json(res, 400, { ok: false, error: 'no show running' });
    if (p === '/api/show/end') { endShow(S.closing || 'Thank you.'); broadcast(); return json(res, 200, { ok: true }); }
    if (p === '/api/step/done') {
      if (!S.step) return json(res, 400, { ok: false, error: 'no current step' });
      if (b.step_id && b.step_id !== S.step.id) return json(res, 409, { ok: false, error: 'step changed; look at the screen' });
      if (S.waiting_for_fable) return json(res, 409, { ok: false, error: 'waiting for Fable' });
      if (S.step.needs === 'report' && !String(b.report || '').trim()) return json(res, 400, { ok: false, error: 'report required' });
      return json(res, 200, completeStep(String(b.report || '')));
    }
    if (p === '/api/continue') {
      // Fable is unreachable but steps are still queued: let the performer carry on.
      if (!S.waiting_for_fable) return json(res, 400, { ok: false, error: 'not waiting' });
      const cur = P.steps[P.current]; const nxt = cur && cur.next;
      if (!nxt || !P.steps[nxt]) return json(res, 400, { ok: false, error: 'nothing is queued' });
      rlog('manual_continue', { from: P.current, to: nxt });
      setCurrent(nxt); broadcast(); return json(res, 200, { ok: true });
    }
    if (p === '/api/problem') {
      const text = String(b.text || '').trim(); if (!text) return json(res, 400, { ok: false, error: 'empty' });
      rlog('problem', { text });
      const cur = S.step ? `Current step ${S.step.id} ("${S.step.text}")${S.step.needs === 'report' ? ' (awaiting a report)' : ''}, ${queueAhead()} queued after it.` : 'No current step.';
      waitForFable(S.step && S.step.hold);
      fableTurn(`[${hhmmss()}] PROBLEM from the performer: "${text}". ${cur} Recent reports: ${JSON.stringify(Object.entries(P.reports).slice(-4))}. The performer is holding with: "${S.hold_text}". Adapt honestly now: direct(...) a fix (it shows immediately), proceed(...) if nothing changes, or plan(...) a new route. Never pretend a broken condition held.`, { effort: EFFORT_PLAN });
      broadcast(); return json(res, 200, { ok: true });
    }
    json(res, 404, { ok: false, error: 'unknown endpoint' });
  } catch (e) { console.error(e); json(res, 500, { ok: false, error: e.message }); }
}).listen(PORT, '0.0.0.0', () => {
  for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.on(sig, () => { try { if (P.running) P.running.kill('SIGKILL'); } catch { } process.exit(0); });
  process.on('exit', () => { try { if (P.running) P.running.kill('SIGKILL'); } catch { } });
  console.log(`\nUNSCRIPTED`);
  console.log(`  stage screen (public, for a projector):  http://localhost:${PORT}/`);
  console.log(`  performer page (PRIVATE, open on your phone):`);
  console.log(`      http://${lanIp()}:${PORT}/performer?k=${KEY}`);
  console.log(`  Keep that link to yourself: it is the only thing protecting your instructions.`);
  console.log(`  model=${MODEL}  plan-effort=${EFFORT_PLAN}  bg-effort=${EFFORT_BG}\n`);
});
