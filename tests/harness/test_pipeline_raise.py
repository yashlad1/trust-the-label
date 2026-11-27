"""dev/pipeline.py: any error while building or running a stage ends like a STOP:
non-zero exit, one "STOP:" line naming the error, no traceback, manifest.json with "stopped" and "logs"."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDING = ROOT / "src/trustlabel/scenarios/wording.json"
DELETE = "src/trustlabel/scenarios/delete.json"


def sh(tmp, name, cmd):
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    env["INSPECT_LOG_DIR"] = os.path.join(tmp, name + "_inspect")
    return subprocess.run([sys.executable, *cmd], capture_output=True, text=True, timeout=900, cwd=ROOT, env=env)


def check(tmp, name, *extra, wording=WORDING):
    s1 = sh(tmp, "s1_" + name, ["dev/scripted_stage1.py", os.path.join(tmp, "s1_" + name), "--jobs", DELETE, "--limit", "2"])
    assert s1.returncode == 0, "setup: scripted stage 1 failed\n" + s1.stderr[-600:]
    log = s1.stdout.strip().splitlines()[-1]
    out = os.path.join(tmp, name)
    p = sh(tmp, name, ["dev/pipeline.py", "dry", out, "--wording", str(wording), "--stage1-logs", log, *extra])
    tail = "\n--- stderr tail ---\n" + p.stderr[-800:]
    assert p.returncode != 0, name + ": exit code must not be 0" + tail
    assert "Traceback" not in p.stdout + p.stderr, name + ": a Python traceback was printed" + tail
    stops = [l for l in (p.stdout + "\n" + p.stderr).splitlines() if l.startswith("STOP:")]
    assert len(stops) == 1, name + ": need exactly one line starting 'STOP:', got %r" % stops + tail
    mp = os.path.join(out, "manifest.json")
    assert os.path.exists(mp), name + ": manifest.json missing" + tail
    m = json.load(open(mp))
    assert m.get("stopped") == stops[0], name + ": manifest 'stopped' %r must equal STOP line %r" % (m.get("stopped"), stops[0])
    assert isinstance(m.get("logs"), list), name + ": manifest 'logs' must be a list; got %r" % m.get("logs")
    print("case passed:", name)


with tempfile.TemporaryDirectory() as tmp:
    check(tmp, "run_error", "--stage2-epochs", "0")

    w = json.load(open(WORDING))
    del w[next(iter(w))]
    broken = os.path.join(tmp, "wording_missing_job.json")
    json.dump(w, open(broken, "w"))
    check(tmp, "build_error", wording=broken)

print("test_pipeline_raise: all checks passed")
