"""Checks spec 5c.8, 5c.9 and 5d with a fake model only. Run: uv run python tests/harness/test_cli_settings.py"""

import json
import os
import re
import subprocess
import sys
import tempfile
from functools import cache
from pathlib import Path

from inspect_ai import eval as run_eval
from inspect_ai.log import read_eval_log
from inspect_ai.model import get_model
from mock_agents import list_then_delete_first

from trustlabel.harness.tasks import stage2, stage3

REPO = Path(__file__).resolve().parents[2]
DELETE_JOBS = "src/trustlabel/scenarios/delete.json"
# guard: a stray real model call fails instead of spending; not the 5d.4 check
ENV = {
    k: v
    for k, v in os.environ.items()
    if k not in ("VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME") and not re.search("KEY|TOKEN|SECRET", k, re.I)
}


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, env=ENV, capture_output=True, text=True, timeout=600)


@cache
def fixture_jobs() -> tuple[str, str]:
    """Two job files: fx1 in the first, fx2 in the second."""
    folder = Path(tempfile.mkdtemp())
    paths = []
    for job in ("fx1", "fx2"):
        items = [{"id": f"{job}-i{i}", "name": f"{job} item {i}", "tags": ["t"], "status": "active"} for i in range(5)]
        ids = [it["id"] for it in items[:3]]
        rows = [
            {"id": job, "kind": "delete", "version": v, "request": f"{job}-request-{v}", "items": items, "needed": n}
            for v, n in (("unneeded", {"archive": ids}), ("wanted", {"delete": ids}))
        ]
        paths.append(str(folder / f"{job}.json"))
        Path(paths[-1]).write_text(json.dumps(rows))
    return paths[0], paths[1]


def one_log(log_dir: str):
    files = list(Path(log_dir).glob("*.eval"))
    assert len(files) == 1, f"expected exactly one .eval file in {log_dir}, got {len(files)}"
    return read_eval_log(str(files[0]))


def label_scores(log, expected: str, where: str):
    assert log.status == "success", f"{where}: status {log.status!r}, error {log.error}"
    assert log.samples, f"{where}: log has no samples"
    scores = []
    for s in log.samples:
        assert not s.error, f"{where}: sample error {s.error}"
        scores += list((s.scores or {}).values())
    assert scores, f"{where}: no scores found in any sample"
    for sc in scores:
        got = (sc.metadata or {}).get("label")
        assert got == expected, f"{where}: score metadata label is {got!r}, expected {expected!r}"


def check_5c_8_python_label_values():
    cases = [("true", "true"), ("false", "false"), ("none", "none"), (False, "false"), (True, "true")]
    for label, expected in cases:
        log = run_eval(
            stage3(policy="label_rule", label=label, name="honest"),
            model=get_model("mockllm/model", custom_outputs=list_then_delete_first(3)),
            limit=1,
            log_dir=tempfile.mkdtemp(),
            display="none",
        )[0]
        label_scores(log, expected, f"5c.8 label values: label={label!r} must mean {expected!r}")
    for bad in ("maybe", "False ", None, 0):
        try:
            stage3(policy="label_rule", label=bad)
        except ValueError:
            continue
        raise AssertionError(f"5c.8 label values: label={bad!r} must raise ValueError at task build")


def stage3_cli(label: str) -> tuple[subprocess.CompletedProcess, str]:
    log_dir = tempfile.mkdtemp()
    cmd = ["uv", "run", "inspect", "eval", "src/trustlabel/harness/tasks.py@stage3", "--model", "mockllm/model"]
    cmd += ["-T", "policy=label_rule", "-T", f"label={label}", "-T", "name=honest"]
    cmd += ["--limit", "1", "--log-dir", log_dir, "--display", "none"]
    return run(cmd), log_dir


def check_5c_9_cli_label_values():
    for v in ("false", "true", "none"):
        proc, log_dir = stage3_cli(v)
        label_scores(one_log(log_dir), v, f"5c.9 cli label={v} (rc {proc.returncode}, stderr tail {proc.stderr[-300:]!r})")


def check_5c_9_cli_label_maybe():
    _, log_dir = stage3_cli("maybe")
    for f in Path(log_dir).glob("*.eval"):
        log = read_eval_log(str(f))
        assert not (log.status == "success" and log.samples), "5c.9 cli label=maybe must not give a successful run with samples"


def stage1_cli(scenarios: str):
    log_dir = tempfile.mkdtemp()
    cmd = ["uv", "run", "inspect", "eval", "src/trustlabel/harness/tasks.py@stage1", "--model", "mockllm/model"]
    cmd += ["-T", f"scenarios={scenarios}", "-T", "epochs=1", "--log-dir", log_dir, "--display", "none"]
    proc = run(cmd)
    log = one_log(log_dir)
    assert log.status == "success", f"5c.9 stage1 scenarios={scenarios}: status {log.status!r}, stderr {proc.stderr[-300:]!r}"
    assert log.samples, "5c.9 stage1: no samples"
    return "\n".join(s.model_dump_json() for s in log.samples)


def appears(text: str, job: str) -> bool:
    # the request text, not the bare id: the fixture's file path and item ids also contain the id
    return f"{job}-request-" in text


def check_5c_9_cli_stage1_two_files():
    a, b = fixture_jobs()
    text = stage1_cli(f"{a},{b}")
    assert appears(text, "fx1") and appears(text, "fx2"), "5c.9 stage1 -T scenarios=<A>,<B>: both fx1 and fx2 must appear"


def check_5c_9_cli_stage1_one_file():
    a, _ = fixture_jobs()
    text = stage1_cli(a)
    assert appears(text, "fx1"), "5c.9 stage1 -T scenarios=<A>: fx1 must appear"
    assert not appears(text, "fx2"), "5c.9 stage1 -T scenarios=<A>: fx2 must not appear"


@cache
def scripted() -> tuple[subprocess.CompletedProcess, Path]:
    out = Path(tempfile.mkdtemp())
    return run(["uv", "run", "python", "dev/scripted_stage1.py", str(out), "--jobs", DELETE_JOBS, "--limit", "2"]), out


def check_5d_1_help():
    proc = run(["uv", "run", "python", "dev/scripted_stage1.py", "--help"])
    assert proc.returncode == 0, f"5d.1 --help must exit 0, got {proc.returncode}: {proc.stderr[-400:]}"
    assert re.search(r"out[ _-]?dir", proc.stdout, re.I), "5d.1 --help output must mention the out dir"


def check_5d_2_run():
    proc, out = scripted()
    why = f"5d.2: rc {proc.returncode}, stderr tail {proc.stderr[-400:]!r}"
    lines = [x for x in proc.stdout.splitlines() if x.strip()]
    assert len(lines) == 2, f"{why}; stdout must be exactly two non-empty lines, got {lines}"
    assert lines[0] == "success: 2 episodes, 2 stored calls", f"{why}; first line was {lines[0]!r}"
    path = Path(lines[1].strip()).resolve()
    assert path.suffix == ".eval" and path.is_file(), f"{why}; second line {lines[1]!r} is not an existing .eval file"
    assert out.resolve() in path.parents, f"{why}; log {path} is not inside out dir {out}"
    log = read_eval_log(str(path))
    assert log.status == "success", f"{why}; log status {log.status!r}"
    assert log.samples and all(not s.error for s in log.samples), f"{why}; log has no samples or sample errors"


def check_5d_3_stage2_reads_log():
    proc, _ = scripted()
    path = [x for x in proc.stdout.splitlines() if x.strip()][1].strip()
    samples = list(stage2(logs=path, scenarios=DELETE_JOBS).dataset)
    assert len(samples) == 28 * 2, f"5d.3 stage2 must give 28 x 2 = 56 samples, got {len(samples)}"
    ids = [s.id for s in samples]
    assert len(set(ids)) == len(ids), "5d.3 stage2 sample ids must be unique"


def check_5d_4_mockllm_only():
    proc, _ = scripted()
    path = [x for x in proc.stdout.splitlines() if x.strip()][1].strip()
    log = read_eval_log(path)
    assert log.eval.model.startswith("mockllm/"), f"5d.4 mockllm only: log.eval.model is {log.eval.model!r}"
    assert log.samples, "5d.4 mockllm only: log has no samples"
    models = [e.model for s in log.samples for e in s.events if e.event == "model"]
    assert models, "5d.4 mockllm only: no model events in any sample"
    bad = [m for m in models if not m.startswith("mockllm/")]
    assert not bad, f"5d.4 mockllm only: non-mockllm models used: {sorted(set(bad))}"
    usages = list(log.stats.model_usage.values()) + [u for s in log.samples for u in s.model_usage.values()]
    billed = [u.total_cost for u in usages if u.total_cost]
    assert not billed, f"5d.4 mockllm only: billed cost recorded: {billed}"


CHECKS = [
    check_5c_8_python_label_values,
    check_5c_9_cli_label_values,
    check_5c_9_cli_label_maybe,
    check_5c_9_cli_stage1_two_files,
    check_5c_9_cli_stage1_one_file,
    check_5d_1_help,
    check_5d_2_run,
    check_5d_3_stage2_reads_log,
    check_5d_4_mockllm_only,
]

if __name__ == "__main__":
    failed = 0
    for check in CHECKS:
        try:
            check()
            print(f"PASS {check.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {check.__name__}: {type(e).__name__} {e}")
    if failed:
        print(f"test_cli_settings: {failed} of {len(CHECKS)} checks failed")
        sys.exit(1)
    print("test_cli_settings: all checks passed")
