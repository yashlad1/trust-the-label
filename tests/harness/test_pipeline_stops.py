"""dev/pipeline.py dry runs that stop early still write manifest.json and print a STOP line."""
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
    return [l for l in (p.stdout + "\n" + p.stderr).splitlines() if l.startswith("STOP")]


with tempfile.TemporaryDirectory() as tmp:
    # Test 1: spend limit
    p, out = run(tmp, "spend", "--stop-at", "-1")
    tail = p.stdout[-600:] + p.stderr[-600:]
    assert p.returncode != 0, "spec 1: spend stop must exit non-zero\n" + tail
    assert stop_lines(p), "spec 1: spend stop must print a line starting STOP\n" + tail
    mp = os.path.join(out, "manifest.json")
    assert os.path.exists(mp), "spec 1: manifest.json must exist after a spend stop\n" + tail
    json.load(open(mp))

print("test_pipeline_stops: all checks passed")
