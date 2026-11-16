# FP3 task 14 (docs/fp3-tasks.html): the job checker and the wording-file check
"""Check every job file against the rules the later stages depend on.

  PYTHONPATH=src python -m trustlabel.scenarios.check                 # the four job files
  PYTHONPATH=src python -m trustlabel.scenarios.check <file> [<file>] # named files only
  PYTHONPATH=src python -m trustlabel.scenarios.check --wording <file.json> [<file>]  # also a wording file

Per job id:
  - exactly two versions, unneeded and wanted;
  - the same records in the same order, and the same target ids, so a call can be shown under either version's
    request without changing anything else;
  - the wanted request keeps the unneeded request's first sentence and its last sentence, and adds the reason
    in between;
  - the unneeded version needs only its kind's safe action, the wanted version only its irreversible action;
  - every target id is a record of that job, and no record id repeats;
  - the job id is not reused by another kind, since the sample id and the bootstrap's cluster both come from it.

Exit status 1 and one line per problem, so a run can stop before paying for a broken job file.
"""

import json
import re
import sys

from trustlabel.scenarios.load import DELETE_JOBS, PAY_JOBS, PUBLISH_JOBS, SEND_JOBS, load_scenarios
from trustlabel.servers.registry import SERVERS


def sentences(text: str) -> list[str]:
    """The request split on sentence ends, so the first and last sentence can be compared."""
    return [s.strip() for s in re.split(r"(?<=\.)\s+", text.strip()) if s.strip()]


def problems(jobs) -> list[str]:
    """Every rule a job file breaks, as plain lines. An empty list means the file is usable."""
    found = []
    by_id: dict[tuple[str, str], dict] = {}
    for job in jobs:
        by_id.setdefault((job.kind, job.id), {})[job.version] = job

    # a job id must be unique across kinds: the sample id and the bootstrap's cluster both come from it
    kinds_per_id: dict[str, set[str]] = {}
    for kind, job_id in by_id:
        kinds_per_id.setdefault(job_id, set()).add(kind)
    for job_id, kinds in sorted(kinds_per_id.items()):
        if len(kinds) > 1:
            found.append(f"job id {job_id} is used by more than one kind ({', '.join(sorted(kinds))})")

    for (kind, job_id), versions in sorted(by_id.items()):
        where = f"{kind} {job_id}"
        if set(versions) != {"unneeded", "wanted"}:
            found.append(f"{where}: versions are {sorted(versions)}, expected unneeded and wanted")
            continue
        unneeded, wanted = versions["unneeded"], versions["wanted"]

        if kind not in SERVERS:
            found.append(f"{where}: no server registered for this kind")
            continue
        server = SERVERS[kind]
        safe = {a for t, a in server.actions.items() if t not in server.irreversible}
        risky = {server.actions[t] for t in server.irreversible}

        # the two versions must differ only in the request and the action
        if [i["id"] for i in unneeded.items] != [i["id"] for i in wanted.items]:
            found.append(f"{where}: the two versions list different records")
        if list(unneeded.needed.values()) != list(wanted.needed.values()):
            found.append(f"{where}: the two versions target different records")

        # same first sentence, same last sentence, a reason added in between
        u, w = sentences(unneeded.request), sentences(wanted.request)
        if not u or not w:
            found.append(f"{where}: an empty request")
        else:
            if u[0] != w[0]:
                found.append(f"{where}: the wanted request changes the first sentence")
            if u[-1] != w[-1]:
                found.append(f"{where}: the wanted request changes the last sentence")
            if len(w) <= len(u):
                found.append(f"{where}: the wanted request adds no reason")

        # each version asks for its own kind of action
        for version, job, allowed in (("unneeded", unneeded, safe), ("wanted", wanted, risky)):
            actions = set(job.needed)
            if not actions <= allowed:
                found.append(f"{where} {version}: needs {sorted(actions)}, expected one of {sorted(allowed)}")

        # the records themselves
        for version, job in (("unneeded", unneeded), ("wanted", wanted)):
            ids = [i["id"] for i in job.items]
            if len(set(ids)) != len(ids):
                found.append(f"{where} {version}: a record id appears twice")
            unknown = [i for group in job.needed.values() for i in group if i not in set(ids)]
            if unknown:
                found.append(f"{where} {version}: targets records it does not list: {', '.join(unknown)}")
            if not job.needed or not any(job.needed.values()):
                found.append(f"{where} {version}: targets no records")
    return found


def wording_problems(jobs, wording: dict) -> list[str]:
    """A wording file must cover exactly the checked jobs and keep the unneeded request's first and last sentence."""
    found = []
    unneeded = {j.id: j for j in jobs if j.version == "unneeded"}
    for job_id in sorted(unneeded.keys() - wording.keys()):
        found.append(f"wording {job_id}: no entry for this job")
    for job_id in sorted(wording.keys() - unneeded.keys()):
        found.append(f"wording {job_id}: not one of the checked jobs")
    for job_id in sorted(wording.keys() & unneeded.keys()):
        entry = wording[job_id]
        base = sentences(unneeded[job_id].request)
        for key in ("unneeded_loud", "wanted_calm"):
            text = entry.get(key) if isinstance(entry, dict) else None
            if not isinstance(text, str) or not text.strip():
                found.append(f"wording {job_id}: {key} is missing or empty")
                continue
            s = sentences(text)
            if s[:1] != base[:1]:
                found.append(f"wording {job_id} {key}: the first sentence differs from the unneeded request's")
            if s[-1:] != base[-1:]:
                found.append(f"wording {job_id} {key}: the last sentence differs from the unneeded request's")
    return found


def main():
    args = sys.argv[1:]
    wording = None
    if "--wording" in args:
        i = args.index("--wording")
        wording = json.loads(open(args[i + 1]).read())
        args = args[:i] + args[i + 2:]
    paths = args or [DELETE_JOBS, SEND_JOBS, PAY_JOBS, PUBLISH_JOBS]
    jobs = [job for path in paths for job in load_scenarios(path)]
    found = problems(jobs)
    if wording is not None:
        found += wording_problems(jobs, wording)
    for line in found:
        print(line)
    ids = {(j.kind, j.id) for j in jobs}
    print(f"checked {len(jobs)} scenarios, {len(ids)} jobs, {len({k for k, _ in ids})} kinds: "
          f"{len(found)} problem(s)")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
