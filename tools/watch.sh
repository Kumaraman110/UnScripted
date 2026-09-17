#!/bin/bash
# v2 watcher: wait until a step is shown and Fable is not needed (or show ended), then print compact state.
KEY=$(cat "$(dirname "$0")/../runs/.key" 2>/dev/null)
Q="k=$KEY"
for i in $(seq 1 600); do
  s=$(curl -s localhost:8787/api/performer/state?$Q)
  ready=$(echo "$s" | python3 -c "import sys,json; d=json.load(sys.stdin); print('1' if (d['step'] and not d['waiting_for_fable']) or d['phase']=='ended' else '0')" 2>/dev/null)
  [ "$ready" = "1" ] && break; sleep 1
done
echo "$s" | python3 -c '
import sys,json; d=json.load(sys.stdin)
print("phase:",d["phase"],"| thinking:",d["thinking"],"| waiting:",d["waiting_for_fable"],"| queued ahead:",d["queue_ahead"])
if d["hold_text"]: print("HOLD:",d["hold_text"])
st=d["step"]
if st: print("STEP",st["id"],"["+st["needs"]+"]","("+st["phase"]+"):",st["text"]); st["hint"] and print("   hint:",st["hint"])
if d["stage"]["line"]: print("SCREEN:",d["stage"]["line"]["text"])
if d["stage"]["prediction"]: print("PREDICTION:",d["stage"]["prediction"])
if d["closing"]: print("CLOSING:",d["closing"])
if d["error"]: print("ERROR:",d["error"])
'
