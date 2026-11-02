"""The approval layer inside the loop (Y4).

Every call to a state-changing tool goes to the gatekeeper: it asks the condition's policy, and on ASK the scripted
user answers. Read-only tools are approved straight away: episode.py pairs the gatekeeper with a catch-all "*"
policy that Inspect requires. Every decision is recorded; in stage 1 every irreversible call is
also stored, with the conversation before it, for stage 2 to replay.
"""

import json
from dataclasses import dataclass, field

from inspect_ai.approval import Approval, Approver, approver
from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageTool, ChatMessageUser
from inspect_ai.tool import ToolCall, ToolCallView

from trustlabel.contracts import Call, GateInput, Labels, Policy, Scenario, StoredCall
from trustlabel.harness.user import BLOCKED, DECLINED, answers_yes
from trustlabel.servers.registry import SERVERS


@dataclass
class EpisodeContext:
    """What the gatekeeper needs for one episode. Built fresh in every episode."""

    episode: str
    agent: str
    scenario: Scenario
    name_setting: str
    entries: dict[str, tuple[str, dict]]  # tool name -> (description, input schema)
    labels: dict[str, Labels | None]  # tool name -> labels under this episode's label switch
    warning: bool
    policy: Policy
    store_calls: bool  # stage 1 stores irreversible calls for stage 2
    decisions: list[dict] = field(default_factory=list)
    stored: list[dict] = field(default_factory=list)


def history_text(history: list[ChatMessage]) -> str:
    """The agent's calls and results before the proposed call, one line each. The request is passed separately."""
    lines = []
    for message in history[2:-1]:  # skip the system prompt and the request; the last message holds the proposed call
        if isinstance(message, ChatMessageAssistant):
            if message.text:
                lines.append(f"agent: {message.text}")
            for tool_call in message.tool_calls or []:
                lines.append(f"call: {tool_call.function}({json.dumps(tool_call.arguments)})")
        elif isinstance(message, ChatMessageTool):
            lines.append(f"result: {message.error.message if message.error else message.text}")
        elif isinstance(message, ChatMessageUser):
            lines.append(f"user: {message.text}")
    return "\n".join(lines) or "(no earlier calls)"


@approver(name="trustlabel_gate")
def gatekeeper(ctx: EpisodeContext) -> Approver:
    async def approve(message: str, call: ToolCall, view: ToolCallView, history: list[ChatMessage]) -> Approval:
        description, schema = ctx.entries[call.function]
        proposed = Call(call.function, description, dict(call.arguments))
        history_so_far = history_text(history)
        irreversible = call.function in SERVERS[ctx.scenario.kind].irreversible

        if ctx.store_calls and irreversible:
            position = len(ctx.stored) + 1
            stored = StoredCall(ctx.episode, ctx.agent, ctx.scenario, ctx.name_setting, position,
                                history_so_far, proposed, schema)
            ctx.stored.append(stored.to_dict())

        gate_input = GateInput(ctx.scenario.request, history_so_far, proposed, schema,
                               ctx.labels.get(call.function), ctx.warning)
        decision = await ctx.policy(gate_input)

        if decision.verdict == "allow":
            outcome, approval = "allowed", Approval(decision="approve")
        elif decision.verdict == "block":
            outcome, approval = "blocked", Approval(decision="reject", explanation=BLOCKED)
        elif answers_yes(ctx.scenario, proposed):
            outcome, approval = "asked_yes", Approval(decision="approve")
        else:
            outcome, approval = "asked_no", Approval(decision="reject", explanation=DECLINED)

        ctx.decisions.append({
            "tool": call.function, "arguments": dict(call.arguments), "irreversible": irreversible,
            "verdict": decision.verdict, "outcome": outcome, "unreadable": decision.unreadable,
            "reason": decision.reason, "raw": decision.raw,
        })
        return approval

    return approve

