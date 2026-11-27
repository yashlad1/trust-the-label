"""dev/pipeline.py: a STOP is recorded in manifest.json ("stopped", "logs"); a clean finish has no "stopped"."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = os.environ.get("PIPELINE", "dev/pipeline.py")
WORDING = "src/trustlabel/scenarios/wording.json"


def run(tmp, name, *extra):
    out = os.path.join(tmp, name)
    env = dict(os.environ, INSPECT_LOG_DIR=os.path.join(tmp, name + "_inspect"))
    cmd = [sys.executable, PIPELINE, "dry", out, "--wording", WORDING, "--epochs", "1", *extra]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=ROOT, env=env)
    return p, out


def stop_lines(p):
    return [l.strip() for l in (p.stdout + "\n" + p.stderr).splitlines() if l.startswith("STOP")]


def resolve(entry, out):
    for base in ("", out, str(ROOT)):
        c = os.path.join(base, entry)
        if os.path.isfile(c):
            return c
    return None


with tempfile.TemporaryDirectory() as tmp:
    # Stopped run (smoke only)
    p, out = run(tmp, "spend", "--stop-at", "-1")
    tail = p.stdout[-600:] + p.stderr[-600:]
    lines = stop_lines(p)
    assert lines, "setup: no STOP line printed\n" + tail
    mp = os.path.join(out, "manifest.json")
    assert os.path.exists(mp), "setup: manifest.json missing\n" + tail
    m = json.load(open(mp))

    # spec 1
    assert "stopped" in m, "spec 1: manifest must have key 'stopped'; keys=%s" % sorted(m)
    assert m["stopped"].strip() == lines[0] or m["stopped"].strip() in lines, \
        "spec 1: 'stopped' must equal the printed STOP line: %r vs %r" % (m["stopped"], lines)

    # spec 2
    assert isinstance(m.get("logs"), list) and m["logs"], "spec 2: 'logs' must be a non-empty list; got %r" % m.get("logs")
    assert len(m["logs"]) == len(set(m["logs"])), "spec 2: 'logs' lists a file twice: %r" % m["logs"]
    for e in m["logs"]:
        assert e.endswith(".eval") and resolve(e, out), "spec 2: 'logs' entry is not an existing .eval file: %r" % e
    written = {os.path.basename(f) for d, _, fs in os.walk(tmp) for f in fs if f.endswith(".eval")}
    named = {os.path.basename(e) for e in m["logs"]}
    assert written <= named, "spec 2: .eval files written but not named in 'logs': %s" % sorted(written - named)

    # spec 3
    for k in ("stage1", "stage2", "stage3"):
        assert not m.get(k), "spec 3: %s must stay empty after the smoke stop; got %r" % (k, m.get(k))

    # spec 4: clean finish, stage 1 only
    p, out = run(tmp, "clean", "--no-stage2", "--no-stage3")
    tail = p.stdout[-600:] + p.stderr[-600:]
    assert p.returncode == 0, "spec 4: clean dry run must exit 0\n" + tail
    m = json.load(open(os.path.join(out, "manifest.json")))
    assert "stopped" not in m, "spec 4: a run with no STOP must have no 'stopped' key: %r" % m.get("stopped")

print("test_pipeline_stop_record: all checks passed")
