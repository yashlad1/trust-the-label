"""Stage 3: a blank gate reply (no text, no tool calls, no usage) must end the sample in error. Run: dev/py.sh python tests/policies/test_blank_gate_reply.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "harness"))
from inspect_ai import eval as run_eval
from inspect_ai.model import ChatCompletionChoice, ChatMessageAssistant, ModelOutput, ModelUsage, get_model
from mock_agents import list_then_delete_first

import trustlabel.policies.gate as gate_mod
from trustlabel.harness.tasks import stage3

from inspect_ai.model._providers.mockllm import MockLLM


async def _keep_usage(self, output, input, tools):  # mockllm fills in usage when a reply has none; a real provider does not
    return None


MockLLM._ensure_default_usage = _keep_usage

TMP = tempfile.mkdtemp()
USAGE = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)


def gate_reply(text, usage):
    msg = ChatMessageAssistant(content=text, model="mockllm/model")
    return ModelOutput(model="mockllm/model", choices=[ChatCompletionChoice(message=msg, stop_reason="stop")], usage=usage)


def errors(text, usage):
    fake = get_model("mockllm/gate", custom_outputs=lambda *a: gate_reply(text, usage))
    orig, gate_mod.get_model = gate_mod.get_model, lambda *a, **k: fake
    try:
        agent = get_model("mockllm/model", custom_outputs=list_then_delete_first(3))
        task = stage3(policy="gate_with_labels", gate_model="mockllm/gate")
        log = run_eval(task, model=agent, log_dir=TMP, display="none", fail_on_error=False, limit=1)[0]
    finally:
        gate_mod.get_model = orig
    assert log.samples, "no samples ran"
    return [s.error for s in log.samples if s.error]


for usage in (None, USAGE):
    assert not errors("ALLOW", usage), f"stage 3: control failed, an ALLOW reply (usage {usage}) must not error"
assert errors("", None), "stage 3: a blank gate reply with no usage must end the sample in error"
print("ok")
