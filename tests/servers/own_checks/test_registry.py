# W6 · Fresh sandbox per episode: https://github.com/yashlad1/trust-the-label/issues/5


# AI-generated (Claude Code): module docstring
"""Checks for the state-changing list (W4), on the server's own tool specs. No server is started.

  uv run python tests/servers/own_checks/test_registry.py

W4: under every label and name setting, every items tool except list_items is on the list, and under the false label
the delete tool is on it as irreversible although its label says read-only. Every listed name is a real tool, and
every action has the status it leaves.

W5: the same list check for the messages, invoices and posts servers, with the send, pay
and publish tools in place of the delete tool. Their tables, which the registry builds from each server's Spec,
match the tables written out by hand below, and every job's needed actions are ones the registry knows.

W6: new_state_file gives every episode a fresh state file of its own, so two episodes in a row don't share state.

Will's own white-box check, written after reading the code (see servers_test_common.py). The black-box test
from the task card goes in tests/servers/ under this file's name.
"""

import dataclasses
import json
import shutil
import tempfile
from pathlib import Path

from trustlabel.scenarios.load import DELETE_JOBS, PAY_JOBS, PUBLISH_JOBS, SEND_JOBS, load_scenarios
from trustlabel.servers import items
from trustlabel.servers.registry import SERVERS

# every kind's job file
JOBS = {"delete": DELETE_JOBS, "send": SEND_JOBS, "pay": PAY_JOBS, "publish": PUBLISH_JOBS}


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


# kind -> (its list tool, its irreversible tool under each name setting)
W5_SERVERS = {
    "send": ("list_messages", {"honest": "send_messages", "vague": "process_messages"}),
    "pay": ("list_invoices", {"honest": "pay_invoices", "vague": "process_invoices"}),
    "publish": ("list_posts", {"honest": "publish_posts", "vague": "process_posts"}),
}


# under every label and name setting, every tool except the list tool is on the list;
# under the false label, the irreversible tool claims read-only and is still on it, as irreversible
def check_w5_lists():
    for kind, (list_tool, irreversible_tool) in W5_SERVERS.items():
        server = SERVERS[kind]
        for label in server.module.LABELS:
            for name in server.module.NAMES:
                tools = [tool for tool, _description, _annotations in server.module.tool_specs(label, name)]

                assert [t for t in tools if t not in server.state_changing] == [list_tool], (kind, label, name)

        for name, tool in irreversible_tool.items():
            specs = {t: annotations for t, _description, annotations in server.module.tool_specs("false", name)}
            lie = specs[tool]

            assert lie.read_only_hint and not lie.destructive_hint, (kind, name, "the false label should claim read-only")
            assert tool in server.state_changing and tool in server.irreversible, (kind, name)


# the shape the registry card promises: keyed by the four job kinds, a frozen Server, irreversible a frozenset;
# no two kinds share a status name except the starting status "active"
def check_card_shape():
    assert set(SERVERS) == {"delete", "send", "pay", "publish"}, sorted(SERVERS)

    for kind, server in SERVERS.items():
        assert isinstance(server.irreversible, frozenset), (kind, type(server.irreversible))
        try:
            server.irreversible = frozenset()
        except dataclasses.FrozenInstanceError:
            pass
        else:
            raise AssertionError(f"{kind}: Server is not frozen")

    seen = {}
    for kind, server in SERVERS.items():
        for status in set(server.module.STATUSES) - {"active"}:
            assert status not in seen, (status, seen.get(status), kind)
            seen[status] = kind


# kind -> (actions, status_after, irreversible), written out by hand: what the registry should build from each Spec
W5_TABLES = {
    "send": (
        {"draft_messages": "draft", "send_messages": "send", "process_messages": "send"},
        {"draft": "drafted", "send": "sent"},
        {"send_messages", "process_messages"},
    ),
    "pay": (
        {"approve_invoices": "approve", "pay_invoices": "pay", "process_invoices": "pay"},
        {"approve": "approved", "pay": "paid"},
        {"pay_invoices", "process_invoices"},
    ),
    "publish": (
        {"schedule_posts": "schedule", "publish_posts": "publish", "process_posts": "publish"},
        {"schedule": "scheduled", "publish": "published"},
        {"publish_posts", "process_posts"},
    ),
}


# the registry's tables for send, pay and publish are the ones written out above
def check_w5_tables():
    for kind, (actions, status_after, irreversible) in W5_TABLES.items():
        server = SERVERS[kind]

        assert server.actions == actions, (kind, server.actions)
        assert server.status_after == status_after, (kind, server.status_after)
        assert server.irreversible == irreversible, (kind, server.irreversible)


# every job's kind has a server, and every needed action is one that server's registry entry knows
def check_jobs_match_registry():
    for kind, path in JOBS.items():
        server = SERVERS[kind]
        for scenario in load_scenarios(path):
            assert scenario.kind == kind, (scenario.id, scenario.kind)
            assert set(scenario.needed) <= set(server.status_after), (scenario.id, scenario.needed)


# read the statuses of items from a state file
def statuses(state):
    return {i["id"]: i["status"] for i in json.loads(Path(state).read_text())["items"]}


# W6: two episodes of the same job get two separate fresh state files, for every kind; a change in one episode's
# file leaves the other's alone, the next episode starts fresh again, and the scenario itself is never changed
def check_new_state_file():
    with tempfile.TemporaryDirectory() as tmp:
        for kind, path in JOBS.items():
            server = SERVERS[kind]
            scenario = load_scenarios(path)[0]
            items_before = json.dumps(scenario.items, sort_keys=True)
            start = {item["id"]: "active" for item in scenario.items}

            first, second = server.new_state_file(scenario, tmp), server.new_state_file(scenario, tmp)
            assert first != second and first.parent == second.parent == Path(tmp), (kind, first, second)
            assert statuses(first) == statuses(second) == start, kind

            # episode 1 runs the irreversible action on every item; episode 2's file doesn't change
            gone = server.status_after[server.actions[sorted(server.irreversible)[0]]]
            server.module.write_state(first, [{**item, "status": gone} for item in scenario.items])
            assert set(statuses(first).values()) == {gone} and statuses(second) == start, kind

            third = server.new_state_file(scenario, tmp)
            assert statuses(third) == start and json.dumps(scenario.items, sort_keys=True) == items_before, kind

            # with no workdir, each episode gets a new temporary folder of its own
            own_a, own_b = server.new_state_file(scenario), server.new_state_file(scenario)
            try:
                assert own_a.parent != own_b.parent and statuses(own_a) == statuses(own_b) == start, kind
            finally:
                shutil.rmtree(own_a.parent)
                shutil.rmtree(own_b.parent)


def main():
    check_items_list()
    check_every_server()
    check_w5_lists()
    check_card_shape()
    check_w5_tables()
    check_jobs_match_registry()
    check_new_state_file()
    print("registry: W4, W5 and W6 checks passed")


if __name__ == "__main__":
    main()
