"""H5 rerun: the wording rows on the final wording file over the full run's stored first calls, gates luna and
nemotron35 (the full run's settings: pins, effort, connections). Every wording row runs.

  dev/py.sh python dev/launch_h5.py dry|paid <the full run's stage-1 manifest.json>     paid: Yash's go only

Each gate runs a 12-sample smoke first; its full run starts only if the smoke passes and H5's billed spend so far plus
the smoke's projection stays at or under CAP. Logs: logs/h5-wording/ (dry: logs/dry/h5-wording/).
"""
import json
import subprocess
import sys
from pathlib import Path

from inspect_ai import eval as run_eval
from inspect_ai.log import read_eval_log

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dev.pipeline import COMMON, model_kwargs  # the full run's gate settings
from trustlabel.analysis.rates import failed
from trustlabel.harness.tasks import stage2

ROOT = Path(__file__).resolve().parents[1]
PAID, DRY = ROOT / "logs/h5-wording", ROOT / "logs/dry/h5-wording"
SCENARIOS = ",".join(str(ROOT / f"src/trustlabel/scenarios/{k}.json") for k in ("delete", "send", "pay", "publish"))
WORDING = str(ROOT / "src/trustlabel/scenarios/wording.json")
REQUESTS = ("unneeded_calm", "unneeded_loud", "wanted_calm", "wanted_loud")
GATES = ("luna", "nemotron35")
CAP = 1.50  # dollars of billed spend for H5 in all: both gates, smokes included


def spend(paths):
    return sum(((e.call.response or {}).get("usage") or {}).get("cost") or 0
               for p in paths for s in read_eval_log(p).samples or [] for e in s.events if e.event == "model" and e.call)


def git(*a):
    try:
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def go(gate, dry, task, ids, stage1):
    out = (DRY if dry else PAID) / gate
    if out.exists():
        sys.exit(f"STOP: {out} exists")
    out.mkdir(parents=True)

    def run(step, sample_ids):
        log = run_eval(task, log_dir=str(out / step), sample_id=sample_ids, **model_kwargs(gate, dry), **COMMON)[0]
        print(f"{step}: {log.status}, {len(log.samples or [])} samples", flush=True)
        return log

    smoke = run(f"{gate}-smoke", ids[::len(ids) // 12][:12])
    scored = [s for s in smoke.samples or [] if not failed(s, "gate_outcome")]
    unreadable = sum(s.scores["gate_outcome"].value["unreadable"] for s in scored)
    cost = 0 if dry else spend([smoke.location])
    projected = cost / 12 * len(ids)
    total = 0 if dry else spend([str(q) for q in PAID.glob("**/*.eval")])  # H5 so far, this smoke included
    print(f"{gate} smoke: {len(scored)}/12 scored, {unreadable} unreadable; smoke ${cost:.4f}, projected ${projected:.2f}; "
          f"H5 spend so far ${total:.2f} (cap ${CAP:.2f})", flush=True)
    ok = smoke.status == "success" and len(scored) == 12 and unreadable <= 3 and total + projected <= CAP
    if not ok and not dry:
        print(f"{gate}: full run skipped", flush=True)
        return
    full = run(gate, ids)
    status = git("status", "--porcelain", "--untracked-files=no")
    (out / "manifest.json").write_text(json.dumps({
        "stage1": stage1, "stage2": {gate: full.location}, "stage3": {}, "live_gate": "luna",
        "smokes": {f"{gate}-smoke": smoke.location}, "mode": "dry" if dry else "paid", "command": sys.argv,
        "code": {"git_sha": git("rev-parse", "HEAD"), "dirty": None if status is None else bool(status)},
        "wording": WORDING, "cap": CAP, "spend": 0 if dry else spend([smoke.location, full.location]),
        "conditions": "H5: wording rows only, vague name, gate with labels, label none/false, warning off, plain",
    }, indent=2))
    print(f"{gate} done: {out}/manifest.json", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("dry", "paid"):
        sys.exit(__doc__)
    stage1 = [str(p) for p in json.loads(Path(sys.argv[2]).read_text())["stage1"]]
    task = stage2(logs=",".join(stage1), scenarios=SCENARIOS, wording_rows=WORDING)
    ids = sorted(s.id for s in task.dataset if s.metadata["request"] in REQUESTS)
    if len(ids) != 1872:
        sys.exit(f"STOP: {len(ids)} wording-row sample ids, expected 1872 (8 per stored first call, 234 calls)")
    for gate in GATES:
        go(gate, sys.argv[1] == "dry", task, ids, stage1)
