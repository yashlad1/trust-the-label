#!/bin/zsh
# FP3 pilot at the final code, all three stages, from the repo root.
#   dev/launch_pilot.sh dry <stage-1 logs, comma list>    fake model: stage 1 alone, then stages 2 and 3 on the given logs
#   dev/launch_pilot.sh paid                              PAID: Yash's go only. Start it detached (it runs stage 1 in the
#                                                         foreground, then stage 3 and the four stage-2 processes detached)
# Jobs: dev/pilot-jobs (12 jobs, both versions). Stops: the pilot's go, passed to dev/run_split.sh through the environment.
MODE=$1
[[ $MODE == paid || ( $MODE == dry && -n $2 ) ]] || { echo "usage: dev/launch_pilot.sh dry <stage-1 logs, comma list> | paid"; exit 1; }
cd ${0:A:h}/.. || exit 1
echo "code: $(git rev-parse --short HEAD), tracked changes: $(git status --porcelain --untracked-files=no | wc -l | tr -d ' ')"
export JOBS=dev/pilot-jobs/delete.json,dev/pilot-jobs/send.json,dev/pilot-jobs/pay.json,dev/pilot-jobs/publish.json
export STOP_S1=0.10 STOP_LUNA=0.50 STOP_NEMO=0.75 STOP_S3=0.20
W=src/trustlabel/scenarios/wording.json
if [[ $MODE == paid ]]; then OUT=logs/fp3-pilot-final; else OUT=logs/dry/fp3-pilot-final; fi
[[ -e $OUT ]] && { echo "STOP: $OUT already exists"; exit 1; }
mkdir -p $OUT
if [[ $MODE == paid ]]; then
  unset STAGE1_LOGS
  dev/run_split.sh paid $OUT/final $W 1
else
  dev/py.sh python -u dev/pipeline.py dry $OUT/final-stage1 --wording $W --epochs 1 --jobs $JOBS --no-stage2 --no-stage3 || exit 1
  STAGE1_LOGS=$2 dev/run_split.sh dry $OUT/final $W 1
fi
