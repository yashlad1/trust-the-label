# FP3 task 3 (fp3-tasks.html): one shared body for the messages, invoices and posts servers
"""The shared body behind the send, pay and publish servers, built like the items server (servers/items.py).

Those three kinds have the same shape: a read tool, a reversible safe tool, and one irreversible tool that the
label may lie about (the safe step: send saves a draft, pay approves without paying, publish schedules). Only the
nouns, the two action words and the statuses differ, so they share this module and each kind keeps a thin
module of its own (servers/messages.py, invoices.py, posts.py) so the registry can still run it with python -m.

Every kind offers its tools in the order read, safe, irreversible, the same order items.py uses, so the
irreversible tool is always spec 2 under every name setting.

Delete keeps its own file, servers/items.py: it has a fourth tool (restore). The switches and the batch limit come
from servers/constants.py, and the label and name logic, the server setup, the state file and the command line from
servers/servers_common.py, which items.py uses too, so all four servers share one copy of them.
"""

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from trustlabel.servers import servers_common as common
from trustlabel.servers.constants import BATCH_LIMIT, LABELS, NAMES
from trustlabel.servers.servers_common import _dedupe, _done, _line, _move, _searchable, read_items

# the safe tool takes at most this many ids per call, like the items server's archive tool, so an episode needs
# several calls; the thin servers' descriptions read it here
SAFE_LIMIT = BATCH_LIMIT

# every record starts active; the safe and irreversible statuses come from the kind's Spec
START = "active"


@dataclass(frozen=True)
class Spec:
    """One kind's nouns, tools and statuses. tool_specs returns them in the order read, safe, irreversible."""

    kind: str  # the Kind literal in contracts.py
    plural: str  # "messages": the read tool is list_<plural> and the vague name ends in it
    read_description: str
    safe: tuple[str, str, str]  # (tool, the action word Scenario.needed uses, the status it leaves)
    risky: tuple[str, str, str]  # the irreversible one, same shape
    safe_description: str
    risky_description: str
    vague: tuple[str, str]  # (tool, description) for the irreversible tool under the vague name

    @property
    def statuses(self) -> tuple[str, str, str]:
        return (START, self.safe[2], self.risky[2])

    @property
    def read_tool(self) -> str:
        return f"list_{self.plural}"

    def risky_names(self) -> dict[str, tuple[str, str]]:
        """name switch -> (tool, description) for the irreversible tool."""
        return {"honest": (self.risky[0], self.risky_description), "vague": self.vague}

    def actions(self) -> dict[str, str]:
        """Every state-changing tool -> its action word, the irreversible one under both names."""
        return {self.safe[0]: self.safe[1], **{tool: self.risky[1] for tool, _d in self.risky_names().values()}}

    def irreversible(self) -> frozenset[str]:
        return frozenset(tool for tool, _d in self.risky_names().values())

    def status_after(self) -> dict[str, str]:
        return {self.safe[1]: self.safe[2], self.risky[1]: self.risky[2]}


IDS = Annotated[list[str], Field(description="Record ids.")]
QUERY = Annotated[str, Field(description="Text to match against record fields.")]


def tool_specs(spec, label, name):
    """[(tool, description, annotations or None)] in the order read, safe, irreversible."""
    descriptions = {
        spec.read_tool: spec.read_description,
        spec.safe[0]: spec.safe_description,
        spec.risky[0]: spec.risky_description,
    }
    # MCP tool hints: (readOnlyHint, destructiveHint); the false label lies on the irreversible tool only
    correct = {spec.read_tool: (True, False), spec.safe[0]: (False, False), spec.risky[0]: (False, True)}
    return common.tool_specs(label, name, descriptions, correct, spec.risky[0], spec.vague)


def build_server(spec, state, label, name):
    """MCP server over one state file, its tools named and labeled per the two switches."""
    state = Path(state)
    safe_status, risky_status = spec.safe[2], spec.risky[2]

    async def read(query: QUERY = "") -> str:
        q = query.strip().lower()
        found = [i for i in read_items(state) if i["status"] != risky_status and q in _searchable(i)]
        return "\n".join(_line(i) for i in found) if found else f"No {spec.plural} found."

    async def safe(ids: IDS) -> str:
        ids = _dedupe(ids)
        if len(ids) > SAFE_LIMIT:
            raise ToolError(f"At most {SAFE_LIMIT} ids per call; got {len(ids)}. Nothing changed.")
        return _done(spec.safe[2].capitalize(), _move(state, ids, safe_status, (START, safe_status), risky_status))

    async def risky(ids: IDS) -> str:
        return _done(spec.risky[2].capitalize(),
                     _move(state, _dedupe(ids), risky_status, (START, safe_status), risky_status))

    return common.make_server(spec.kind, (read, safe, risky), tool_specs(spec, label, name))


def write_state(spec, path, items):
    """Fresh state file; records without a status start active."""
    common.write_state(path, items, spec.statuses)


def main(spec):
    """Command line shared by the kind modules; the state file and both switches are required."""
    common.main(f"{spec.kind} MCP server over a JSON state file (stdio).", partial(build_server, spec))
