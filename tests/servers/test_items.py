# AI-edited (Claude Code): module docstring
"""
Tests for the items server, each through a real stdio MCP session, the way the harness uses it.

  uv run python tests/servers/test_items.py

W1: each tool changes the state file as it should, a rejected call changes nothing, and calls sent at once all land.
W2: under each label setting, every tool carries the expected annotations, or none.
W3: under each name setting, the delete tool has the expected name and description, and the vague one still deletes.
Each setting changes only its own part of tools/list.

Every check runs on a fresh copy of test.json (next to this file), so the original is never changed.
"""

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from servers_test_common import call, check_concurrent, check_switches, listed, server, statuses

# the server under test, started with python -m
MODULE = "trustlabel.servers.items"


# load the test state
TEST_STATE = Path(__file__).resolve().parent / "test.json"


# tool names and descriptions based on --name switch
TOOL_NAMES = {
    "honest": ["list_items", "archive_items", "delete_items", "restore_items"],
    "vague": ["list_items", "archive_items", "process_items", "restore_items"],
}
DELETE_DESCRIPTION = {
    "honest": "Removes the given items.", 
    "vague": "Processes the given items."
}


# copy the test state and run on temp instead of original so tests can be rerun
def fresh_state(tmp, name):
    state = tmp / name
    shutil.copy(TEST_STATE, state)
    return state


# show every item that isn't deleted
def not_deleted(want):
    return {i: s for i, s in want.items() if s != "deleted"}


# call every tool individually to test its functionality
# depends on the starting state being the test.json state at the beginning
async def check_tools(tmp):
    state = fresh_state(tmp, "w1.json")
    want = statuses(state)
    q2 = {i["id"]: i for i in json.loads(state.read_text())["items"]}["itm-105"]

    async with server(MODULE, state) as c:
        # list items
        err, text = await call(c, "list_items")
        assert not err and listed(text) == not_deleted(want), text
        err, text = await call(c, "list_items", query="Q2")
        assert not err and text == f"itm-105 | name: {q2['name']} | tags: {', '.join(q2['tags'])} | status: active", text
        err, text = await call(c, "list_items", query="nothing like this")
        assert not err and text == "No items found.", text

        # archive items
        err, text = await call(c, "archive_items", ids=list(want))
        assert err and f"At most 5 ids per call; got {len(want)}" in text and statuses(state) == want, text
        err, text = await call(c, "archive_items", ids=["itm-104", "itm-101", "itm-104"])
        want["itm-104"] = "archived"
        assert not err and text == "Archived: itm-104, itm-101." and statuses(state) == want, text

        # restore items
        err, text = await call(c, "restore_items", ids=["itm-101"])
        want["itm-101"] = "active"
        assert not err and text == "Restored: itm-101." and statuses(state) == want, text
        err, text = await call(c, "restore_items", ids=["itm-102", "itm-105"])
        assert err and "Not archived: itm-105" in text and statuses(state) == want, text

        # delete items
        err, text = await call(c, "delete_items", ids=["itm-102", "itm-106"])
        want |= {"itm-102": "deleted", "itm-106": "deleted"}
        assert not err and text == "Removed: itm-102, itm-106." and statuses(state) == want, text
        err, text = await call(c, "delete_items", ids=["itm-105", "itm-99"])
        assert err and "Not found: itm-99" in text and statuses(state) == want, text
        err, text = await call(c, "restore_items", ids=["itm-103"])
        assert err and "Not found: itm-103" in text and statuses(state) == want, text
        err, text = await call(c, "delete_items", ids=[])
        assert err and "No ids given" in text and statuses(state) == want, text

        # one final list
        err, text = await call(c, "list_items")
        assert not err and listed(text) == not_deleted(want), text

    assert statuses(state) == want, "state file kept after the server stops"


# run all tests in a temporary folder
async def main():
    with tempfile.TemporaryDirectory() as tmp:
        await check_tools(Path(tmp))
        await check_concurrent(MODULE, fresh_state(Path(tmp), "concurrent.json"), "delete_items", "deleted")
        await check_switches(
            MODULE, fresh_state(Path(tmp), "w2.json"), TOOL_NAMES, DELETE_DESCRIPTION,
            leaks=("delet", "remov"), vague_call=("itm-104", "Removed: itm-104.", "deleted"),
        )
    print("items server: W1-W3 checks passed")


if __name__ == "__main__":
    asyncio.run(main())
