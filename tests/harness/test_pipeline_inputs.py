# H12 · dev/pipeline.py dry run with reused stage-1 logs: an errored sample, an unknown eval model
import ast, glob, os, subprocess, sys, tempfile, zipfile
from pathlib import Path
from inspect_ai.log import EvalError, read_eval_log, write_eval_log

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = os.environ.get("PIPELINE", "dev/pipeline.py")
ONLY = os.environ.get("ONLY", "ab")
_fx = tempfile.TemporaryDirectory()
zipfile.ZipFile(ROOT / "tests/harness/fixtures/stage1.zip").extractall(_fx.name)
SRC = glob.glob(os.path.join(_fx.name, "**", "*.eval"), recursive=True)[0]
GPTOSS = "openrouter/openai/gpt-oss-120b"
JOBS = ",".join(f"src/trustlabel/scenarios/{k}.json" for k in ("delete", "send", "pay", "publish"))


def run(log_path, out):
    cmd = [sys.executable, PIPELINE, "dry", out, "--wording", "src/trustlabel/scenarios/wording.json",
           "--stage1-logs", log_path, "--jobs", JOBS, "--epochs", "1", "--no-stage2", "--no-stage3"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=ROOT)


def gptoss_count(p):
    assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]
    lines = p.stdout.splitlines()
    assert lines[-1].startswith("done."), lines[-3:]
    line = [l for l in lines if l.startswith("stage 3 agent:")][0]
    return ast.literal_eval(line[line.index("{"):line.rindex("}") + 1]).get("gptoss", 0)


def save(log, d, name):
    path = os.path.join(d, name)
    write_eval_log(log, path)
    return path


with tempfile.TemporaryDirectory() as d:
  if "a" in ONLY:
    # (a) errored sample
    log = read_eval_log(SRC)
    log.eval.model = GPTOSS
    base_path = save(log, d, "agent.eval")
    base = gptoss_count(run(base_path, os.path.join(d, "out_base")))
    assert base > 0, base
    i = next(i for i, s in enumerate(log.samples) if s.metadata["scenario"]["version"] == "unneeded"
             and s.store.get("episode", {}).get("stored_calls"))
    log.samples[i].error = EvalError(message="boom", traceback="tb", traceback_ansi="tb")
    log.samples[i].store = {}
    err_path = save(log, d, "errored.eval")
    got = gptoss_count(run(err_path, os.path.join(d, "out_err")))
    assert got == base - 1, (got, base)


  if "b" in ONLY:
    # (b) unknown model
    log = read_eval_log(SRC)
    log.eval.model = "mockllm/model"
    unk_path = save(log, d, "unknown.eval")
    p = run(unk_path, os.path.join(d, "out_unk"))
    assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]
    assert p.stdout.splitlines()[-1].startswith("done."), p.stdout[-300:]
    assert any("not one of the agents" in l and "mockllm/model" in l for l in (p.stdout + p.stderr).splitlines()), \
        (p.stdout + p.stderr)[-800:]

print("checks passed")
