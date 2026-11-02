#!/bin/zsh
# Progress of runs: per .eval log, status, done/planned, errors, cost, linear finish time (UTC, New York).
# Usage: dev/progress.sh logs/stage1 [more log dirs]
[ $# -ge 1 ] || { echo "usage: dev/progress.sh <log dir> [...]"; exit 1; }
cd "${0:A:h:h}" || exit 1
exec dev/py.sh python - "$@" <<'PY'
import sys, glob, datetime as dt
from zoneinfo import ZoneInfo
from inspect_ai.log import read_eval_log, read_eval_log_sample_summaries
now = dt.datetime.now(dt.timezone.utc)
for d in sys.argv[1:]:
    total = 0.0
    print(f"== {d}")
    for p in sorted(glob.glob(f"{d}/*.eval")):
        h = read_eval_log(p, header_only=True)
        s = read_eval_log_sample_summaries(p)
        # OpenRouter's billed usage.cost per call (Inspect has no prices for our models; run.sh logs every response).
        # Only calls made after this log was created, so an eval-retry's copied samples aren't counted twice.
        created = dt.datetime.fromisoformat(h.eval.created)
        cost = sum(((e.call.response or {}).get("usage") or {}).get("cost") or 0
                   for x in read_eval_log(p).samples or [] for e in x.events
                   if e.event == "model" and e.call and e.timestamp >= created)
        total += cost
        err = sum(1 for x in s if x.error)
        n = (len(h.eval.dataset.sample_ids or []) or h.eval.dataset.samples or 0) * (h.eval.config.epochs or 1)  # sample_ids honours --limit
        k = len(s)
        line = f"{p.split('/')[-1]} {h.eval.task} {h.eval.model} {h.status} {k}/{n} errors={err} cost=${cost:.4f}"
        if h.status == "started" and k and n:
            end = now + (now - created) * (n - k) / k
            line += f" {100*k/n:.0f}% finish {end:%H:%M} UTC / {end.astimezone(ZoneInfo('America/New_York')):%H:%M} EDT"
        print(line)
    print(f"total cost ${total:.4f}")
PY
