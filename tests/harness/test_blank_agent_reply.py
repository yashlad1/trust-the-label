"""A blank agent reply (no text, no tool calls, no usage) is a provider failure: the sample must error.
Run from the repo root: dev/py.sh python tests/harness/test_blank_agent_reply.py"""
import tempfile

from inspect_ai import eval as run_eval
from inspect_ai.model import ChatCompletionChoice, ChatMessageAssistant, ModelOutput, ModelUsage, get_model

from trustlabel.harness.tasks import stage1, stage3

from inspect_ai.model._providers.mockllm import MockLLM


async def _keep_usage(self, output, input, tools):  # mockllm fills in usage when a reply has none; a real provider does not
    return None


MockLLM._ensure_default_usage = _keep_usage

TMP = tempfile.mkdtemp()
USAGE = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)


def reply(usage):
    msg = ChatMessageAssistant(content="", model="mockllm/model")
    return ModelOutput(model="mockllm/model", choices=[ChatCompletionChoice(message=msg, stop_reason="stop")], usage=usage)


def errors(task, usage):
    model = get_model("mockllm/model", custom_outputs=lambda *a: reply(usage))
    log = run_eval(task, model=model, log_dir=TMP, display="none", fail_on_error=False, limit=1)[0]
    assert log.samples, "no samples ran"
    return [s.error for s in log.samples if s.error]


def stage3_task():
    return stage3(policy="never_ask")


for name, make in (("stage 1", lambda: stage1(epochs=1)), ("stage 3", stage3_task)):
    assert not errors(make(), USAGE), f"{name}: control failed, a blank reply WITH usage must not error"
    assert errors(make(), None), f"{name}: a blank agent reply with no usage must end the sample in error"
print("ok")
