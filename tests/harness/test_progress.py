"""Checks dev/progress.sh from the spec (logs in subfolders, NY zone abbreviation); run: uv run python tests/harness/test_progress.py"""
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from inspect_ai.log import read_eval_log, write_eval_log

ROOT = Path.cwd()


def progress(*dirs):
    r = subprocess.run(["dev/progress.sh", *map(str, dirs)], cwd=ROOT, capture_output=True, text=True)
    return r.stdout + r.stderr


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    with zipfile.ZipFile(ROOT / "sample_records/dry_run_fake_model.zip") as z:
        z.extractall(tmp)
    step = tmp / "dry_run" / "stage2-luna-smoke"
    step_log = next(step.glob("*.eval"))

    # Check 1: parent folder lists logs of subfolders
    out = progress(tmp / "dry_run")
    named = sum(1 for p in (tmp / "dry_run").rglob("*.eval") if p.name in out)
    assert named >= 2, \
        "spec 1: passing the parent folder must list every step's log, got: " + repr(out)
    out = progress(step)
    assert step_log.name in out, \
        "spec 1: a step folder must list its log, got: " + repr(out)

    # Check 2: unfinished log shows the right New York abbreviation
    log = read_eval_log(str(step_log))
    planned = len(log.samples)
    assert planned >= 2, "test setup: need at least 2 samples"
    log.status = "started"
    log.samples = log.samples[: planned // 2]
    log.eval.dataset.samples = planned
    log.results = None
    unf = tmp / "unfinished"
    unf.mkdir()
    write_eval_log(log, str(unf / step_log.name))
    out = progress(unf)
    assert "UTC" in out, "spec 2: unfinished log line must show a UTC finish time, got: " + repr(out)
    started = datetime.fromisoformat(log.stats.started_at)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    finish = max(now, started + (now - started) * planned / (planned // 2))
    want = finish.astimezone(ZoneInfo("America/New_York")).strftime("%Z")
    other = "EDT" if want == "EST" else "EST"
    assert want in out, f"spec 2: New York time must carry {want} for the finish time, got: " + repr(out)
    assert other not in out, f"spec 2: must not print {other} when New York is on {want}, got: " + repr(out)

print("test_progress: all checks passed")
