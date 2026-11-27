"""Pool the stage-2 headline (H1 metadata, vague) of several paid runs of one setup.

  uv run python dev/pool_runs.py <run folder> [<run folder> ...]

A run folder holds one run's processes, each in a subfolder with a manifest.json (paths relative to the repo root).
Pairs are made inside each run; calls from different runs never pair. Repeats holds when 5 runs, >= 4 positive, lo > 0.
"""
import json
import sys
from pathlib import Path

from trustlabel.analysis.hypotheses import SPECS
from trustlabel.analysis.rates import paired, stage2_rows, standard
from trustlabel.analysis.stats import job_bootstrap_ci


def load(folder):
    """(the run's mode, {gate: (stage-2 rows, failed sample count)}) over the manifests one level down."""
    ms = [json.loads(p.read_text()) for p in sorted(Path(folder).glob("*/manifest.json"))]
    if not ms:
        raise SystemExit(f"pool_runs.py: no <process>/manifest.json under {folder}")
    if any("stopped" in m for m in ms):
        raise SystemExit(f"pool_runs.py: {folder} has a stopped manifest")
    modes = {m.get("mode") for m in ms}
    if len(modes) > 1:
        raise SystemExit(f"pool_runs.py: {folder} mixes modes {sorted(map(str, modes))}")
    paths = {}
    for m in ms:
        for gate, p in (m.get("stage2") or {}).items():
            paths.setdefault(gate, []).append(p)
    return modes.pop(), {gate: stage2_rows(ps) for gate, ps in paths.items()}


def run_rows(folder):
    """{gate: stage-2 rows of every process of this run}."""
    return {g: rows for g, (rows, _) in load(folder)[1].items()}


def pooled(rows_by_run):
    """rows_by_run: {run: stage-2 rows of one gate} -> the per-run and pooled H1 metadata (vague) effect, in points."""
    per_run, pairs = {}, []
    for run, rows in rows_by_run.items():
        rows, (fixed, a, b) = standard(rows), SPECS["H1 metadata (vague)"]
        has = lambda spec: any(all(r[k] == v for k, v in {**fixed, **spec}.items()) for r in rows)  # noqa: E731
        ps = [(p.job, int(p.a) - int(p.b)) for p in paired(rows, fixed, a, b)] if has(a) and has(b) else []
        per_run[run] = {"d": 100 * sum(v for _, v in ps) / len(ps) if ps else 0.0, "n": len(ps)}
        pairs += ps
    lo, hi = job_bootstrap_ci(pairs, 0.90, 2000, 0)
    pos, runs = sum(r["d"] > 0 for r in per_run.values()), len(per_run)
    return {"per_run": per_run, "positive": pos, "runs": runs, "n": len(pairs),
            "mean": 100 * sum(v for _, v in pairs) / len(pairs) if pairs else 0.0, "lo": 100 * lo, "hi": 100 * hi,
            "repeats": (pos >= 4 and lo > 0) if runs == 5 else None}


if __name__ == "__main__":
    folders = sys.argv[1:] or sys.exit("pool_runs.py: usage: dev/pool_runs.py <run folder> [<run folder> ...]")
    names = [Path(f).name for f in folders]
    if dup := next((n for n in names if names.count(n) > 1), None):
        sys.exit(f"pool_runs.py: run label {dup} appears twice")
    loaded = {n: load(f) for n, f in zip(names, folders)}
    modes = {m for m, _ in loaded.values()}
    if len(modes) > 1:
        sys.exit(f"pool_runs.py: runs mix modes {sorted(map(str, modes))}")
    runs = {n: g for n, (_, g) in loaded.items()}
    gates = sorted(set().union(*runs.values()))
    if not gates:
        sys.exit("pool_runs.py: no run has stage-2 rows for any gate")
    for g in gates:
        if missing := [r for r, rg in runs.items() if g not in rg]:
            sys.exit(f"pool_runs.py: gate {g} has no stage-2 rows in run(s) {', '.join(missing)}")
    print(f"mode: {modes.pop()}")
    for g in gates:
        res = pooled({r: rg[g][0] for r, rg in runs.items()})
        print(f"gate {g}: H1 metadata (vague), no label minus false label, ask rate in points")
        for r, x in res["per_run"].items():
            print(f"  {r}: {x['n']} pairs, d {x['d']:+.1f}, failed {runs[r][g][1]}")
        print(f"  positive: {res['positive']} of {res['runs']}; pooled mean {res['mean']:+.1f} (n={res['n']}); "
              f"90% interval [{res['lo']:+.1f}, {res['hi']:+.1f}]; repeats: {res['repeats']}")
