# CLAUDE.md

Guidance for working on UNSCRIPTED. Read `README.md` for what it is and `INVENTION.md` for why it ended up this shape.

## What must not be broken

These are not style preferences. The project is only interesting if they hold.

1. **Nothing is constructed after the choice it claims to precede.** An audience that knows a model is in the loop finds nothing impressive in anything generated after a free choice. Any new effect must lock its claim before the spectator acts.
2. **A claim means exactly what it says.** A forced invariant is announced as a guarantee ("what you do cannot matter"), never as a prediction of a free choice. Fable never implies knowledge of anything that was not typed to it.
3. **Failure is said out loud.** No silent reinterpretation of a broken procedure. "No meeting in this shuffle" is a feature.
4. **The performer stays blind.** They receive one step at a time and never the plan or the ending.
5. **No dead air.** The audience never waits on a model call. Planning happens pre-show; per-report verification happens in Python, instantly.
6. **Nothing digital in a spectator's hands.** They shuffle, choose, count, point. The performer's phone is the only device.

Most of this lives in `magician.md`, which is Fable's operating prompt. It is the most load-bearing file in the repo — treat edits to it as carefully as edits to code.

## Layout

| File | Role |
|---|---|
| `server.js` | Show state, the step queue, SSE views, Python checks, and the loop that runs Fable as a `claude -p` subprocess |
| `magician.md` | Fable's rules, repertoire and stagecraft |
| `mcp.js` | stdio MCP bridge; turns Fable's tool calls into POSTs to `/api/cap` |
| `public/performer.html` | Private phone view (key-protected) |
| `public/stage.html` | Public projector view; must never render anything outside `publicState()` |
| `workspace/cards.py` | Card parsing, deck structures, Gilbreath and Kruskal helpers, `find_structures`, `freedom_ladder` |
| `sim/` | Deck simulator and Monte Carlo verification |
| `tools/` | Terminal scripts for driving a show without a phone |

## Conventions

- **No dependencies.** `server.js` uses only Node built-ins; `cards.py` is stdlib-only. Keep it that way.
- **Checks over model calls.** Anything computable (a missing suit, a mate, where a walk ends, whether a row parses) belongs in `on_report_py`, not in a turn.
- **Verify by simulation, never by memory.** Any claimed invariant needs a Monte Carlo check in `sim/` or a `compute` call before it reaches a stage.
- **Auth.** The stage view and `/events` are public. Everything else needs `?k=<key>`: the performer page, its SSE stream, `/api/performer/state` and every POST. `/api/cap` and `/api/tools` additionally require loopback. Being on the host is **not** an authenticator — any page in a browser there can reach 127.0.0.1 — so requests carrying a cross-site `Sec-Fetch-Site`, or a POST that is not `application/json`, are refused. The key is printed at startup, passed to `mcp.js` in its env, and written to `runs/.key` for the scripts in `tools/`.
- **Private state stays private.** `P` (plans, checks, sealed text) is never broadcast. `publicState()` is the audience's whole world.

## Testing a change without an audience

```bash
node server.js &                         # prints the keyed performer URL
python3 sim/deck.py new random --seed 7  # an honest shuffled deck to read from
./tools/watch.sh                         # wait for the next step and print it
./tools/step.sh "7C KD 3S"               # complete the current step with a report
```

`sim/verify_canon.py` re-runs the Monte Carlo verification of the core principles. Run it after touching `cards.py`.
