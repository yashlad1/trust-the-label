"""How an episode reaches its tools (Y2): one fresh state file, one stdio MCP server with the episode's two switches,
and the labels the approval layer may read, taken from the server's own specs.

Inspect starts a new server process for every tool call unless the episode runs inside mcp_connection(...), so
episode.py wraps the whole loop in it: one process per episode, one process per state file.
"""

import os
import sys
from pathlib import Path

from inspect_ai.tool import Tool, ToolDef, ToolSource, mcp_server_stdio, mcp_tools

from trustlabel.contracts import Labels, Scenario
from trustlabel.servers.registry import SERVERS


def start_server(scenario: Scenario, label: str, name: str, workdir: str | None = None) -> tuple[ToolSource, Path]:
    """A fresh state file with the job's starting items, and the MCP server over it (started on first use)."""
    registered = SERVERS[scenario.kind]
    state_file = registered.new_state_file(scenario, workdir)

    # the server is a child process: pass PYTHONPATH on when set (needed only when the package isn't installed)
    env = {"PYTHONPATH": os.environ["PYTHONPATH"]} if "PYTHONPATH" in os.environ else None
    server = mcp_server_stdio(
        name=f"{scenario.kind}-server",
        command=sys.executable,
        args=["-m", registered.module.__name__, "--state", str(state_file), "--label", label, "--name", name],
        env=env,
    )
    return mcp_tools(server), state_file


def tool_entries(tools: list[Tool]) -> dict[str, tuple[str, dict]]:
    """name -> (description, input schema), as the agent sees them in tools/list (no annotations)."""
    entries = {}
    for tool in tools:
        tool_def = ToolDef(tool)
        entries[tool_def.name] = (tool_def.description, tool_def.parameters.model_dump(exclude_none=True))
    return entries


def labels_for(kind: str, label: str, name: str) -> dict[str, Labels | None]:
    """tool name -> its labels under these switches, from the server's own specs (None = no annotations)."""
    return {
        tool: None if ann is None else Labels(ann.read_only_hint, ann.destructive_hint)
        for tool, _description, ann in SERVERS[kind].module.tool_specs(label, name)
    }


def final_state(kind: str, state_file: Path) -> dict[str, str]:
    """item id -> status at the end of the episode; the scorer reads only this."""
    return {item["id"]: item["status"] for item in SERVERS[kind].module.read_items(state_file)}
