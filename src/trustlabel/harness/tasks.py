"""The three stages as Inspect tasks (Y6). Every switch is a task parameter (-T key=value).

  inspect eval src/trustlabel/harness/tasks.py@stage1 --model <agent>
  inspect eval src/trustlabel/harness/tasks.py@stage2 --model <gate> -T logs=<stage-1 .eval paths, comma-separated>
  inspect eval src/trustlabel/harness/tasks.py@stage3 --model <agent> -T gate_model=<gate> -T gate_config=<yaml> -T gate_effort=<effort> -T warning=true
"""

from dataclasses import asdict
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import GenerateConfig
from inspect_ai.solver import generate

from trustlabel.harness.episode import episode
from trustlabel.harness.replay import gate_outcome, replay_samples, stored_calls
from trustlabel.scenarios.load import DELETE_JOBS, load_scenarios
from trustlabel.scorer import final_state_scorer

# `inspect eval` runs a task from its own folder, so relative paths in -T arguments are read from the project root
ROOT = Path(__file__).resolve().parents[3]


def from_root(path: str) -> str:
    return str(path if Path(path).is_absolute() else ROOT / path) if path else path


def episode_samples(scenarios: str, names: str) -> MemoryDataset:
    samples = [
        Sample(input=s.request, id=f"{s.id}-{s.version}-{name}", metadata={"scenario": asdict(s), "name": name})
        for path in scenarios.split(",")
        for s in load_scenarios(from_root(path))
        for name in names.split(",")
    ]
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
def stage2(logs: str, first_only: bool = True) -> Task:
    """Gate decisions: every stored call from the given stage-1 logs, under all 7 conditions for its name."""
    calls = stored_calls([from_root(p) for p in logs.split(",")], first_only)
    if not calls:
        raise ValueError(f"no stored calls in {logs}: no agent proposed an irreversible call there "
                         "(a plain mockllm stage 1 never calls tools; use tests/harness/test_stages.py or a smoke log)")
    return Task(
        dataset=MemoryDataset(replay_samples(calls)),
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
    return Task(
        dataset=episode_samples(scenarios, name),
        solver=episode(stage=3, policy=policy, label=label, warning=warning, gate_model=gate_model or None,
                       gate_config=from_root(gate_config) or None, gate_effort=gate_effort or None,
                       max_steps=max_steps, seed=seed),
        scorer=final_state_scorer(),
        epochs=epochs,
        config=GenerateConfig(temperature=1.0),
    )
