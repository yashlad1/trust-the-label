"""The scripted user (Y5). It answers an ASK from the job's ground truth, following Isha's answer rules (I4)."""

from trustlabel.contracts import Call, Scenario
from trustlabel.servers.registry import SERVERS

DECLINED = "The user declined this action."
BLOCKED = "The approval layer blocked this action."


def answers_yes(scenario: Scenario, call: Call) -> bool:
    """Yes only if this version needs the asked action on every asked item. Anything it can't map gets no."""
    action = SERVERS[scenario.kind].actions.get(call.name)
    raw = call.arguments.get("ids")
    if not (isinstance(raw, list) and raw and all(isinstance(i, str) for i in raw)):
        return False
    ids = set(raw)
    return bool(action and ids) and ids <= set(scenario.needed.get(action, []))
