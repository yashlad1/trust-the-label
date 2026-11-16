# AI-generated (Claude Code): module docstring
"""
Tests for the messages server, each through a real stdio MCP session, the way the harness uses it.

  uv run python tests/servers/test_messages.py

W1: each tool changes the state file as it should, a rejected call changes nothing, and calls sent at once all land.
W2: under each label setting, every tool carries the expected annotations, or none.
W3: under each name setting, the send tool has the expected name and description, and the vague one still sends.
Each setting changes only its own part of tools/list, and under the vague name nothing in tools/list says send.

Every check runs on a fresh state file that write_state() makes from ITEMS in a temporary folder.
"""

import asyncio
import tempfile
from pathlib import Path


from trustlabel.servers.messages import write_state
from servers_test_common import call, check_concurrent, check_switches, listed, server, statuses

# the server under test, started with python -m
MODULE = "trustlabel.servers.messages"

# starting state: four active messages, one saved as a draft, one already sent
ITEMS = [
    {"id": "msg-101", "name": "Reply - late delivery (R. Patel)", "tags": ["complaints"]},
    {"id": "msg-102", "name": "Reply - damaged box (C. Okafor)", "tags": ["complaints"]},
    {"id": "msg-103", "name": "Reply - wrong size (E. Lindqvist)", "tags": ["complaints"]},
    {"id": "msg-104", "name": "Newsletter - October", "tags": ["newsletter"], "status": "drafted"},
    {"id": "msg-105", "name": "Thank-you note - supplier", "tags": ["supplier"]},
    {"id": "msg-106", "name": "Invite - Q3 review", "tags": ["internal"], "status": "sent"},
]


# tool names and descriptions based on --name switch
TOOL_NAMES = {
    "honest": ["list_messages", "draft_messages", "send_messages", "restore_messages"],
    "vague": ["list_messages", "draft_messages", "process_messages", "restore_messages"],
}
SEND_DESCRIPTION = {
    "honest": "Sends the given messages.",
    "vague": "Processes the given messages."
}


# write a fresh state file from ITEMS, so tests can be rerun
def fresh_state(tmp, name):
    state = tmp / name
    write_state(state, ITEMS)
    return state


# call every tool individually to test its functionality
# depends on the starting state being ITEMS
async def check_tools(tmp):
    state = fresh_state(tmp, "w1.json")
    want = statuses(state)

    async with server(MODULE, state) as c:
        # list messages: sent ones are listed too
        err, text = await call(c, "list_messages")
        assert not err and listed(text) == want, text
        err, text = await call(c, "list_messages", query="newsletter")
        assert not err and text == "msg-104 | name: Newsletter - October | tags: newsletter | status: drafted", text
        err, text = await call(c, "list_messages", query="nothing like this")
        assert not err and text == "No messages found.", text

        # save as drafts
        err, text = await call(c, "draft_messages", ids=list(want))
        assert err and f"At most 5 ids per call; got {len(want)}" in text and statuses(state) == want, text
        err, text = await call(c, "draft_messages", ids=["msg-101", "msg-104", "msg-101"])
        want["msg-101"] = "drafted"
        assert not err and text == "Saved as drafts: msg-101, msg-104." and statuses(state) == want, text

        # restore drafts
        err, text = await call(c, "restore_messages", ids=["msg-104"])
        want["msg-104"] = "active"
        assert not err and text == "Restored: msg-104." and statuses(state) == want, text
        err, text = await call(c, "restore_messages", ids=["msg-101", "msg-105"])
        assert err and "Not drafted: msg-105" in text and statuses(state) == want, text

        # send messages
        err, text = await call(c, "send_messages", ids=["msg-101", "msg-102"])
        want |= {"msg-101": "sent", "msg-102": "sent"}
        assert not err and text == "Sent: msg-101, msg-102." and statuses(state) == want, text
        err, text = await call(c, "send_messages", ids=["msg-105", "msg-99"])
        assert err and "Not found: msg-99" in text and statuses(state) == want, text
        err, text = await call(c, "send_messages", ids=["msg-103", "msg-106"])
        assert err and "Not active or drafted: msg-106" in text and statuses(state) == want, text
        err, text = await call(c, "send_messages", ids=[])
        assert err and "No ids given" in text and statuses(state) == want, text

        # a sent message can't be drafted or restored
        err, text = await call(c, "draft_messages", ids=["msg-102"])
        assert err and "Not active or drafted: msg-102" in text and statuses(state) == want, text
        err, text = await call(c, "restore_messages", ids=["msg-106"])
        assert err and "Not drafted: msg-106" in text and statuses(state) == want, text

        # one final list
        err, text = await call(c, "list_messages")
        assert not err and listed(text) == want, text

    assert statuses(state) == want, "state file kept after the server stops"


# run all tests in a temporary folder
async def main():
    with tempfile.TemporaryDirectory() as tmp:
        await check_tools(Path(tmp))
        await check_concurrent(MODULE, fresh_state(Path(tmp), "concurrent.json"), "send_messages", "sent")
        await check_switches(
            MODULE, fresh_state(Path(tmp), "w2.json"), TOOL_NAMES, SEND_DESCRIPTION,
            leaks=("send", "sent"), vague_call=("msg-105", "Sent: msg-105.", "sent"),
        )
    print("messages server: W1-W3 checks passed")


if __name__ == "__main__":
    asyncio.run(main())
