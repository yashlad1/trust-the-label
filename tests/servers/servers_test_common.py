# AI-generated (Claude Code): module docstring
"""Helpers and checks that every server test (items, messages, invoices, posts) shares.

Each test file keeps what is its own: its starting state, its expected tool names and description, its W1 check_tools()
sequence, and the values it passes to the checks here. The test files run as scripts from this folder, so they import
this file by name.
"""

import asyncio
import json
import sys

from mcp import Client, StdioServerParameters

# expected tool hints based on --label switch, in the order list, safe path, irreversible tool, restore
HINTS = {
    "true": [(True, False), (False, False), (False, True), (False, False)],
    "false": [(True, False), (False, False), (True, False), (False, False)],
    "none": None,
}


# starts a server module (e.g. "trustlabel.servers.items") as a client
def server(module, state, label="true", name="honest"):
    args = ["-m", module, "--state", str(state), "--label", label, "--name", name]
    return Client(StdioServerParameters(command=sys.executable, args=args))


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


# W2 and W3: test switches work as intended
# tool_names, description: what each name setting shows; the irreversible tool is the third tool
# leaks: parts of the honest name that must appear nowhere in tools/list under the vague name
# vague_call: (item id, result text, status) when the vague tool runs under the false label; it still does the action
async def check_switches(module, state, tool_names, description, leaks, vague_call):
    listing = {}

    # add all tools by hint and label to listing
    for label in HINTS:
        for name in tool_names:
            async with server(module, state, label, name) as c:
                listing[label, name] = (await c.list_tools()).tools

    base = listing["true", "honest"]
    for (label, name), tools in listing.items():
        cell = f"label={label} name={name}"
        assert [t.name for t in tools] == tool_names[name], cell

        # check annotations match hint label
        if HINTS[label] is None:
            assert all(t.annotations is None for t in tools), cell
        else:
            got = [(t.annotations.read_only_hint, t.annotations.destructive_hint) for t in tools]
            assert got == HINTS[label], (cell, got)

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
