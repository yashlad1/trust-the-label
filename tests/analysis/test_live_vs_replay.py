"""stage2_rows rows carry the agent; live_vs_replay compares live stage-3 first-irreversible rates with replayed stage 2."""
import json
import tempfile
import zipfile
from pathlib import Path

from inspect_ai.log import read_eval_log

from trustlabel.analysis.hypotheses import live_vs_replay
from trustlabel.analysis.rates import failed, pct, stage2_rows

ROOT = Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory() as tmp:
    with zipfile.ZipFile(ROOT / "sample_records" / "dry_run_fake_model.zip") as z:
        z.extractall(Path(tmp) / "sample_records")
    m = json.loads((Path(tmp) / "sample_records" / "dry_run" / "manifest.json").read_text())
    stage3 = {label: str(Path(tmp) / p) for label, p in m["stage3"].items()}
    live = str(Path(tmp) / m["stage2"][m["live_gate"]])

    rows, failed2 = stage2_rows([live])
    assert rows

    # every row names the agent of a stored call in that log
    agents = {s.metadata["call"]["agent"] for s in read_eval_log(live).samples}
    for r in rows:
        assert "agent" in r and r["agent"] in agents, r

    out = live_vs_replay(stage3, [live])
    lines = out.splitlines()
    assert lines[0].startswith("**Live versus replay:") and lines[0].endswith("**"), out
    body = [l for l in lines if any(l.startswith(f"| {label} |") for label in stage3)]
    assert len(body) == len(stage3), out
    assert [l.split("|")[1].strip() for l in body] == list(stage3), out  # dict order

    failed3 = none_reached = 0
    for label, line in zip(stage3, body):
        log = read_eval_log(stage3[label])
        ta = log.eval.task_args
        n = k = 0
        for s in log.samples:
            if failed(s, "final_state_scorer"):
                failed3 += 1
                continue
            if s.metadata["scenario"]["version"] != "unneeded":
                continue
            irr = [d for d in s.store["episode"]["decisions"] if d["irreversible"]]
            if irr:
                n += 1
                k += irr[0]["outcome"] == "allowed"
            else:
                none_reached += 1
        mine = [r for r in rows
                if r["policy"] == ta["policy"] and r["warning"] == ta["warning"]
                and (ta["policy"] == "gate_on_call" or r["label"] == ta["label"])
                and r["name"] == ta["name"] and r["request"] == "own" and r["prompt"] == "plain"
                and r["version"] == "unneeded" and r["stored_version"] == "unneeded"
                and r["agent"] == log.eval.model]
        rk = sum(r["answer"] == "allowed" for r in mine)
        if n == 0 or not mine:
            diff = "–"
        else:
            diff = f"{round(100 * k / n - 100 * rk / len(mine)):+d}".replace("+0", "0")
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert cells == [label, pct(k, n), pct(rk, len(mine)), diff], (cells, k, n, rk, len(mine), diff)

    src = [l for l in lines if l.startswith("Source")]
    assert src and src[0].endswith(f"{failed3} failed stage-3 samples and {failed2} failed stage-2 samples (not counted); {none_reached} unneeded episodes never reached an irreversible call (not in n)"), src

print("ok")
