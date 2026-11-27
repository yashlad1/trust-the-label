"""dev/report.py prints a STOPPED line for a manifest with a "stopped" key. Run: dev/py.sh python tests/harness/test_report_stopped.py"""
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "dev" / "report.py"


def run(args, cwd):
    return subprocess.run([sys.executable, str(REPORT), *map(str, args)], cwd=cwd, capture_output=True, text=True)


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    with zipfile.ZipFile(ROOT / "sample_records" / "dry_run_fake_model.zip") as z:
        z.extractall(tmp / "sample_records")
    base = json.loads((tmp / "sample_records" / "dry_run" / "manifest.json").read_text())

    plain = tmp / "plain.json"
    plain.write_text(json.dumps(base))
    r = run([plain], tmp)
    assert r.returncode == 0, r.stderr
    assert "STOPPED" not in r.stdout, "spec 5: no STOPPED line without a stopped key"

    text = "stopped early: error rate passed 5% (7/100)"
    stopped = tmp / "stopped.json"
    stopped.write_text(json.dumps(dict(base, stopped=text)))
    r = run([stopped], tmp)
    assert r.returncode == 0, r.stderr
    lines = [ln for ln in r.stdout.splitlines() if "STOPPED" in ln]
    assert len(lines) == 1, ("spec 5: one STOPPED line", r.stdout[:800])
    assert str(stopped) in lines[0] and text in lines[0], ("spec 5: path and text on the line", lines[0])
    assert r.stdout.index("STOPPED") < r.stdout.index("## Runs"), "spec 5: STOPPED line before the runs table"

print("test_report_stopped: all checks passed")
