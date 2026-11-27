"""An agent reply cut off by a length limit or content filter fails the sample; a normal "stop" reply is unchanged. Run: dev/py.sh python tests/harness/test_cut_off_reply.py"""
import tempfile

from inspect_ai import eval as run_eval
from inspect_ai.model import ChatCompletionChoice, ChatMessageAssistant, ModelOutput, ModelUsage, get_model
from inspect_ai.model._providers.mockllm import MockLLM
from mock_agents import list_then_delete_first

from trustlabel.harness.tasks import stage1, stage3


async def _keep_usage(self, output, input, tools):  # a real provider does not invent usage
    return None


MockLLM._ensure_default_usage = _keep_usage

TMP = tempfile.mkdtemp()
USAGE = ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2)


def reply(stop_reason, text="Done.", usage=USAGE):
    msg = ChatMessageAssistant(content=text, model="mockllm/model")
    return ModelOutput(model="mockllm/model", choices=[ChatCompletionChoice(message=msg, stop_reason=stop_reason)], usage=usage)


def agent(stop_reason, cut_turn, text="Done."):
    """list, then delete (a state-changing call), with the reply at assistant turn `cut_turn` (0 = before acting, 2 = after the delete) given this stop_reason."""
    base = list_then_delete_first(3)

    def respond(messages, tools, tool_choice, config):
        turn = sum(1 for m in messages if m.role == "assistant")
        if turn == cut_turn:
            return reply(stop_reason, text)
        return base(messages, tools, tool_choice, config)

    return respond


def run(make, stop_reason, cut_turn, text="Done."):
    model = get_model("mockllm/model", custom_outputs=agent(stop_reason, cut_turn, text))
    log = run_eval(make(), model=model, log_dir=TMP, display="none", fail_on_error=False, limit=1)[0]
    assert log.samples, "no samples ran"
    return log.samples[0]


def end_reasons(sample):
    return [sc.metadata["end_reason"] for sc in (sample.scores or {}).values() if sc.metadata and "end_reason" in sc.metadata]


STAGES = (("stage 1", lambda: stage1(epochs=1)), ("stage 3", lambda: stage3(policy="never_ask")))

for name, make in STAGES:
    # spec 1: cut-off replies fail the sample, before acting (turn 0) and after the delete (turn 2)
    for reason in ("max_tokens", "model_length", "content_filter"):
        for turn, when in ((0, "before acting"), (2, "after a state-changing call")):
            s = run(make, reason, turn)
            assert s.error is not None, f"spec 1: {name}, {reason} {when}: the sample must have an error"
            assert reason in str(s.error), f"spec 1: {name}, {reason} {when}: the error must name the stop reason, got {s.error!r}"
            assert not {"done", "clarify_twice"} & set(end_reasons(s)), f"spec 1: {name}, {reason} {when}: must not end as done or clarify_twice"
    # spec 2: stop replies are unchanged, including blank text with usage
    for text in ("Done.", ""):
        for turn in (0, 2):
            s = run(make, "stop", turn, text)
            assert s.error is None, f"spec 2: {name}, stop reply (text {text!r}, turn {turn}) must not error, got {s.error!r}"
print("test_cut_off_reply: all checks passed")
