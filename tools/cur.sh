#!/bin/bash
KEY=$(cat "$(dirname "$0")/../runs/.key" 2>/dev/null)
Q="k=$KEY"
curl -s localhost:8787/api/performer/state?$Q | python3 -c '
import sys,json; d=json.load(sys.stdin); s=d["step"]
print("phase:",d["phase"],"| waiting:",d["waiting_for_fable"],"| queued:",d["queue_ahead"],"| thinking:",d["thinking"])
if d["hold_text"] and d["waiting_for_fable"]: print("HOLD:",d["hold_text"])
if s: print("STEP",s["id"],"["+s["needs"]+"]:",s["text"]); s.get("hint") and print("   HINT:",s["hint"])
if d["stage"]["line"]: print("SCREEN:",d["stage"]["line"]["text"])
if d["stage"]["prediction"]: print("PREDICTION:",d["stage"]["prediction"])
if d["closing"]: print("CLOSING:",d["closing"])'
