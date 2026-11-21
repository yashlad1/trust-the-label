#!/bin/zsh
# R4: stage 3 at full size, live gate luna then (if the money checks pass) nemotron35. Usage: dev/launch_r4.sh dry|paid
MODE=$1
[[ $MODE == dry || $MODE == paid ]] || { echo "usage: dev/launch_r4.sh dry|paid"; exit 1; }
cd "${0:A:h:h}" || exit 1
L=logs; [[ $MODE == dry ]] && L=logs/dry
LUNA=$L/r4-luna; NEMO=$L/r4-nemotron35
[[ -e $LUNA || -e $NEMO ]] && { echo "STOP: $LUNA or $NEMO exists"; exit 1; }
S1=records/fp4/fp4-stage1
S1LOGS=$(dev/py.sh python -c "import json,sys;print(','.join(json.load(open('$S1/manifest.json'))['stage1']))")
J=src/trustlabel/scenarios
COMMON=(--wording $J/wording.json --epochs 2 --jobs $J/delete.json,$J/send.json,$J/pay.json,$J/publish.json --stage1-logs $S1LOGS --no-stage2)

dev/py.sh python -u dev/pipeline.py $MODE $LUNA $COMMON --stop-at 1.20 || exit 1

CHECK=$(dev/py.sh python - $MODE $LUNA <<'PY'
import sys, json, glob
sys.path.insert(0, "dev")
from pathlib import Path
from inspect_ai.log import read_eval_log
mode, luna = sys.argv[1:3]
luna_spend = json.load(open(f"{luna}/manifest.json"))["spend"]
proj = luna_spend * 1.48
def spend(paths):
    return sum(((e.call.response or {}).get("usage") or {}).get("cost") or 0
               for p in paths for s in read_eval_log(p).samples or [] for e in s.events if e.event == "model" and e.call)
billed = spend(q for pre in ("r2", "r4") for q in glob.glob(f"logs/{pre}-*/**/*.eval", recursive=True))
print(f"luna ${luna_spend:.4f}; projected nemotron ${proj:.4f}; billed r2+r4 ${billed:.4f}", file=sys.stderr)
why = []
if luna_spend + proj > 1.20: why.append("luna + projected nemotron over 1.20")
if billed + proj > 9.50: why.append("billed + projected over 9.50")
print(f"{max(1.20 - luna_spend, 0):.4f}|{'; '.join(why)}")
PY
)
STOP=${CHECK%%|*}; WHY=${CHECK#*|}
if [[ $MODE == paid && -n $WHY ]]; then echo "SKIP nemotron35: $WHY"; exit 0; fi
[[ -n $WHY ]] && echo "dry: nemotron35 would be skipped ($WHY); dry run goes on"
dev/py.sh python -u dev/launch_r4_nemotron.py $MODE $NEMO $COMMON --stop-at $STOP
