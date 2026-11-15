# FP3 task 11 (docs/fp3-tasks.html): the four job-file constants and load_scenarios
"""Where the jobs live and how to read them.

DELETE_JOBS, SEND_JOBS, PAY_JOBS and PUBLISH_JOBS are the paths of the four job files next to this module
(delete.json, send.json, pay.json, publish.json). Each file holds the jobs of one kind, every job in its two
versions, unneeded and wanted.

load_scenarios(path) reads one job file and returns a list of Scenario objects, one per version of each job, in
file order. Without a path it reads delete.json.
"""

import json
from pathlib import Path

from trustlabel.contracts import Scenario

DELETE_JOBS = str(Path(__file__).with_name("delete.json"))
SEND_JOBS = str(Path(__file__).with_name("send.json"))
PAY_JOBS = str(Path(__file__).with_name("pay.json"))
PUBLISH_JOBS = str(Path(__file__).with_name("publish.json"))


def load_scenarios(path: str = DELETE_JOBS) -> list[Scenario]:
    return [Scenario(**job) for job in json.loads(Path(path).read_text())]
