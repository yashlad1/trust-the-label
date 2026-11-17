#!/bin/zsh
# Split run: stage 3 beside stage 2, one stage-2 process per gate per stage-1 log.
# Usage: dev/run_split.sh paid|dry <out prefix> <wording json> [epochs]     paid is PAID: Yash's go only
# STAGE1_LOGS (env, comma list): reuse these stage-1 logs; unset runs stage 1 first, in the foreground. A dry run needs it (scripted stage-1 logs: plain mockllm stores no calls).
# JOBS (env): job files to run, passed as --jobs to every process (the default is the delete jobs; FP4 sets ALL_JOBS)
# Yash sets the per-process stop values per go (dollars, per process); together they must add up to the run's cap.
STOP_S1=2.0       # stage 1 (only when STAGE1_LOGS is unset)
STOP_S3=3.0       # the one stage-3 process
STOP_LUNA=1.0     # each luna stage-2 process (one per stage-1 log)
STOP_NEMO=1.0     # each nemotron35 stage-2 process (one per stage-1 log)
[[ $1 == (paid|dry) && -n $3 ]] || { echo "usage: dev/run_split.sh paid|dry <out prefix> <wording json> [epochs]"; exit 1; }
MODE=$1 P=$2 W=$3 E=${4:-2}
COMMON=(--wording $W --epochs $E ${=JOBS:+--jobs $JOBS})
if [[ -z $STAGE1_LOGS ]]; then
  dev/py.sh python -u dev/pipeline.py $MODE $P-stage1 $COMMON --no-stage2 --no-stage3 --stop-at $STOP_S1 || exit 1
  STAGE1_LOGS=$(python3 -c 'import json,sys; print(",".join(json.load(open(sys.argv[1]))["stage1"]))' $P-stage1/manifest.json)
fi
launch() {  # launch <name> <args...>: detached, own session, stdout to <prefix>-<name>.out
  local n=$1; shift
  perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' -- caffeinate -is dev/py.sh python -u dev/pipeline.py $MODE $P-$n $COMMON "$@" \
    > $P-$n.out 2>&1 < /dev/null &
  echo "$n PID $! out $P-$n.out"
}
launch stage3 --stage1-logs $STAGE1_LOGS --no-stage2 --stop-at $STOP_S3
i=0
for log in ${(s:,:)STAGE1_LOGS}; do
  i=$((i+1))
  launch luna-$i --stage1-logs $log --gates luna --no-stage3 --stop-at $STOP_LUNA
  launch nemotron35-$i --stage1-logs $log --gates nemotron35 --no-stage3 --stop-at $STOP_NEMO
done
