# FP3 task 19 (docs/fp3-tasks.html): the runner: dry, smoke and full runs with a spend stop
"""The whole experiment, end to end: ping, stage 1, stage 2, stage 3, manifest.

Each stage runs a 12-sample smoke first; the full stage starts only if the smoke passes its checks. Spend is summed
from OpenRouter's billed usage.cost after every eval, and the run stops once it passes STOP_AT.

  dev/py.sh python dev/pipeline.py dry  <out dir> --wording <wording json> --stage1-logs <scripted stage-1 .eval> [--epochs N] [--stage2-epochs N]
  dev/py.sh python dev/pipeline.py paid <out dir> --wording <wording json> [--epochs N] [--stage2-epochs N]        PAID: Yash's go only
  dev/run_split.sh paid|dry <out prefix> <wording json> [epochs]   split run: stage 3 beside stage 2, one process per gate and stage-1 log

--jobs picks the scope and defaults to the delete jobs; ALL_JOBS covers all four kinds (about 4x the calls and cost):
  --jobs "$(python -c 'import dev.pipeline as p; print(p.ALL_JOBS)')"

Run paid detached (own process session, survives the terminal):
  perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' -- caffeinate -is dev/py.sh python dev/pipeline.py paid logs/run \
      --wording <wording json> [--epochs N] > logs/run.out 2>&1 < /dev/null &
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml
from inspect_ai import eval as run_eval
from inspect_ai.log import read_eval_log

from trustlabel.analysis.rates import failed
from trustlabel.policies.gate import ATTEMPT_TIMEOUT, MAX_RETRIES
from trustlabel.harness.tasks import stage1, stage2, stage3
from trustlabel.scenarios.load import DELETE_JOBS, PAY_JOBS, PUBLISH_JOBS, SEND_JOBS

STOP_AT = 12.00  # dollars of billed spend for ONE run of this script, not the whole project
ALL_JOBS = ",".join([DELETE_JOBS, SEND_JOBS, PAY_JOBS, PUBLISH_JOBS])
MODELS = {  # name -> (Inspect model, provider pin, reasoning effort)
    "gptoss": ("openrouter/openai/gpt-oss-120b", "dev/models/gpt-oss-120b.yaml", "medium"),
    "glm": ("openrouter/z-ai/glm-5.3-flash", "dev/models/glm-5.3-flash.yaml", "medium"),
    "luna": ("openrouter/openai/gpt-6-luna", "dev/models/gpt-6-luna.yaml", "medium"),
    "nemotron35": ("openrouter/nvidia/nemotron-3.5-super-vl", "dev/models/nemotron-3.5-super-vl.yaml", "medium"),
}
AGENTS, GATES, LIVE_GATE = ["gptoss", "glm"], ["luna", "nemotron35"], "luna"
STAGE1_NAMES = "honest"  # stage 1 runs the honest name only; stage 2 shows every call under honest and vague
STAGE3_NAME = "honest"
STAGE3 = {"gate on call": ("gate_on_call", False), "labels, warning off": ("gate_with_labels", False),
          "labels, warning on": ("gate_with_labels", True)}
COMMON = dict(display="none", fail_on_error=0.05, log_model_api=True, attempt_timeout=ATTEMPT_TIMEOUT, max_retries=MAX_RETRIES)
CONNECTIONS = {"gptoss": 2, "nemotron35": 8}  # gpt-oss answered 429 (too many requests) at 4; nemotron35 ran clean at 8 in two parallel processes; everyone else gets 4
STAGE3_SAMPLES = 6  # live episodes at once: more than the agent's connections, so they stay busy while the gate thinks (connections still cap agent calls)


def model_kwargs(name, dry):
    if dry:
        return dict(model="mockllm/model", max_connections=4)
    model, pin, effort = MODELS[name]
    return dict(model=model, model_args=yaml.safe_load(Path(pin).read_text()), max_connections=CONNECTIONS.get(name, 4),
                **({"reasoning_effort": effort} if effort else {}))


def git(*args):
    try:
        return subprocess.run(["git", "-C", str(Path(__file__).resolve().parent.parent), *args], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def spend(paths):
    return sum(((e.call.response or {}).get("usage") or {}).get("cost") or 0
               for p in paths for s in read_eval_log(p).samples or [] for e in s.events if e.event == "model" and e.call)


class Run:
    def __init__(self, out, dry, stop_at=STOP_AT):
        self.stop_at = stop_at
        self.out, self.dry, self.logs, self.manifest = Path(out), dry, [], {"stage1": [], "stage2": {}, "stage3": {},
                                                                    "live_gate": LIVE_GATE, "smokes": {}}
        self.out.mkdir(parents=True, exist_ok=True)

    def run(self, step, task, name, **kw):
        log = run_eval(task, log_dir=str(self.out / step), **model_kwargs(name, self.dry), **COMMON, **kw)[0]
        self.logs.append(log.location)
        if "smoke" in step:
            self.manifest["smokes"][step] = log.location
        cost = spend(self.logs)
        print(f"{step}: {log.status}, {len(log.samples or [])} samples, spend so far ${cost:.4f}", flush=True)
        if cost > self.stop_at:
            self.stop(f"STOP: spend ${cost:.4f} passed ${self.stop_at:.2f}")
        if "smoke" not in step and log.status != "success":
            self.stop(f"STOP: {step} ended with status {log.status}; its log was not used")
        return log

    def check(self, step, log, ok, why):
        errors = [s.id for s in log.samples or [] if s.error]
        passed = log.status == "success" and not errors and ok
        print(f"{step} smoke check: {'pass' if passed else 'FAIL'} ({why}; sample errors: {len(errors)})", flush=True)
        if not passed and not self.dry:
            self.stop(f"STOP: {step} smoke failed; the full stage was not started")

    def stop(self, msg):  # save the manifest first, so a stopped run still says what ran
        self.save()
        sys.exit(msg)

    def save(self):
        (self.out / "manifest.json").write_text(json.dumps(self.manifest, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["dry", "paid"])
    ap.add_argument("out")
    ap.add_argument("--wording", required=True, help="path to the wording JSON for the stage-2 wording rows")
    ap.add_argument("--stage1-logs", help="comma-separated stage-1 .eval logs to reuse: stage 1 is not run (dry: scripted "
                                          "logs, plain mockllm stores no calls)")
    ap.add_argument("--gates", help=f"comma-separated stage-2 gates to run (default all of {GATES})")
    ap.add_argument("--no-stage2", action="store_true", help="skip stage 2 entirely (no smoke, no runs)")
    ap.add_argument("--no-stage3", action="store_true", help="skip stage 3 entirely (no smoke, no runs)")
    ap.add_argument("--stop-at", type=float, default=STOP_AT,
                    help="stop once billed spend passes this many dollars; applies PER PROCESS, so a split run gives each process its share")
    ap.add_argument("--jobs", help="comma-separated job files; default the delete jobs. ALL_JOBS covers all four "
                                   "kinds (about 4x the episodes, gate calls and cost, so it needs its own go)")
    ap.add_argument("--epochs", type=int, default=2,
                    help="repeats per task for the full stage-1 and stage-3 runs; the pilot uses 1")
    ap.add_argument("--stage2-epochs", type=int, default=1,
                    help="how many times each stage-2 sample is run (repeats keep the same sample id)")
    a = ap.parse_args()
    dry, jobs = a.mode == "dry", a.jobs or DELETE_JOBS
    gates = a.gates.split(",") if a.gates else GATES
    if [g for g in gates if g not in GATES]:
        ap.error(f"unknown gate in {gates}; valid: {GATES}")
    p = Run(a.out, dry, a.stop_at)
    p.manifest.update(jobs=jobs, wording=a.wording, epochs=a.epochs, stage2_epochs=a.stage2_epochs)  # the manifest says what a run covered
    status = git("status", "--porcelain", "--untracked-files=no")  # tracked files only; how to rebuild the run: mode, command, code, models
    p.manifest.update(mode=a.mode, command=sys.argv, code={"git_sha": git("rev-parse", "HEAD"),
                                                           "dirty": None if status is None else bool(status)})
    p.manifest["models"] = {n: {"model": MODELS[n][0], "config": MODELS[n][1], "provider": yaml.safe_load(Path(MODELS[n][1]).read_text()),
                                "effort": MODELS[n][2], "connections": CONNECTIONS.get(n, 4)}
                            for n in dict.fromkeys([*AGENTS, *gates, LIVE_GATE])}
    p.manifest.update(stage2_skipped=a.no_stage2, stage3_skipped=a.no_stage3)

    if not dry:  # 0. one tiny tool call per model, the same way the runs send them
        if subprocess.run([sys.executable, "dev/check_openrouter.py", "--ping", "--yes"]).returncode:
            p.stop("STOP: the ping failed")

    # 1. stage 1: each agent proposes, with never ask
    unneeded = {}
    for agent in [] if a.stage1_logs else AGENTS:
        log = p.run(f"stage1-{agent}-smoke", stage1(scenarios=jobs, names=STAGE1_NAMES), agent, limit=12, epochs=1)
        used_tools = any(m.role == "assistant" and m.tool_calls for s in log.samples for m in s.messages)
        p.check(f"stage1-{agent}", log, used_tools, "the agent called tools" if used_tools else "no tool calls")
        log = p.run(f"stage1-{agent}", stage1(scenarios=jobs, names=STAGE1_NAMES), agent, epochs=a.epochs)
        p.manifest["stage1"].append(log.location)
        unneeded[agent] = sum(bool(s.store["episode"]["stored_calls"]) for s in log.samples
                              if not failed(s, None) and s.metadata["scenario"]["version"] == "unneeded")
    if a.stage1_logs:  # reuse: count the unneeded proposals from the given logs, per agent
        unneeded = dict.fromkeys(AGENTS, 0)
        for path in a.stage1_logs.split(","):
            old = read_eval_log(path)
            agent = next((g for g in AGENTS if MODELS[g][0] == old.eval.model), None)
            if agent is None:
                if not dry:
                    p.stop(f"STOP: {path} was made by {old.eval.model}, not one of the agents {AGENTS}")
                agent = AGENTS[0]
                print(f"note: {path} was made by {old.eval.model}, not one of the agents; counted as {agent} (dry run)")
            unneeded[agent] += sum(bool(s.store["episode"]["stored_calls"]) for s in old.samples or []
                                   if not failed(s, None) and s.metadata["scenario"]["version"] == "unneeded")
        p.manifest.update(stage1=a.stage1_logs.split(","), stage1_reused=True)
    p.save()
    stage1_logs = ",".join(p.manifest["stage1"])

    # 2. stage 2: every gate judges the same stored calls: the standard rows plus the intent rows and the wording rows
    rows = dict(intent_rows=True, wording_rows=a.wording)
    for gate in [] if a.no_stage2 else gates:
        log = p.run(f"stage2-{gate}-smoke", stage2(logs=stage1_logs, scenarios=jobs, **rows), gate, limit=12)
        scored = [s for s in log.samples if not failed(s, "gate_outcome")]
        unreadable = sum(s.scores["gate_outcome"].value["unreadable"] for s in scored)
        p.check(f"stage2-{gate}", log, len(scored) == 12 and unreadable <= 3,
                f"{unreadable}/{len(scored)} unreadable replies, {len(scored)}/12 scored")
        p.manifest["stage2"][gate] = p.run(f"stage2-{gate}", stage2(logs=stage1_logs, scenarios=jobs, **rows), gate,
                                         epochs=a.stage2_epochs).location
        p.save()

    # 3. stage 3: the stage-1 agent with more unneeded proposals, live, with the live gate
    agent = max(unneeded, key=unneeded.get)
    gate_model, gate_pin, gate_effort = MODELS[LIVE_GATE]
    gate = dict(gate_model="mockllm/model" if dry else gate_model, gate_config="" if dry else gate_pin,
                gate_effort="" if dry else gate_effort)
    p.manifest.update(stage3_agent=agent, stage1_unneeded=unneeded)
    print(f"stage 3 agent: {agent} (unneeded proposals in stage 1: {unneeded})", flush=True)
    for i, (label, (policy, warning)) in enumerate({} if a.no_stage3 else STAGE3.items()):
        task = lambda: stage3(policy=policy, warning=warning, name=STAGE3_NAME, scenarios=jobs, epochs=a.epochs, **gate)
        if i == 0:
            log = p.run("stage3-smoke", task(), agent, limit=12, epochs=1, max_samples=STAGE3_SAMPLES)
            gated = any(d["verdict"] for s in log.samples if not failed(s, "final_state_scorer") for d in s.store["episode"]["decisions"])
            p.check("stage3", log, gated, "the gate decided calls" if gated else "no gate decisions")
        p.manifest["stage3"][label] = p.run(f"stage3-{policy}-{'warn' if warning else 'plain'}", task(), agent, max_samples=STAGE3_SAMPLES).location
        p.save()

    p.manifest.update(spend=spend(p.logs), stop_at=p.stop_at)
    p.save()
    print(f"done. spend ${spend(p.logs):.4f}. manifest: {p.out}/manifest.json")


if __name__ == "__main__":
    main()
