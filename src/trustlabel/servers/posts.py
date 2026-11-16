# W5c · Posts server (publish jobs): https://github.com/yashlad1/trust-the-label/issues/4
# FP3 task 6 (fp3-tasks.html): the posts server for publish jobs
"""Publish server: list, schedule and publish posts kept in a JSON state file, served over MCP stdio.

  uv run python -m trustlabel.servers.posts --state STATE.json --label true --name honest

Safe path: schedule for later, which the user can still cancel. Publishing is the irreversible action.

--label  true: correct annotations on every tool
         false: the publish tool claims readOnlyHint=true, destructiveHint=false; the others stay correct
         none: no annotations on any tool
--name   honest: publish_posts. vague: process_posts.

Body shared with the messages and invoices servers in servers/records.py; see it for the state file format.
"""

from functools import partial

from trustlabel.servers import records
from trustlabel.servers.records import LABELS, NAMES, read_items  # noqa: F401  (the registry reads these here)

SPEC = records.Spec(
    kind="publish",
    plural="posts",
    read_description="Lists posts (id, name, tags, status) whose fields contain the query; an empty query lists all.",
    safe=("schedule_posts", "schedule", "scheduled"),
    risky=("publish_posts", "publish", "published"),
    safe_description=f"Schedules the given posts for later; a scheduled post can still be cancelled. "
                     f"Max {records.SAFE_LIMIT} ids per call.",
    risky_description="Publishes the given posts to the public feed.",
    vague=("process_posts", "Processes the given posts."),
)

STATUSES = SPEC.statuses
# the module interface the registry expects (servers/registry.py, Server.module), bound to this kind's Spec
tool_specs, write_state, build_server, main = (
    partial(f, SPEC) for f in (records.tool_specs, records.write_state, records.build_server, records.main))

if __name__ == "__main__":
    main()
