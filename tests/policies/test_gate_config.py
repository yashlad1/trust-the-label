# Gate config: every generate() call carries the run settings (timeout, retries, temperature, effort).
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import trustlabel.policies.gate as gate_mod
from trustlabel.contracts import Call, GateInput, Labels
from trustlabel.policies.gate import Gate


def one_gate_call(effort):
    configs = []

    class Fake:
        async def generate(self, messages, config=None):
            configs.append(config)
            return SimpleNamespace(completion="ALLOW\nok")

    orig = gate_mod.get_model
    gate_mod.get_model = lambda *a, **k: Fake()
    try:
        g = GateInput(request="tidy up", history="", call=Call("delete_file", "Deletes a file", {"id": "1"}),
                      input_schema={}, labels=Labels(read_only=False, destructive=True), warning=False)
        decision = asyncio.run(Gate(model="fake/gate", with_labels=True, effort=effort)(g))
    finally:
        gate_mod.get_model = orig
    return decision, configs


def check_config(effort):
    decision, configs = one_gate_call(effort)
    assert decision.verdict == "allow", f"effort {effort}: expected allow, got {decision.verdict}"
    assert configs, f"effort {effort}: the gate made no generate() call"
    for c in configs:
        assert c is not None, f"effort {effort}: generate() got no config"
        assert c.attempt_timeout == 180, f"effort {effort}: attempt_timeout {c.attempt_timeout}"
        assert c.max_retries == 10, f"effort {effort}: max_retries {c.max_retries}"
        assert c.temperature == 1.0, f"effort {effort}: temperature {c.temperature}"
        assert c.reasoning_effort == effort, f"effort {effort}: reasoning_effort {c.reasoning_effort}"


def check_shared_setting():
    assert gate_mod.ATTEMPT_TIMEOUT == 180, gate_mod.ATTEMPT_TIMEOUT
    assert gate_mod.MAX_RETRIES == 10, gate_mod.MAX_RETRIES
    path = Path(__file__).resolve().parents[2] / "dev" / "pipeline.py"
    spec = importlib.util.spec_from_file_location("pipeline_under_test", path)
    pipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pipe)
    assert pipe.COMMON["attempt_timeout"] == gate_mod.ATTEMPT_TIMEOUT, pipe.COMMON
    assert pipe.COMMON["max_retries"] == gate_mod.MAX_RETRIES, pipe.COMMON


if __name__ == "__main__":
    check_shared_setting()
    check_config(None)
    check_config("low")
    print("ok")
