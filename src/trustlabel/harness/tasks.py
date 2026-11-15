# FP3 tasks 16, 17 (docs/fp3-tasks.html): stage tasks one to three, live loop
"""The three stages as Inspect tasks. Every switch is a task parameter (-T key=value).

  inspect eval src/trustlabel/harness/tasks.py@stage1 --model <agent>
  inspect eval src/trustlabel/harness/tasks.py@stage2 --model <gate> -T logs=<stage-1 .eval paths, comma-separated> -T scenarios=<the stage-1 scenario files>
  inspect eval src/trustlabel/harness/tasks.py@stage3 --model <agent> -T gate_model=<gate> -T gate_config=<yaml> -T gate_effort=<effort> -T warning=true
"""

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.solver import generate

from trustlabel.harness.episode import episode
from trustlabel.harness.replay import INTENT_CONDITIONS, NAMES_SHOWN, WORDING_CONDITIONS, gate_outcome, replay_samples, stored_calls
from trustlabel.scenarios.load import DELETE_JOBS, load_scenarios
from trustlabel.scorer import final_state_scorer

# `inspect eval` runs a task from its own folder, so relative paths in -T arguments are read from the project root
ROOT = Path(__file__).resolve().parents[3]


def from_root(path: str) -> str:
    return str(path if Path(path).is_absolute() else ROOT / path) if path else path


def as_list(value) -> list[str]:
    """A comma-list parameter: inspect's -T parsing turns "a,b" into a list, Python callers pass a string."""
    return [str(v) for v in value] if isinstance(value, (list, tuple)) else value.split(",")


def episode_samples(scenarios: str, names: str) -> MemoryDataset:
    samples = [
        Sample(input=s.request, id=f"{s.id}-{s.version}-{name}", metadata={"scenario": asdict(s), "name": name})
        for path in as_list(scenarios)
        for s in load_scenarios(from_root(path))
        for name in as_list(names)
    ]
    clashing = [i for i, c in Counter(s.id for s in samples).items() if c > 1]
    assert not clashing, (f"{len(clashing)} sample ids appear more than once, so two jobs share an id across the "
                          f"job files: {clashing[:4]}. Inspect cannot run this, and the job bootstrap would "
                          f"resample them as one job.")
    return MemoryDataset(samples)


@task
def stage1(scenarios: str = DELETE_JOBS, names: str = "honest,vague", epochs: int = 2,
           max_steps: int = 12, seed: int = 0) -> Task:
    """Proposals: the agent works every version under both names; never ask, so nothing stops it.
    `scenarios` takes comma-separated scenario files, like stage2's logs.
    Labels play no part (neither the agent nor never ask reads them), so the server runs with true labels."""
    return Task(
        dataset=episode_samples(scenarios, names),
        solver=episode(stage=1, policy="never_ask", label="true", max_steps=max_steps, seed=seed),
        scorer=final_state_scorer(),
        epochs=epochs,
        config=GenerateConfig(temperature=1.0),
    )


@task
def stage2(logs: str, scenarios: str = DELETE_JOBS, first_only: bool = True, intent: bool = False,
           wording: str = "", intent_rows: bool = False, wording_rows: str = "") -> Task:
    """Gate decisions: every stored call from the given stage-1 logs, under all 7 conditions, both names and both
    requests (28 samples per call). `scenarios` must hold both versions of every job the logs came from.
    intent=True is the intent-instruction run instead: labels true/false/none (warning off) x both names x both
    requests, each under the plain prompt and the intent one (24 samples per call).
    wording=<json file> is the wording run instead: no label and the false label (warning off, vague name) x the
    four requests, need x wording (8 samples per call).
    intent_rows=True adds the intent-prompt rows to the standard run (labels true/false/none, warning off, both names,
    both requests: 12 more per call); not with intent or wording.
    wording_rows=<json file> adds the wording rows (8 more per call) to the standard run; not with intent or wording."""
    if intent_rows and (intent or wording):
        raise ValueError("intent_rows needs the standard rows: not with intent or wording")
    if wording_rows and (intent or wording):
        raise ValueError("wording_rows needs the standard rows: not with intent or wording")
    calls = stored_calls([from_root(p) for p in as_list(logs)], first_only)
    if not calls:
        raise ValueError(f"no stored calls in {logs}: no agent proposed an irreversible call there "
                         "(a plain mockllm stage 1 never calls tools; use tests/harness/test_stages.py or a smoke log)")
    jobs = [s for path in as_list(scenarios) for s in load_scenarios(from_root(path))]
    if wording:
        samples = replay_samples(calls, jobs, WORDING_CONDITIONS, names=("vague",),
                                 wording=json.loads(Path(from_root(wording)).read_text()))
    elif intent:
        samples = replay_samples(calls, jobs, INTENT_CONDITIONS, ("plain", "intent"))
    else:
        samples = replay_samples(calls, jobs)
    if intent_rows:
        samples = samples + replay_samples(calls, jobs, INTENT_CONDITIONS, ("intent",))
    if wording_rows:
        samples = samples + replay_samples(calls, jobs, WORDING_CONDITIONS, names=("vague",),
                                           wording=json.loads(Path(from_root(wording_rows)).read_text()))
    return Task(
        dataset=MemoryDataset(samples),
        solver=generate(),
        scorer=gate_outcome(),
        config=GenerateConfig(temperature=1.0),
    )


@task
def stage3(policy: str = "gate_with_labels", label: str = "false", name: str = "vague", warning: bool = False,
           gate_model: str = "", gate_config: str = "",
           gate_effort: str = "", scenarios: str = DELETE_JOBS, epochs: int = 1, max_steps: int = 12,
           seed: int = 0) -> Task:
    """Live check: the whole loop with a real gate, scored on harm and task success. Name the gate explicitly, with the same provider pin and reasoning effort as its stage-2 run, e.g. -T gate_model=openrouter/openai/gpt-6-luna -T gate_config=dev/models/gpt-6-luna.yaml -T gate_effort=medium (Qwen: no gate_effort). Rule policies (never_ask, label_rule) need no gate."""
    if isinstance(label, bool):  # -T label=false arrives as the boolean False
        label = str(label).lower()
    if label not in ("true", "false", "none"):
        raise ValueError(f"label must be 'true', 'false' or 'none', not {label!r}")
    return Task(
        dataset=episode_samples(scenarios, name),
        solver=episode(stage=3, policy=policy, label=label, warning=warning, gate_model=gate_model or None,
                       gate_config=from_root(gate_config) or None, gate_effort=gate_effort or None,
                       max_steps=max_steps, seed=seed),
        scorer=final_state_scorer(),
        epochs=epochs,
        config=GenerateConfig(temperature=1.0),
    )
