"""Checks that replay.shown_as picks the tool by identity, not list position; fake tool lists only.
Run from the repo root: dev/py.sh python tests/harness/test_name_swap.py"""

from trustlabel.contracts import Call, Scenario, StoredCall
from trustlabel.harness.replay import shown_as
from trustlabel.servers.registry import SERVERS

# kind -> (irreversible tool, a tool that is never renamed)
KINDS = {"delete": ("delete_items", "archive_items"), "send": ("send_messages", None)}
ARGS = {"ids": ["a", "b"]}


def real(module, name):
    return {t[0]: t[1] for t in module.tool_specs("true", name)}


def stored(kind, name_setting, tool, desc):
    sc = Scenario(id="x", kind=kind, version="wanted", request="r", items=[], needed={})
    return StoredCall(episode="e", agent="a", scenario=sc, name_setting=name_setting, position=1,
                      history="", call=Call(tool, desc, dict(ARGS)), input_schema={})


def check(kind, shuffled):
    module = SERVERS[kind].module
    orig = module.tool_specs
    honest, vague = real(module, "honest"), real(module, "vague")
    irrev, other = KINDS[kind]
    if other is None:  # any tool that keeps its name
        other = next(n for n in honest if n in vague and n != irrev)
    new_vague = next(n for n in vague if n not in honest)
    # list order differs under one name setting only
    module.tool_specs = lambda label, name: (lambda s: s[::-1] if name == shuffled else s)(orig(label, name))
    try:
        for made, shown in (("honest", "vague"), ("vague", "honest"), ("honest", "honest"), ("vague", "vague")):
            src = honest if made == "honest" else vague
            tgt = honest if shown == "honest" else vague
            tool = irrev if made == "honest" else new_vague
            want = irrev if shown == "honest" else new_vague
            got = shown_as(stored(kind, made, tool, src[tool]), shown)
            assert (got.name, got.description) == (want, tgt[want]), f"{kind} {made}->{shown} ({shuffled} shuffled): got {got.name}"
            assert got.arguments == ARGS, f"{kind} arguments changed"
            got = shown_as(stored(kind, made, other, src[other]), shown)
            assert (got.name, got.description) == (other, tgt[other]), f"{kind} {other} {made}->{shown}: not kept"
    finally:
        module.tool_specs = orig


for kind in KINDS:
    for shuffled in ("vague", "honest"):
        check(kind, shuffled)
print("ok")
