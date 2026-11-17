# FP3 task 20 (docs/fp3-tasks.html): runs table from a run's records (measure tables arrive with rates.py)
"""Runs table: one row per log, with failed samples, wall time, tokens and billed cost.

  dev/py.sh python dev/report.py <manifest.json> [<manifest.json> ...]
  dev/py.sh python dev/report.py <log.eval> [<log.eval> ...]

manifest: {"stage1": [path, ...], "stage2": {gate: path}, "stage3": {policy label: path}, ...}
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from inspect_ai.log import read_eval_log

SCORER = {"stage1": None, "stage2": "gate_outcome", "stage3": "final_state_scorer"}  # stage 1: no scorer, it stores episodes


def failed(s, scorer):
    """A sample that errored or never got its stage's score (stage 1: never stored its episode)."""
    return bool(s.error) or (scorer not in (s.scores or {}) if scorer else "episode" not in (s.store or {}))


def cost(log):
    """Billed cost: usage.cost on every model event; None if no event carries one."""
    c = [((e.call.response or {}).get("usage") or {}).get("cost") for s in log.samples or []
         for e in s.events if e.event == "model" and e.call]
    c = [x for x in c if x is not None]
    return sum(c) if c else None


def entries(arg):
    """(stage, model or gate, log path) per log: from the manifest's keys, or from each log's own task and model."""
    if all(a.endswith(".json") for a in arg):  # several manifests (a split run) read as one
        ms = [json.loads(Path(a).read_text()) for a in arg]
        return ([("stage1", None, p) for p in dict.fromkeys(p for m in ms for p in m.get("stage1") or [])]
                + [("stage2", g, p) for m in ms for g, p in (m.get("stage2") or {}).items()]
                + [("stage3", g, p) for m in ms for g, p in (m.get("stage3") or {}).items()])
    return [(None, None, p) for p in arg]


def runs(rows):
    body = []
    for stage, name, p in rows:
        log = read_eval_log(p)
        stage = stage or log.eval.task
        smp = log.samples or []
        bad = sum(failed(s, SCORER.get(stage)) for s in smp)
        try:
            wall = (datetime.fromisoformat(log.stats.completed_at) - datetime.fromisoformat(log.stats.started_at)).total_seconds()
        except (TypeError, ValueError):
            wall = None
        u = list((log.stats.model_usage or {}).values())
        c = cost(log)
        body.append((stage, name or log.eval.model, len(smp),
                     f"{100 * bad / len(smp):.0f}% ({bad}/{len(smp)})" if smp else "-",
                     f"{wall / 60:.1f}" if wall is not None else "-",
                     *(sum(getattr(x, f) or 0 for x in u) if u else "-" for f in ("input_tokens", "output_tokens", "total_tokens")),
                     f"${c:.4f}" if c is not None else "not recorded"))
    head = ["stage", "model or gate", "samples", "failed samples", "wall time (min)", "input tokens", "output tokens",
            "total tokens", "billed cost"]
    return "\n".join(["## Runs", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
                     + ["| " + " | ".join(map(str, r)) + " |" for r in body])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1:]
    print(runs(entries(arg)))
    print("\nRead it as one row per log. A failed sample errored or has no score from its stage's scorer; it is counted "
          "here and never as a success. Wall time is the log's start to end; billed cost is what the provider reported, "
          f"'not recorded' if it reported none. Source: {', '.join(arg)}")
