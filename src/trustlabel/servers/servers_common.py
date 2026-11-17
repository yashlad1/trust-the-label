# AI-generated (Claude Code): module docstring
"""Functions every server shares: items (servers/items.py) and, through servers/records.py, messages, invoices and posts.

tool_specs, make_server, write_state and main hold everything the servers do alike; each caller passes its own tool
names, descriptions, hints and statuses, and keeps its own tool functions. The helpers below them work on the JSON
state file, which is {"items": [...]} for every server. One copy here means the label and name switches work the same
way on all four servers.

Each server module keeps its own tool_specs(label, name), write_state(path, items), read_items(path) and main(), so
items.tool_specs, messages.tool_specs and the rest still work for the harness, the scorer and python -m.
"""

import argparse
import json
import os
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from trustlabel.servers.constants import LABELS, LIE, NAMES


# what tools/list shows under one label and name setting
# the irreversible tool gets the lie under --label false, and the vague name and description under --name vague
def tool_specs(label, name, descriptions, correct, irreversible, vague):
    """[(tool name, description, annotations or None)] in the order of descriptions."""
    if label not in LABELS or name not in NAMES:
        raise ValueError(f"unknown setting: label={label!r}, name={name!r}")

    specs = []
    for tool, description in descriptions.items():
        read_only, destructive = LIE if label == "false" and tool == irreversible else correct[tool]
        annotations = None if label == "none" else ToolAnnotations(read_only_hint=read_only, destructive_hint=destructive)
        
        if tool == irreversible and name == "vague":
            tool, description = vague
        specs.append((tool, description, annotations))

    return specs


# MCP server with the given tool functions, each named and labeled by its entry in specs (from tool_specs)
def make_server(title, tools, specs):
    server = MCPServer(title, log_level="WARNING")

    # add tools and their labels to the server
    for fn, (tool, description, annotations) in zip(tools, specs, strict=True):
        fn.__name__ = tool
        server.add_tool(fn, name=tool, description=description, annotations=annotations, structured_output=False)

    return server


# write fresh state file from item statuses. items without a status are active
def write_state(path, items, statuses):
    fresh, seen = [], set()

    for raw in items:
        item = {**raw, "status": raw.get("status", "active")}

        if item["id"] in seen:
            raise ValueError(f"duplicate id {item['id']!r}")

        if item["status"] not in statuses:
            raise ValueError(f"{item['id']!r} has unknown status {item['status']!r}")

        seen.add(item["id"])
        fresh.append(item)

    _save(Path(path), fresh)


# command line; the state file and both switches are required, so no run gets a default
def main(description, build_server):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--state", required=True, help="JSON state file made by write_state()")
    parser.add_argument("--label", required=True, choices=LABELS)
    parser.add_argument("--name", required=True, choices=NAMES)
    args = parser.parse_args()
    if not Path(args.state).is_file():
        parser.error(f"no state file at {args.state}")
    build_server(args.state, args.label, args.name).run()


# ----------------------------------- Helper functions -----------------------------------


# every item in the state file regardless of status
def read_items(path):
    return json.loads(Path(path).read_text())["items"]


# change the status of items
# all or nothing, if one cannot be changed then change none of them
# items in gone_status count as not found: "deleted" on the items server, the irreversible status on the others
def _move(state, ids, to, allowed_from, gone_status="deleted"):
    if not ids:
        raise ToolError("No ids given. Nothing changed.")

    items = {i["id"]: i for i in read_items(state)}
    missing = [i for i in ids if i not in items or items[i]["status"] == gone_status]
    if missing:
        raise ToolError(f"Not found: {', '.join(missing)}. Nothing changed.")

    wrong = [i for i in ids if items[i]["status"] not in allowed_from]
    if wrong:
        raise ToolError(f"Not {' or '.join(allowed_from)}: {', '.join(wrong)}. Nothing changed.")

    for i in ids:
        items[i]["status"] = to
    _save(state, list(items.values()))
    return ids


# save the state file
# write through a temporary file, so the state file is never left half-written
def _save(path, items):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"items": items}, indent=2))
    os.replace(tmp, path)


# text result of state-changing call
def _done(verb, ids):
    return f"{verb}: {', '.join(ids)}."


# order-preserving de-duplication of ids
def _dedupe(ids):
    return list(dict.fromkeys(ids))


# flatten an item's fields into lowercase text for search
def _searchable(item):
    parts = []
    for value in item.values():
        parts.extend(value if isinstance(value, list) else [value])

    return " ".join(str(p) for p in parts).lower()


# format one item as a single readable line
def _line(item):
    fields = [f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in item.items() if k not in ("id", "status")]
    return " | ".join([item["id"], *fields, f"status: {item['status']}"])
