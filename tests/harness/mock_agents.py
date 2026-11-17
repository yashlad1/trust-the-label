"""Fake mockllm agents (list_then_act_first, list_then_delete_first) and gate stand-ins; imported by test_stages.py."""

from inspect_ai.model import ModelOutput

from trustlabel.servers.registry import SERVERS

MODEL = "mockllm/model"


def list_then_act_first(kind=None, n=3, seen_tools=None):
    """Turn 0 lists all items, turn 1 calls the irreversible tool on the first n ids, later turns say Done."""
    kinds = [kind] if kind else list(SERVERS)
    irreversible = set().union(*(SERVERS[k].irreversible for k in kinds))

    def respond(messages, tools, tool_choice, config):
        if seen_tools is not None:
            seen_tools.append(tools)
        offered = [t.name for t in tools]
        turn = sum(m.role == "assistant" for m in messages)
        if turn == 0:
            listers = [t for t in offered if t.startswith("list_")]
            if not listers:
                raise ValueError(f"no list_ tool offered; offered tools: {offered}")
            return ModelOutput.for_tool_call(MODEL, listers[0], {"query": ""})
        if turn == 1:
            lines = messages[-1].text.splitlines()
            ids = [line.split(" | ")[0] for line in lines if " | " in line][:n]
            hits = [t for t in offered if t in irreversible]
            if not hits:
                raise ValueError(f"no irreversible tool offered for kind {kind!r}; offered tools: {offered}")
            return ModelOutput.for_tool_call(MODEL, hits[0], {"ids": ids})
        return ModelOutput.from_content(MODEL, "Done.")

    return respond


def list_then_delete_first(n=3, seen_tools=None):
    return list_then_act_first("delete", n, seen_tools)


def allow_gate(messages, tools, tool_choice, config):
    return ModelOutput.from_content(MODEL, "ALLOW\nok")


def ask_gate(messages, tools, tool_choice, config):
    return ModelOutput.from_content(MODEL, "ASK\ncheck")


def garbled_gate(messages, tools, tool_choice, config):
    return ModelOutput.from_content(MODEL, "Unsure about this call.")
