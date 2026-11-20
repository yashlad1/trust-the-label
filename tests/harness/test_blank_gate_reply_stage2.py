"""Stage 2: a blank gate reply (no text, no tool calls, no usage) must end the sample in error. Run: dev/py.sh python tests/harness/test_blank_gate_reply_stage2.py"""
import tempfile

from inspect_ai import eval as run_eval
from inspect_ai.model import ChatCompletionChoice, ChatMessageAssistant, ModelOutput, ModelUsage, get_model
from mock_agents import list_then_delete_first

from trustlabel.harness.tasks import stage1, stage2

from inspect_ai.model._providers.mockllm import MockLLM


async def _keep_usage(self, output, input, tools):  # mockllm fills in usage when a reply has none; a real provider does not
    return None


MockLLM._ensure_default_usage = _keep_usage

TMP = tempfile.mkdtemp()
USAGE = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)


def gate_reply(text, usage):
    msg = ChatMessageAssistant(content=text, model="mockllm/model")
    return ModelOutput(model="mockllm/model", choices=[ChatCompletionChoice(message=msg, stop_reason="stop")], usage=usage)


agent = get_model("mockllm/model", custom_outputs=list_then_delete_first(3))
stage1_log = run_eval(stage1(epochs=1), model=agent, log_dir=TMP, display="none")[0].location


def errors(text, usage):
    gate = get_model("mockllm/model", custom_outputs=lambda *a: gate_reply(text, usage))
    log = run_eval(stage2(logs=stage1_log), model=gate, log_dir=TMP, display="none", fail_on_error=False, limit=4)[0]
    assert log.samples, "no samples ran"
    return [s.error for s in log.samples if s.error]


for usage in (None, USAGE):
    assert not errors("ALLOW", usage), f"stage 2: control failed, an ALLOW reply (usage {usage}) must not error"
assert errors("", None), "stage 2: a blank gate reply with no usage must end the sample in error"
print("ok")
