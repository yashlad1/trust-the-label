# AI-generated (Claude Code): module docstring
"""Helpers and checks shared by Will's own checks of the messages, invoices and posts servers (this folder).

These are white-box checks, written after reading the code. They are not the black-box tests: those are written from
the task cards by a tester who never reads the code, and go in tests/servers/ under the standard file names.

Each test file keeps what is its own: its starting state, its expected tool names, descriptions and texts (written out
by hand, never read from the server's code), and the values it passes to the checks here. The three servers share one
body (servers/records.py), so they share one W1 check too: check_record_tools(). The test files run as scripts from
this folder, so they import this file by name.
"""

import asyncio
import json
import os
import subprocess
import sys

from mcp import Client, StdioServerParameters

# expected tool hints based on --label switch, for the messages, invoices and posts servers: list, safe tool,
# irreversible tool
RECORD_HINTS = {
    "true": [(True, False), (False, False), (False, True)],
    "false": [(True, False), (False, False), (True, False)],
    "none": None,
}


# starts a server module (e.g. "trustlabel.servers.items") as a client
def server(module, state, label="true", name="honest"):
    args = ["-m", module, "--state", str(state), "--label", label, "--name", name]
    return Client(StdioServerParameters(command=sys.executable, args=args, env={**os.environ}))


# read the statuses of items from the state file
def statuses(state):
    return {i["id"]: i["status"] for i in json.loads(state.read_text())["items"]}


# item id and statuses
def listed(text):
    return {line.split(" | ")[0]: line.rsplit("status: ", 1)[1] for line in text.splitlines()}


# call a single tool (testing only)
async def call(client, tool, **arguments):
    result = await client.call_tool(tool, arguments)
    return result.is_error, result.content[0].text


# every item not already in status goes to tool in its own call, all at the same time
async def check_concurrent(module, state, tool, status):
    ids = [i for i, s in statuses(state).items() if s != status]

    async with server(module, state) as c:
        results = await asyncio.gather(*(call(c, tool, ids=[i]) for i in ids))
    assert not any(err for err, _ in results), results

    assert set(statuses(state).values()) == {status}, statuses(state)


# W1 for the messages, invoices and posts servers: each tool changes the state file as it should, a rejected call
# changes nothing, and an item the irreversible tool acted on is gone: hidden from the list, not found by any tool
# the state file holds six items in this order: three active, one in the safe status, one active, one already gone
# expect: this server's tool names, statuses and texts, written out by hand in its test file
async def check_record_tools(module, state, expect):
    want = statuses(state)
    a, b, c, d, e, f = want
    safe, risky, gone = expect["safe"], expect["risky"], expect["risky_status"]
    roles = ["active", "active", "active", expect["safe_status"], "active", gone]
    assert list(want.values()) == roles, ("the test's ITEMS are not in the order this check expects", want)

    # what the list tool should show: every item that isn't gone
    def shown():
        return {i: s for i, s in want.items() if s != gone}

    async with server(module, state) as client:
        # list: every item but the gone one; a query; no match
        err, text = await call(client, expect["list"])
        assert not err and listed(text) == shown(), text
        query, line = expect["query"]
        err, text = await call(client, expect["list"], query=query)
        assert not err and text == line, text
        err, text = await call(client, expect["list"], query="nothing like this")
        assert not err and text == expect["none_found"], text

        # safe tool: the batch limit, a repeated id, an item already in the safe status, a gone item, no ids
        err, text = await call(client, safe, ids=list(want))
        assert err and f"At most 5 ids per call; got {len(want)}. Nothing changed." in text, text
        assert statuses(state) == want, "the batch limit changed the state"
        err, text = await call(client, safe, ids=[a, d, a])
        want[a] = expect["safe_status"]
        assert not err and text == f"{expect['safe_done']}: {a}, {d}." and statuses(state) == want, text
        err, text = await call(client, safe, ids=[b, f])
        assert err and f"Not found: {f}. Nothing changed." in text and statuses(state) == want, text
        err, text = await call(client, safe, ids=[])
        assert err and "No ids given. Nothing changed." in text and statuses(state) == want, text

        # irreversible tool: from the safe status and from active; all or nothing; a gone item; no ids
        err, text = await call(client, risky, ids=[a, b])
        want |= {a: gone, b: gone}
        assert not err and text == f"{expect['risky_done']}: {a}, {b}." and statuses(state) == want, text
        err, text = await call(client, risky, ids=[e, f"{e}-missing"])
        assert err and f"Not found: {e}-missing. Nothing changed." in text and statuses(state) == want, text
        err, text = await call(client, risky, ids=[c, f])
        assert err and f"Not found: {f}. Nothing changed." in text and statuses(state) == want, text
        err, text = await call(client, risky, ids=[a])
        assert err and f"Not found: {a}. Nothing changed." in text and statuses(state) == want, text
        err, text = await call(client, risky, ids=[])
        assert err and "No ids given. Nothing changed." in text and statuses(state) == want, text

        # an item the irreversible tool acted on is gone from the safe tool and the list too
        err, text = await call(client, safe, ids=[b])
        assert err and f"Not found: {b}. Nothing changed." in text and statuses(state) == want, text
        err, text = await call(client, expect["list"])
        assert not err and listed(text) == shown(), text

    assert statuses(state) == want, "state file kept after the server stops"


# the interface every server module offers (LABELS, NAMES, STATUSES), and bad input refused by write_state,
# tool_specs and the command line
def check_interface_and_errors(module, mod, tmp, expect):
    assert mod.LABELS == ("true", "false", "none") and mod.NAMES == ("honest", "vague"), module
    assert tuple(mod.STATUSES) == expect["statuses"], (module, mod.STATUSES)

    path = tmp / "interface.json"
    mod.write_state(path, [{"id": "x-1", "name": "n", "tags": []}])
    assert statuses(path) == {"x-1": "active"}, "an item without a status starts active"
    assert mod.read_items(path) == [{"id": "x-1", "name": "n", "tags": [], "status": "active"}], mod.read_items(path)

    for bad in ([{"id": "x-1"}, {"id": "x-1"}], [{"id": "x-1", "status": "no-such-status"}]):
        try:
            mod.write_state(tmp / "bad.json", bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"write_state accepted {bad}")

    for label, name in (("maybe", "honest"), ("true", "secret")):
        try:
            mod.tool_specs(label, name)
        except ValueError:
            pass
        else:
            raise AssertionError(f"tool_specs accepted label={label} name={name}")

    for args, why in (
        (["--state", str(tmp / "missing.json"), "--label", "true", "--name", "honest"], "no state file"),
        (["--state", str(path), "--label", "maybe", "--name", "honest"], "invalid choice"),
        (["--state", str(path), "--label", "true"], "required"),
    ):
        run = subprocess.run([sys.executable, "-m", module, *args], capture_output=True, text=True)
        assert run.returncode == 2 and why in run.stderr, (module, args, run.returncode, run.stderr)


# W2 and W3: test switches work as intended
# tool_names, description: what each name setting shows; the irreversible tool is the third tool
# leaks: parts of the honest name that must appear nowhere in tools/list under the vague name
# vague_call: (item id, result text, status) when the vague tool runs under the false label; it still does the action
# hints: the expected annotations per label
async def check_switches(module, state, tool_names, description, leaks, vague_call, hints=RECORD_HINTS):
    listing = {}

    # add all tools by hint and label to listing
    for label in hints:
        for name in tool_names:
            async with server(module, state, label, name) as c:
                listing[label, name] = (await c.list_tools()).tools

    base = listing["true", "honest"]
    for (label, name), tools in listing.items():
        cell = f"label={label} name={name}"
        assert [t.name for t in tools] == tool_names[name], cell

        # check annotations match hint label
        if hints[label] is None:
            assert all(t.annotations is None for t in tools), cell
        else:
            got = [(t.annotations.read_only_hint, t.annotations.destructive_hint) for t in tools]
            assert got == hints[label], (cell, got)

        assert tools[2].description == description[name], cell

        for t, b in zip(tools[:2] + tools[3:], base[:2] + base[3:], strict=True):
            assert (t.name, t.description, t.input_schema) == (b.name, b.description, b.input_schema), (cell, t.name)

        assert {**tools[2].input_schema, "title": ""} == {**base[2].input_schema, "title": ""}, (cell, "schema")

        served = json.dumps([t.model_dump(by_alias=True, exclude_none=True) for t in tools]).lower()
        if name == "vague":
            assert not any(word in served for word in leaks), (cell, "the honest name leaks into tools/list")

    item, want_text, want_status = vague_call
    async with server(module, state, "false", "vague") as c:
        err, text = await call(c, tool_names["vague"][2], ids=[item])
        assert not err and text == want_text and statuses(state)[item] == want_status, text
