"""R2 launcher: stage 2 on FP4's 234 stored first calls, the 4 headline conditions, one run per gate model.

  dev/py.sh python dev/launch_r2.py dry|paid <run>|all      (all = glm, qwen, haiku, luna-low, luna-high)
"""
import json
import sys
from pathlib import Path

import yaml
from inspect_ai import eval as run_eval

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dev.pipeline import git, spend
from trustlabel.analysis.rates import failed
from trustlabel.harness.tasks import stage2
from trustlabel.policies.gate import ATTEMPT_TIMEOUT, MAX_RETRIES

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
CAP = 8.20
SCENARIOS = ",".join(str(ROOT / f"src/trustlabel/scenarios/{k}.json") for k in ("delete", "send", "pay", "publish"))
STAGE1 = [str(p) for p in json.loads((ROOT / "records/fp4/fp4-stage1/manifest.json").read_text())["stage1"]]
MODELS = ROOT / "dev/models"
# name -> (model, pin, effort, stop $)
RUNS = {
    "glm": ("openrouter/z-ai/glm-5.3-flash", MODELS / "glm-5.3-flash.yaml", "medium", 0.80),
    "qwen": ("openrouter/qwen/qwen3.8-flash", MODELS / "qwen3.8-flash.yaml", None, 0.80),
    "haiku": ("openrouter/anthropic/claude-haiku-5.5", MODELS / "haiku.yaml", "medium", 0.80),
    "luna-low": ("openrouter/openai/gpt-6-luna", MODELS / "gpt-6-luna.yaml", "low", 0.30),
    "luna-high": ("openrouter/openai/gpt-6-luna", MODELS / "gpt-6-luna.yaml", "high", 0.80),
    "gemini": ("openrouter/google/gemini-3.8-flash", MODELS / "gemini-3.8-flash.yaml", "medium", 4.50),
}
ALL = ["glm", "qwen", "haiku", "luna-low", "luna-high"]
COMMON = dict(display="none", fail_on_error=0.05, log_model_api=True, attempt_timeout=ATTEMPT_TIMEOUT,
              max_retries=MAX_RETRIES, max_connections=4)


def headline(task):
    """The 4 headline cells: vague name, own request, gate with labels, label none or false, warning off or on, plain prompt."""
    ids = sorted(s.id for s in task.dataset
                 if s.metadata["shown_name"] == "vague" and s.metadata["request"] == "own"
                 and s.metadata["policy"] == "gate_with_labels" and s.metadata["label"] in ("none", "false")
                 and s.metadata["prompt"] == "plain")
    if len(ids) != 936:
        sys.exit(f"STOP: {len(ids)} headline sample ids, expected 936")
    return ids


def billed_so_far():
    return spend(str(q) for pre in ("r2", "r4") for q in LOGS.glob(f"{pre}-*/**/*.eval"))


def go(name, dry, ids):
    model, pin, effort, stop = RUNS[name]
    out = LOGS / "dry" / f"r2-{name}" if dry else LOGS / f"r2-{name}"
    if not dry and out.exists():
        sys.exit(f"STOP: {out} exists")
    out.mkdir(parents=True, exist_ok=True)
    kw = dict(model="mockllm/model") if dry else dict(
        model=model, model_args=yaml.safe_load(pin.read_text()), **({"reasoning_effort": effort} if effort else {}))

    def run(step, sample_ids):
        log = run_eval(stage2(logs=",".join(STAGE1), scenarios=SCENARIOS), log_dir=str(out / step), sample_id=sample_ids,
                       **kw, **COMMON)[0]
        print(f"{step}: {log.status}, {len(log.samples or [])} samples", flush=True)
        return log

    smoke_ids = ids[::78][:12]
    assert len(set(smoke_ids)) == 12, "smoke must hold 12 distinct ids"
    smoke = run(f"{name}-smoke", smoke_ids)
    scored = [s for s in smoke.samples or [] if not failed(s, "gate_outcome")]
    errors = [s.id for s in smoke.samples or [] if s.error]
    unreadable = sum(s.scores["gate_outcome"].value["unreadable"] for s in scored)
    smoke_cost = 0 if dry else spend([smoke.location])
    projected = smoke_cost / 12 * 936
    spent = 0 if dry else billed_so_far()
    print(f"{name} smoke: {len(scored)}/12 scored, {len(errors)} sample errors, {unreadable} unreadable; smoke ${smoke_cost:.4f}, "
          f"projected ${projected:.2f} (stop ${stop:.2f}), launcher spend so far ${spent:.2f} (cap ${CAP:.2f})", flush=True)
    why = [r for ok, r in [(smoke.status == "success" and len(scored) == 12 and not errors and unreadable <= 3, "smoke failed"),
                           (projected <= stop, "projected cost over the run's stop"),
                           (spent + projected <= CAP, "launcher cap would be passed")] if not ok]
    if why:
        print(f"{name}: full run {'skipped' if not dry else 'would be skipped (dry run goes on)'} ({'; '.join(why)})", flush=True)
        if not dry:
            return
    full = run(name, ids)
    status = git("status", "--porcelain", "--untracked-files=no")
    (out / "manifest.json").write_text(json.dumps({
        "stage1": STAGE1, "stage2": {name: full.location}, "stage3": {}, "live_gate": "luna",
        "smokes": {f"{name}-smoke": smoke.location}, "mode": "dry" if dry else "paid", "command": sys.argv,
        "code": {"git_sha": git("rev-parse", "HEAD"), "dirty": None if status is None else bool(status)},
        "model": model, "pin": yaml.safe_load(pin.read_text()), "effort": effort, "stop_at": stop,
        "spend": 0 if dry else spend([full.location]), "conditions": "headline: vague, own, gate with labels, label none/false, warning off/on, plain",
    }, indent=2))
    print(f"{name} done: {out}/manifest.json", flush=True)


if __name__ == "__main__":
    mode, which = sys.argv[1:3]
    if mode not in ("dry", "paid") or (which != "all" and which not in RUNS):
        sys.exit(__doc__)
    ids = headline(stage2(logs=",".join(STAGE1), scenarios=SCENARIOS))
    for n in ALL if which == "all" else [which]:
        go(n, mode == "dry", ids)
