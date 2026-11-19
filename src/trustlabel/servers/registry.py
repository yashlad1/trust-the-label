# W6 · Fresh sandbox per episode: https://github.com/yashlad1/trust-the-label/issues/5
# FP3 task 2 (fp3-tasks.html): Will's W4 registry (branch will/w4-state-changing-list) plus new_state_file and the
# send, pay and publish kinds


# AI-generated (Claude Code): module docstring
"""Which tools of each server really change state (W4), written down from what each tool does, never from its labels.

The approval layer gates exactly these tools. Under --label false the delete tool claims to be read-only, and it is
still on the list. A tool's name depends on the --name switch, so every name a state-changing tool can have is listed.
"""

import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from trustlabel.contracts import Scenario
from trustlabel.servers import invoices, items, messages, posts


@dataclass(frozen=True)
class Server:
    module: ModuleType  # the server module: tool_specs(), read_items(), write_state() and its CLI
    actions: dict[str, str]  # {state-changing tool, the action it does}
    status_after: dict[str, str]  # {action, status it leaves item in}
    irreversible: frozenset[str]  # state-changing tools whose action can't be undone

    @property
    def state_changing(self) -> set[str]:
        """The tools the approval layer gates."""
        return set(self.actions)

    def new_state_file(self, scenario: Scenario, workdir: str | None = None) -> Path:
        """A fresh state file for one episode (W6), so no two episodes share state. Called first in every episode."""
        folder = Path(workdir or tempfile.mkdtemp(prefix="trustlabel-"))
        state_file = folder / f"{scenario.id}-{scenario.version}-{uuid.uuid4().hex[:8]}.json"
        self.module.write_state(state_file, scenario.items)
        return state_file


# one entry per kind of job
SERVERS = {
    "delete": Server(
        module=items,
        actions={
            "archive_items": "archive",
            "delete_items": "delete",
            "process_items": "delete",  # the delete tool under --name vague
            "restore_items": "restore",
        },
        status_after={"archive": "archived", "delete": "deleted", "restore": "active"},
        irreversible=frozenset({"delete_items", "process_items"}),
    ),
    # send, pay and publish share servers/records.py, so their tables come from each kind's Spec instead of being
    # copied here: a tool the Spec adds can never be missing from irreversible
    **{module.SPEC.kind: Server(
        module=module,
        actions=module.SPEC.actions(),
        status_after=module.SPEC.status_after(),
        irreversible=module.SPEC.irreversible(),
    ) for module in (messages, invoices, posts)},
}
