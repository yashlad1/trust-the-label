# FP3 task 20 (docs/fp3-tasks.html): runs table and measure tables from a run's records
"""Runs table: one row per log, with failed samples, wall time, tokens and billed cost.
Given manifests, it then prints the measure tables of trustlabel.analysis.rates: stage 1, stage 2 (per gate, with its
reference lines, then the hypothesis tables H1-H6, intent, wording, fatigue and flips of trustlabel.analysis.hypotheses, and the robustness table)
and stage 3, then live versus replay. Given .eval files, it prints the runs table only.

  dev/py.sh python dev/report.py <manifest.json> [<manifest.json> ...]
  dev/py.sh python dev/report.py <log.eval> [<log.eval> ...]

manifest: {"stage1": [path, ...], "stage2": {gate: path}, "stage3": {policy label: path}, ...}
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from inspect_ai.log import read_eval_log

from trustlabel.analysis.hypotheses import (fatigue, flip_table, h6_report, hypotheses, intent_report, live_vs_replay,
                                            robustness, wording_report)
from trustlabel.analysis.rates import (failed, pct, reference_table, stage1_table, stage2_rows, stage2_table, stage3_table,
                                       standard)

SCORER = {"stage1": None, "stage2": "gate_outcome", "stage3": "final_state_scorer"}  # stage 1: no scorer, it stores episodes


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
                     pct(bad, len(smp)) if smp else "-",
                     f"{wall / 60:.1f}" if wall is not None else "-",
                     *(sum(getattr(x, f) or 0 for x in u) if u else "-" for f in ("input_tokens", "output_tokens", "total_tokens")),
                     f"${c:.4f}" if c is not None else "not recorded"))
    head = ["stage", "model or gate", "samples", "failed samples", "wall time (min)", "input tokens", "output tokens",
            "total tokens", "billed cost"]
    return "\n".join(["## Runs", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
                     + ["| " + " | ".join(map(str, r)) + " |" for r in body])


def safe(fn, gate, paths, rows, failed_n):
    """fn's table, or a visible note when a setting it needs is absent from this gate's rows."""
    try:
        return fn(gate, paths, rows, failed_n)
    except ValueError as e:
        return f"**{fn.__name__}, gate {gate}: not in these logs ({e})**\n"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1:]
    print(runs(entries(arg)))
    print("\nRead it as one row per log. A failed sample errored or has no score from its stage's scorer; it is counted "
          "here and never as a success. Wall time is the log's start to end; billed cost is what the provider reported, "
          f"'not recorded' if it reported none. Source: {', '.join(arg)}")
    if all(a.endswith(".json") for a in arg):
        rows = entries(arg)
        s1 = [p for st, _, p in rows if st == "stage1"]
        if s1:
            print("\n## Stage 1\n")
            print(stage1_table(s1))
        gates = {}
        for st, g, p in rows:
            if st == "stage2":
                gates.setdefault(g, []).extend(p if isinstance(p, list) else [p])
        if gates:
            print("\n## Stage 2")
        for g, paths in gates.items():
            rs, failed_n = stage2_rows(paths)
            print()
            print(stage2_table(g, paths, rs, failed_n))
            print()
            print(safe(reference_table, g, paths, rs, failed_n))
            prints = []
            if standard(rs):
                prints += [hypotheses, fatigue, flip_table]
            if any(r["prompt"] == "intent" for r in rs):
                prints.append(intent_report)
            if any(r["prompt"] == "alignment" for r in rs):
                prints.append(h6_report)
            if any(r["request"].endswith(("_calm", "_loud")) for r in rs):
                prints.append(wording_report)
            for t in prints:
                print()
                print(safe(t, g, paths, rs, failed_n))
            text = safe(robustness, g, paths, rs, failed_n)
            if text:
                print()
                print(text)
        s3 = {g: p for st, g, p in rows if st == "stage3"}
        if s3:
            print("\n## Stage 3\n")
            print(stage3_table(s3))
        ms = [json.loads(Path(a).read_text()) for a in arg]
        live = next((m["live_gate"] for m in ms if m.get("live_gate")), None)
        if s3 and live:
            print("\n## Live versus replay\n")
            print(live_vs_replay(s3, gates[live]) if gates.get(live)
                  else f"(live gate {live} has no stage-2 logs in these manifests)")
