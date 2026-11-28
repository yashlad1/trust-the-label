# V6a · Stage-1 proposal rates: https://github.com/yashlad1/trust-the-label/issues/17
# V6b · Stage-2 outcome rates per gate condition: https://github.com/yashlad1/trust-the-label/issues/18
# V6c · Stage-3 harm and task success: https://github.com/yashlad1/trust-the-label/issues/19
# V6d · Reference lines on the stored calls: https://github.com/yashlad1/trust-the-label/issues/20
# FP3 task 18 (fp3-tasks.html): the FP3 measures from the logs, as plain rates
"""The FP3 measures, read from Inspect .eval logs: plain rates and the paired comparisons (the tests: analysis/stats.py).

  stage1_table(paths)                        how often each agent proposed an irreversible call (stage 1)
  stage2_rows(paths)                         one row per first-call stage-2 sample (every row kind), and the failed count
  stage2_table(gate, paths, rows, failed_n)  what the gate did with each call, per name, request and condition
  reference_table(gate, paths, rows, failed_n)  never ask, the label rule and the hybrid, computed on the same calls
  stage3_table(logs)                         harm, task success, stray items and failed episodes, per policy
  paired(rows, fixed, a, b)                  the same calls under two settings that differ in one field, as Pair objects
  compare(pairs)                             paired difference in ask rate, in points, with McNemar p and a job-bootstrap CI

The stage-2 tables use the standard rows only (own or swapped request, plain prompt); the intent-sentence and wording
rows are in stage2_rows for their own tables. gate is the gate's name, used in the table titles.

A sample that errored or never got its score is a failed sample. Every table counts failed samples on their own: they
are never dropped silently and never counted as a success. An unreadable gate reply counts as an ask. A log that did not
finish is named in the table's source line, so a cut-short log never looks like a clean one.
"""

from collections import Counter
from pathlib import Path
from typing import NamedTuple

from inspect_ai.log import read_eval_log

from trustlabel.analysis.stats import job_bootstrap_ci, mcnemar_p
from trustlabel.analysis.tables import table
from trustlabel.contracts import Decision, StoredCall
from trustlabel.harness.connection import labels_for
from trustlabel.policies.hybrid import hybrid
from trustlabel.servers.constants import LABELS

# with the call itself, these fields tell one stage-2 sample from another
KEY_FIELDS = ("name", "request", "stored_version", "policy", "label", "warning", "prompt")


def pct(k, n):
    """Percent with the count, like '43% (17/40)'; a cell with no calls prints '– (0/0)'."""
    return f"{(200 * k + n) // (2 * n):.0f}% ({k}/{n})" if n else "– (0/0)"


def pick(rows, spec):
    for k, v in spec.items():
        if rows and not any(r[k] == v for r in rows):
            raise ValueError(f"no row has {k}={v!r}")
    return [r for r in rows if all(r[k] == v for k, v in spec.items())]


class Pair(NamedTuple):  # one stored call judged under both settings: its job and whether the gate asked under each
    call: str
    job: str
    a: bool
    b: bool


def paired(rows, fixed, a, b):
    """Calls judged under both fixed+a and fixed+b, all other fields equal: [Pair(call, job, ask under a, ask under b)]."""
    vary = set(a) | set(b)
    key = lambda r: (r["call"],) + tuple(r[f] for f in KEY_FIELDS if f not in vary)  # noqa: E731
    ra, rb = ({key(r): r for r in pick(rows, {**fixed, **spec})} for spec in (a, b))
    assert len(ra) == len(pick(rows, {**fixed, **a})) and len(rb) == len(pick(rows, {**fixed, **b})), "ambiguous pairing"
    return [Pair(k[0], ra[k]["job"], ra[k]["ask"], rb[k]["ask"]) for k in sorted(ra.keys() & rb.keys())]


def compare(pairs):
    """Paired difference in ask rate (first minus second), in points, with McNemar p and a job-bootstrap 90% CI."""
    n = len(pairs)
    b = sum(x and not y for _c, _j, x, y in pairs)  # asked only under the first
    c = sum(y and not x for _c, _j, x, y in pairs)  # asked only under the second
    lo, hi = job_bootstrap_ci([(j, int(x) - int(y)) for _c, j, x, y in pairs])
    return {"n": n, "ka": sum(x for *_, x, _y in pairs), "kb": sum(y for *_, y in pairs), "b": b, "c": c,
            "d": 100 * (b - c) / n if n else 0.0, "p": mcnemar_p(b, c), "lo": 100 * lo, "hi": 100 * hi}


def failed(s, scorer):
    """A sample that errored or never got its scorer's score (stage 1: never stored its episode)."""
    return bool(s.error) or (scorer not in (s.scores or {}) if scorer else "episode" not in (s.store or {}))


def names(paths):
    """The log file names, and a note naming every log that did not finish."""
    bad = [f"{Path(p).name} ({s})" for p in paths if (s := read_eval_log(p, header_only=True).status) != "success"]
    return ", ".join(Path(p).name for p in paths) + (f"; NOT FINISHED: {', '.join(bad)}" if bad else "")


def standard(rows):
    """The standard stage-2 rows: the call's own or swapped request under the plain gate prompt."""
    return [r for r in rows if r["request"] in ("own", "swapped") and r["prompt"] == "plain"]


def cond_label(policy, label, warning):
    return "gate on call" if policy == "gate_on_call" else f"labels: {label}, warning {'on' if warning else 'off'}"


def stage1_table(paths):
    n, k, bad = Counter(), Counter(), Counter()
    for p in paths:
        log = read_eval_log(p)
        for s in log.samples or []:
            key = (log.eval.model, s.metadata["name"], s.metadata["scenario"]["version"])
            if failed(s, None):
                bad[key] += 1
                continue
            n[key] += 1
            k[key] += bool(s.store["episode"].get("stored_calls"))
    cells = sorted({(a, b) for a, b, _ in n | bad})
    body = [(a, b, *[pct(k.get((a, b, v), 0), n.get((a, b, v), 0)) for v in ("unneeded", "wanted")],
             sum(bad.get((a, b, v), 0) for v in ("unneeded", "wanted"))) for a, b in cells]
    return table("Stage 1: how often each agent proposed an irreversible call (out of its episodes)",
                 ["agent", "name the agent saw", "unneeded versions", "wanted versions", "failed episodes"], body,
                 "each cell is episodes with at least one stored irreversible call, out of the episodes in that cell; "
                 "failed episodes are not in those counts.",
                 f"{names(paths)}; analysis/rates.py; n={sum(n.values())} episodes, {sum(bad.values())} failed")


def stage2_rows(paths):
    """Stage-2 logs of one gate -> (one row per first-call sample, the number of failed first-call samples)."""
    rows, failed_n = [], 0
    for s in [s for p in paths for s in read_eval_log(p).samples or []]:
        call = StoredCall.from_dict(s.metadata["call"])
        if call.position != 1:
            continue
        if failed(s, "gate_outcome"):
            failed_n += 1
            continue
        sc = s.scores["gate_outcome"]
        m = sc.metadata
        rows.append({"call": f"{call.episode}-c{call.position}", "job": m["job"], "kind": m["kind"],
                     "tool": s.metadata["shown_call"]["name"], "answer": sc.answer, "ask": sc.answer != "allowed",
                     "unreadable": sc.value["unreadable"], "version": m["version"], "agent": call.agent, **{f: m[f] for f in KEY_FIELDS}})
    return rows, failed_n


def stage2_table(gate, paths, rows, failed_n):
    rows = standard(rows)
    cells = {}
    for r in rows:
        c = cells.setdefault((r["name"], r["request"], (r["policy"], r["label"], r["warning"])),
                             {"unneeded": [], "wanted": [], "unread": 0, "n": 0})
        c[r["version"]].append(r["answer"])
        c["unread"] += r["unreadable"]
        c["n"] += 1
    body = []
    for (name, request, cond), c in sorted(cells.items(), key=lambda x: (x[0][0], x[0][1], str(x[0][2]))):
        u, w = c["unneeded"], c["wanted"]
        body.append((name, request, cond_label(*cond), 
                     pct(u.count("allowed"), len(u)), pct(u.count("asked_no"), len(u)),
                     pct(w.count("allowed"), len(w)), pct(w.count("asked_yes"), len(w)), pct(w.count("asked_no"), len(w)), 
                     pct(c["unread"], c["n"])))
    return table(f"Stage 2, gate {gate}: what the gate did with each call (out of the calls in that cell)",
                 ["name the gate saw", "request", "condition", "unneeded: allowed (a miss)", "unneeded: asked then no",
                  "wanted: allowed", "wanted: asked then yes (an interruption)", "wanted: asked then no", "unreadable (of all calls in row)"],
                 body, "unneeded and wanted are the version whose request the gate saw; own = the call's own request, "
                       "swapped = its job's other version.",
                 f"{names(paths)}; analysis/rates.py; standard rows, first calls only, n={len(rows)} samples, "
                 f"{failed_n} failed (not in the table)")


def reference_table(gate, paths, rows, failed_n):
    rows = standard(rows)
    base = {"name": "vague", "request": "own", "stored_version": "unneeded"}
    calls = {r["call"]: r for r in pick(rows, {**base, "policy": "gate_on_call"})}
    by = {(r["call"], r["label"]): r["ask"] for r in pick(rows, {**base, "policy": "gate_with_labels", "warning": False})}
    lab = lambda c, x: labels_for(calls[c]["kind"], x, "vague").get(calls[c]["tool"])  # noqa: E731
    allow = lambda f, cs=calls: pct(sum(f(c) for c in cs), len(cs))  # noqa: E731
    body = [("never ask", allow(lambda c: True))]
    body += [(f"label rule, labels {x}", allow(lambda c, x=x: lab(c, x) is not None and lab(c, x).read_only is True))
             for x in LABELS]
    # a call whose gate-with-labels sample failed has no decision to fall back on, so it leaves that line's count
    body += [(f"hybrid, labels {x} (falls back to gate with labels {x}, warning off)",
              allow(lambda c, x=x: hybrid(lab(c, x), Decision("ask" if by[(c, x)] else "allow")).verdict == "allow",
                    [c for c in calls if (c, x) in by]))
             for x in LABELS]
    return table(f"Reference lines, gate {gate}: allowed rate on unneeded calls, vague name, own request (computed, not run)",
                 ["rule", "allowed (a miss)"], body, "same stored calls as the gate rows; never ask allows everything; "
                                                     "each line's count is the calls it could be computed on.",
                 f"{names(paths)}; analysis/rates.py; n={len(calls)} calls, {failed_n} failed samples in this gate's logs")


def stage3_table(logs):
    """logs: {policy label: .eval path}."""
    body = []
    for label, p in logs.items():
        h, u, s, w, a, au, st, bad, total = 0, 0, 0, 0, 0, 0, 0, 0, 0
        for smp in read_eval_log(p).samples or []:
            total += 1
            if failed(smp, "final_state_scorer"):
                bad += 1
                continue
            v = smp.scores["final_state_scorer"].value
            st += v.get("stray", 0) > 0
            if smp.metadata["scenario"]["version"] == "unneeded":
                u += 1
                h += v["harm"]
                first = next((d for d in smp.store["episode"]["decisions"] if d["irreversible"]), None)
                if first:
                    au += 1
                    a += first["outcome"] == "allowed"
            else:
                w += 1
                s += v["success"]
        body.append((label, pct(h, u), pct(s, w), pct(a, au), pct(st, u + w), pct(bad, total)))
    return table("Stage 3: the live loop, per policy (out of episodes)",
                 ["policy", "harm, unneeded episodes", "task success, wanted episodes",
                  "first irreversible decision allowed, unneeded episodes (out of those that reached one)",
                  "episodes that changed an item the user didn't ask about", "failed episodes"], body,
                 "harm is an irreversible action done in an unneeded episode; lower is better for harm, higher for success.",
                 f"{names(logs.values())}; analysis/rates.py")
