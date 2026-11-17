# FP3 task 19 (docs/fp3-tasks.html): scripted stage-one logs for fake-model runs
"""Stage-1 logs with real stored calls, on mockllm, so a dry run can exercise stage 2 at full scale.

Plain mockllm never calls a tool, so a plain dry run has no stored calls to replay. This drives the same
stage-1 task with the scripted agent from tests/harness, which lists records and then calls whichever
irreversible tool the server offers. Free: no model is ever called.

  dev/py.sh python dev/scripted_stage1.py <out dir> [--jobs <files>] [--limit N]

Prints the log path, to pass to stage 2 as -T logs=<path>
"""

import argparse
import sys
from pathlib import Path

from inspect_ai import eval as run_eval
from inspect_ai.model import get_model

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests" / "harness"))
from mock_agents import list_then_act_first  # noqa: E402

from trustlabel.harness.tasks import stage1  # noqa: E402
from trustlabel.scenarios.load import DELETE_JOBS, PAY_JOBS, PUBLISH_JOBS, SEND_JOBS  # noqa: E402

ALL_JOBS = ",".join([DELETE_JOBS, SEND_JOBS, PAY_JOBS, PUBLISH_JOBS])
STAGE1_NAMES = "honest"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out")
    ap.add_argument("--jobs", default=ALL_JOBS)
    ap.add_argument("--limit", type=int, default=None, help="episodes, for a quick check")
    a = ap.parse_args()

    log = run_eval(stage1(scenarios=a.jobs, names=STAGE1_NAMES, epochs=1),
                   model=get_model("mockllm/model", custom_outputs=list_then_act_first()),
                   log_dir=a.out, display="none", limit=a.limit)[0]
    stored = sum(len(s.store["episode"]["stored_calls"]) for s in log.samples or [])
    print(f"{log.status}: {len(log.samples or [])} episodes, {stored} stored calls")
    print(log.location)


if __name__ == "__main__":
    main()
