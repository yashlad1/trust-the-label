# W6 · Fresh sandbox per episode: https://github.com/yashlad1/trust-the-label/issues/5

# AI-generated (Claude Code): module docstring
"""Checks for the state-changing list (W4), on the server's own tool specs. No server is started.

  uv run python tests/servers/test_registry.py

W4: under every label and name setting, every items tool except list_items is on the list, and under the false label
the delete tool is on it as irreversible although its label says read-only. Every listed name is a real tool, and
every action has the status it leaves.
"""

from trustlabel.servers import items
from trustlabel.servers.registry import SERVERS


# under every label and name setting, every items tool except list_items is on the list;
# under the false label, the delete tool claims read-only and is still on it, as irreversible
def check_items_list():
    server = SERVERS["delete"]
    for label in items.LABELS:
        for name in items.NAMES:
            tools = [tool for tool, _description, _annotations in items.tool_specs(label, name)]

            assert [t for t in tools if t not in server.state_changing] == ["list_items"], (label, name)

    for name, delete_tool in (("honest", "delete_items"), ("vague", "process_items")):
        specs = {tool: annotations for tool, _description, annotations in items.tool_specs("false", name)}
        lie = specs[delete_tool]

        assert lie.read_only_hint and not lie.destructive_hint, (name, "the false label should claim read-only")
        assert delete_tool in server.state_changing and delete_tool in server.irreversible, name


# every server: listed names are real tools, irreversible tools are state-changing, every action has its status
def check_every_server():
    for kind, server in SERVERS.items():
        real = {tool for name in server.module.NAMES for tool, _, _ in server.module.tool_specs("true", name)}
        
        assert server.state_changing <= real, (kind, server.state_changing - real)
        assert server.irreversible <= server.state_changing, kind
        assert set(server.actions.values()) == set(server.status_after), kind
        assert set(server.status_after.values()) <= set(server.module.STATUSES), kind


def main():
    check_items_list()
    check_every_server()
    print("registry: W4 checks passed")


if __name__ == "__main__":
    main()
