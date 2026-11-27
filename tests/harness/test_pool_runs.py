"""dev/pool_runs.py pools the stage-2 headline of several runs. Run: uv run python tests/harness/test_pool_runs.py"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from dev.pool_runs import pooled, run_rows  # noqa: E402,F401
from trustlabel.analysis.stats import job_bootstrap_ci  # noqa: E402

ENV = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
HEAD = dict(policy="gate_with_labels", stored_version="unneeded", request="own", name="vague", warning=False, prompt="plain")


def row(call, job, label, ask, **over):
    r = dict(call=call, job=job, kind="delete", tool="t", answer="a", ask=ask, unreadable=False, version="v1", agent="ag", label=label)
    r.update(HEAD)
    r.update(over)
    return r


def pair_rows(calls, vs):
    """calls: list of (call, job); vs: v per call. Returns headline rows (false row listed before none row)."""
    out = []
    for i, ((call, job), v) in enumerate(zip(calls, vs)):
        none, false = {1: (True, False), -1: (False, True), 0: ((i % 2 == 0),) * 2}[v]
        out += [row(call, job, "false", false), row(call, job, "none", none)]
    return out


def oracle(rows_by_run_v):
    pairs = [(job, v) for calls, vs in rows_by_run_v for (_, job), v in zip(calls, vs)]
    lo, hi = job_bootstrap_ci(pairs, 0.90, 2000, 0)
    return 100 * lo, 100 * hi, 100 * sum(v for _, v in pairs) / len(pairs)


def close(a, b):
    return abs(a - b) < 1e-9


# Part 1: constructed rows, three runs, same call ids everywhere
calls = [(f"c{i}", f"j{i % 3}") for i in range(6)]
V = {"A": [1, 1, 0, -1, 0, 1], "B": [0, 0, 1, 0, -1, 0], "C": [-1, 0, 0, 1, 1, 0]}
rows_by_run = {}
for name, vs in V.items():
    rows = pair_rows(calls, vs)
    # noise outside the headline cell: must change nothing
    for call, job in calls:
        rows += [row(call, job, "true", True), row(call, job, "none", True, name="other"),
                 row(call, job, "false", False, name="other"), row(call, job, "none", True, warning=True),
                 row(call, job, "false", False, warning=True), row(call, job, "none", True, prompt="fancy"),
                 row(call, job, "false", False, prompt="fancy"), row(call, job, "none", True, policy="other")]
    rows_by_run[name] = rows
res = pooled(rows_by_run)
for name, vs in V.items():
    assert close(res["per_run"][name]["d"], 100 * sum(vs) / len(vs)), res
    assert res["per_run"][name]["n"] == 6, res
assert res["positive"] == 2 and res["runs"] == 3 and res["n"] == 18, res
lo, hi, mean = oracle([(calls, vs) for vs in V.values()])
assert close(res["mean"], mean) and close(res["lo"], lo) and close(res["hi"], hi), (res, lo, hi, mean)
assert res["repeats"] is None, res
print("part 1 ok: constructed rows, three runs, per_run/positive/n/mean/lo/hi/repeats")


# Part 1b: one run, in-cell rows give d; each look-alike set differs from the cell in ONE field and has the opposite ask
vs1b = [1, 1, 0, -1, 0, 1]
rows1b = pair_rows(calls, vs1b)
for over in (dict(request="swapped"), dict(warning=True), dict(name="honest"), dict(stored_version="wanted")):
    for call, job in calls:
        rows1b += [row(call, job, "none", False, **over), row(call, job, "false", True, **over)]  # v = -1 each
res = pooled({"only": rows1b})
assert close(res["per_run"]["only"]["d"], 100 * sum(vs1b) / 6) and res["per_run"]["only"]["n"] == 6, res
assert res["n"] == 6 and close(res["mean"], 100 * sum(vs1b) / 6), res
print("part 1b ok: look-alike rows differing in request, warning, name or stored_version are ignored")


# Part 2: five runs
jobs8 = [(f"c{i}", f"j{i % 8}") for i in range(40)]
good = {f"r{k}": pair_rows(jobs8, [1 if i % 4 else 0 for i in range(40)]) for k in range(5)}
res = pooled(good)
lo, hi, _ = oracle([(jobs8, [1 if i % 4 else 0 for i in range(40)])] * 5)
assert res["runs"] == 5 and res["positive"] == 5 and close(res["lo"], lo) and lo > 0, (res, lo)
assert res["repeats"] is True, res

calls20 = jobs8[:20]
vp = [1] + [0] * 19
vn = [-1] * 20
bad = {f"r{k}": pair_rows(calls20, vp) for k in range(4)}
bad["r4"] = pair_rows(calls20, vn)
res = pooled(bad)
lo, hi, _ = oracle([(calls20, vp)] * 4 + [(calls20, vn)])
assert res["positive"] == 4 and res["runs"] == 5 and close(res["lo"], lo) and lo <= 0, (res, lo)
assert res["repeats"] is False, res
print("part 2 ok: five runs, repeats True; four positive with lo <= 0 gives False")


def cli(*folders):
    r = subprocess.run(["uv", "run", "python", "dev/pool_runs.py", *map(str, folders)], cwd=ROOT, env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    def sh(*args):
        r = subprocess.run(["uv", "run", "python", *map(str, args)], cwd=ROOT, env=ENV, capture_output=True, text=True)
        assert r.returncode == 0, (args, r.stdout[-800:], r.stderr[-800:])
        return r.stdout

    scen = ROOT / "src/trustlabel/scenarios"
    out = sh("dev/scripted_stage1.py", tmp / "s1", "--jobs", scen / "delete.json", "--limit", "2")
    s1 = out.strip().splitlines()[-1].strip()
    sh("dev/pipeline.py", "dry", tmp / "base" / "final", "--jobs", scen / "delete.json", "--wording", scen / "wording.json",
       "--stage1-logs", s1, "--no-stage3")
    runs = [tmp / f"run{i}" for i in range(1, 6)]
    for d in runs:
        shutil.copytree(tmp / "base", d)
    gates = set()
    for m in (tmp / "base").rglob("manifest.json"):
        gates |= set(json.loads(m.read_text()).get("stage2", {}))
    assert gates, "dry run made no stage-2 manifest"

    # Part 3: CLI on five copies of a real dry run
    code, so, se = cli(*runs)
    assert code == 0 and "Traceback" not in so + se, (code, so[-800:], se[-800:])
    counts = set()
    clean_out = so
    for d in runs:
        ls = [ln for ln in so.splitlines() if d.name in ln]
        assert len(ls) == len(gates), (d.name, len(gates), so)
        for ln in ls:
            counts.add(int(re.findall(r"\d+", ln.split(d.name, 1)[1])[0]))
    assert len(counts) == 1 and counts != {0}, ("paired-call counts differ or are zero", counts, so)
    print("part 3 ok: CLI on five dry-run copies, exit 0, five run lines per gate, same paired-call count", counts)

    # Part 4: a stopped manifest
    m = next(runs[2].rglob("manifest.json"))
    m.write_text(json.dumps(dict(json.loads(m.read_text()), stopped="STOP: test")))
    code, so, se = cli(*runs)
    msg = [ln for ln in (so + se).splitlines() if ln.startswith("pool_runs.py:")]
    assert code != 0 and len(msg) == 1 and "Traceback" not in so + se, (code, so[-800:], se[-800:])
    print("part 4 ok: stopped manifest gives non-zero exit and one pool_runs.py: line")

    # Part 5: spec additions, each sub-check reports on its own
    fails = []

    def sub(tag, fn):
        try:
            fn()
        except BaseException as e:  # noqa: BLE001
            fails.append(f"({tag}) {type(e).__name__}: {str(e)[-700:]}")

    def fresh(tag):
        ds = []
        for i in range(1, 6):
            d = tmp / tag / f"run{i}"
            shutil.copytree(tmp / "base", d)
            ds.append(d)
        return ds

    def manifests(d):
        return sorted(d.glob("*/manifest.json"))

    def edit(path, **kw):
        m = json.loads(path.read_text())
        for k, v in kw.items():
            if v is DEL:
                m.pop(k, None)
            else:
                m[k] = v
        path.write_text(json.dumps(m))

    def one_line_error(folders):
        code, so, se = cli(*folders)
        msg = [ln for ln in (so + se).splitlines() if ln.startswith("pool_runs.py:")]
        assert code != 0 and len(msg) == 1 and "Traceback" not in so + se, (code, so[-400:], se[-400:])

    DEL = object()

    def check_a():
        rs = fresh("pa")
        before = cli(*rs)
        assert before[0] == 0, before
        m = manifests(rs[0])[0]
        ev = rs[0] / "evidence" / "x"
        ev.mkdir(parents=True)
        mm = json.loads(m.read_text())
        new = {}
        for g, pth in mm["stage2"].items():
            src = Path(pth) if Path(pth).is_absolute() else ROOT / pth
            dst = ev / f"copy_{g}.eval".replace("/", "_")
            shutil.copy(src, dst)
            new[g] = str(dst)
        (ev / "manifest.json").write_text(json.dumps(dict(mm, stage2=new)))
        after = cli(*rs)
        assert after[0] == 0, after
        lines = lambda o: [ln for ln in o.splitlines() if any(d.name in ln for d in rs)]
        assert lines(before[1]) == lines(after[1]) and lines(after[1]), (before[1], after[1])

    def check_b():
        a, b = tmp / "pb" / "a" / "run1", tmp / "pb" / "b" / "run1"
        shutil.copytree(tmp / "base", a)
        shutil.copytree(tmp / "base", b)
        one_line_error([a, b])

    def check_c():
        rs = fresh("pc")
        for i, d in enumerate(rs):
            for m in manifests(d):
                edit(m, stage2={} if i < 2 else DEL)
        one_line_error(rs)

    def check_d():
        empty = [dict(r, name="other") for r in pair_rows(calls, [1] * 6)]
        v1, v2 = [1, 1, 0, -1, 0, 1], [0, 1, 1, 0, 0, -1]
        res = pooled({"r1": pair_rows(calls, v1), "r2": empty, "r3": pair_rows(calls, v2)})
        assert res["per_run"]["r2"] == {"d": 0.0, "n": 0}, res
        assert res["runs"] == 3 and res["positive"] == 2 and res["n"] == 12, res
        assert close(res["mean"], 100 * (sum(v1) + sum(v2)) / 12), res

    def check_e():
        rs = fresh("pe")
        for d in rs:
            for m in manifests(d):
                edit(m, mode="dry")
        code, so, se = cli(*rs)
        assert code == 0 and "dry" in so, (code, so[-400:], se[-400:])
        edit(manifests(rs[1])[0], mode="paid")
        one_line_error(rs)

    def check_f():
        for d in runs:
            ls = [ln for ln in clean_out.splitlines() if d.name in ln]
            assert ls and all("failed 0" in ln for ln in ls), ls

    for tag, fn in (("a", check_a), ("b", check_b), ("c", check_c), ("d", check_d), ("e", check_e), ("f", check_f)):
        sub(tag, fn)
    for f in fails:
        print("part 5 FAIL", f)
    assert not fails, f"part 5: {len(fails)} sub-check(s) failed"
    print("part 5 ok: manifest depth, duplicate names, no gate, empty cell, mode, failed counts")

print("test_pool_runs: all checks passed")
