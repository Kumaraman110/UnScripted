#!/bin/bash
# Complete the current step (optionally with a report), then wait for the next step and print it.
KEY=$(cat "$(dirname "$0")/../runs/.key" 2>/dev/null)
Q="k=$KEY"
sid=$(curl -s localhost:8787/api/performer/state?$Q | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['step']['id'] if d['step'] else '')")
if [ -z "$sid" ]; then echo "no current step"; ./tools/watch.sh; exit 0; fi
UNSCRIPTED_KEY="$KEY" python3 - "$sid" "$1" <<'PY'
import sys,json,urllib.request,os
sid,rep=sys.argv[1],sys.argv[2] if len(sys.argv)>2 else ''
req=urllib.request.Request('http://localhost:8787/api/step/done?k='+os.environ.get('UNSCRIPTED_KEY',''),data=json.dumps({'step_id':sid,'report':rep}).encode(),headers={'content-type':'application/json'})
try: print('done',sid,'->',urllib.request.urlopen(req).read().decode()[:200])
except Exception as e: print('ERR',e, getattr(e,'read',lambda:b'')().decode()[:200])
PY
sleep 0.6; ./tools/watch.sh
