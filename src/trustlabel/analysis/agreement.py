# FP3 task 21 (fp3-tasks.html): blind labeling sheets and the agreement between two labelers
"""Two-person labeling: blind sheets for two labelers, then how far they agree with each other and with the intended
version (unneeded -> the safe action is enough, wanted -> it needs the irreversible one).

  PYTHONPATH=src python -m trustlabel.analysis.agreement sheet <out dir> <job files...> [--wording <wording json>]
  PYTHONPATH=src python -m trustlabel.analysis.agreement agree <key.csv> <a.csv> <b.csv>

The sheet hides the version and shuffles the order, so each request is judged on its own words. With --wording it also
holds each job's two added requests (a high-stakes unneeded one and a calm wanted one), so the 80 job versions and the
80 added requests are labeled together. key.csv maps rows back to jobs and versions: keep it away from the labelers.
"""

import argparse
import csv
import json
import random
from pathlib import Path
from trustlabel.analysis.rates import pct

ANSWERS = ("irreversible", "safe", "unsure")
RISKY = {"delete": "deleted for good", "send": "sent", "pay": "paid", "publish": "published"}
SAFE = {"delete": "archived", "send": "saved as drafts", "pay": "approved without paying", "publish": "scheduled"}
EXPECTED = {"unneeded": "safe", "wanted": "irreversible", "unneeded_loud": "safe", "wanted_calm": "irreversible"}


def sheet(out_dir, paths, wording=None, seed=0):
    """Write sheet.csv and key.csv for every job version (and every added request, with a wording file); return the
    number of rows."""
    jobs = [s for p in paths for s in json.loads(Path(p).read_text())]
    rows = [(s["id"], s["kind"], s["version"], s["request"]) for s in jobs]
    if wording:
        kinds = {s["id"]: s["kind"] for s in jobs}
        rows += [(job, kinds[job], version, text) for job, entry in json.loads(Path(wording).read_text()).items()
                 for version, text in entry.items()]
    random.Random(seed).shuffle(rows)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "sheet.csv", "w", newline="") as f, open(out / "key.csv", "w", newline="") as k:
        sheet_rows, key_rows = csv.writer(f), csv.writer(k)
        sheet_rows.writerow(["row", "kind", "request", "question", "answer", "note"])
        key_rows.writerow(["row", "job", "kind", "version"])
        for row, (job, kind, version, request) in enumerate(rows, 1):
            question = (f"Would the user want these {RISKY[kind]} (cannot be undone), "
                        f"or is {SAFE[kind]} enough? Answer irreversible, safe or unsure.")
            sheet_rows.writerow([row, kind, request, question, "", ""])
            key_rows.writerow([row, job, kind, version])
    return len(rows)


def kappa(a, b):
    """Cohen's kappa of two equally long label lists."""
    if not a or len(a) != len(b):
        raise ValueError("kappa needs two equally long, non-empty label lists")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(c) / n) * (b.count(c) / n) for c in set(a) | set(b))
    if expected == 1:  # both labelers used one and the same label throughout, so they agree everywhere
        return 1.0
    return (observed - expected) / (1 - expected)


def answers(path):
    with open(path, newline="") as f:
        got = {int(r["row"]): r["answer"].strip().lower() for r in csv.DictReader(f)}
    bad = sorted(r for r, a in got.items() if a not in ANSWERS)
    if bad:
        raise ValueError(f"{path}: rows {bad[:10]} need one of {', '.join(ANSWERS)}")
    return got


def agree(key_path, a_path, b_path):
    """Compare two filled sheets with each other and with the intended versions in the key."""
    with open(key_path, newline="") as f:
        key = {int(r["row"]): r for r in csv.DictReader(f)}
    a, b = answers(a_path), answers(b_path)
    if set(a) != set(key) or set(b) != set(key):
        raise ValueError("the two sheets and the key must hold the same rows")
    rows = sorted(key)
    expect = {r: EXPECTED[key[r]["version"]] for r in rows}
    return {"n": len(rows), "agree": sum(a[r] == b[r] for r in rows),
            "kappa": kappa([a[r] for r in rows], [b[r] for r in rows]),
            "a_off": [r for r in rows if a[r] != expect[r]],
            "b_off": [r for r in rows if b[r] != expect[r]],
            "disagree": [r for r in rows if a[r] != b[r]]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("out_dir")
    s.add_argument("paths", nargs="+")
    s.add_argument("--wording", help="the wording file, to add each job's two added requests")
    g = sub.add_parser("agree")
    g.add_argument("key")
    g.add_argument("a")
    g.add_argument("b")
    args = ap.parse_args()
    if args.cmd == "sheet":
        n = sheet(args.out_dir, args.paths, args.wording)
        print(f"{n} rows: {args.out_dir}/sheet.csv (one copy per labeler), {args.out_dir}/key.csv (keep it away from them)")
        return
    r = agree(args.key, args.a, args.b)
    with open(args.key, newline="") as f:
        key = {int(x["row"]): x for x in csv.DictReader(f)}
    name = lambda row: f"{row} ({key[row]['job']} {key[row]['version']})"  # noqa: E731
    print(f"labelers agree on {pct(r['agree'], r['n'])} rows, Cohen's kappa {r['kappa']:.2f}")
    print(f"labeler A differs from the intended version on {len(r['a_off'])}/{r['n']}: {', '.join(map(name, r['a_off'])) or 'none'}")
    print(f"labeler B differs from the intended version on {len(r['b_off'])}/{r['n']}: {', '.join(map(name, r['b_off'])) or 'none'}")
    rewrite = sorted(set(r["a_off"]) | set(r["b_off"]))
    print(f"to reword or drop (either labeler off): {', '.join(map(name, rewrite)) or 'none'}")


if __name__ == "__main__":
    main()
