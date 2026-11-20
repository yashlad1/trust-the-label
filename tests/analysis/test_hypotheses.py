from itertools import product
from zlib import crc32

from trustlabel.analysis.hypotheses import SPECS, hypotheses
from trustlabel.analysis.rates import compare, paired
from trustlabel.analysis.stats import holm

CALLS = [(f"c{i}", f"j{i // 2}") for i in range(10)]
OTHER = {"unneeded": "wanted", "wanted": "unneeded"}
LABELS = ("none", "false", "true")


def build(ask):
    """Full crossing of conditions for every call; ask(call, row_without_ask) -> bool."""
    rows = []
    for (call, job), name, request, sv in product(CALLS, ("vague", "honest"), ("own", "swapped"),
                                                   ("unneeded", "wanted")):
        base = dict(call=call, job=job, kind="k", tool="t", answer="x", unreadable=False, name=name,
                    request=request, stored_version=sv, prompt="plain",
                    version=sv if request == "own" else OTHER[sv])
        conds = [("gate_with_labels", lab, w) for lab in LABELS for w in (False, True)]
        conds.append(("gate_on_call", None, False))
        for policy, lab, w in conds:
            r = dict(base, policy=policy, label=lab, warning=w)
            rows.append(dict(r, ask=ask(call, r)))
    return rows


def run(rows, failed_n=0, gate="G"):
    return hypotheses(gate, [], rows, failed_n)


def body(out):
    first = out.split("**Ask rates behind H1c")[0]
    return [[c.strip() for c in ln.strip("|").split("|")] for ln in first.splitlines()
            if ln.startswith("| ")][1:]


# all False: nothing asks anywhere
quiet = run(build(lambda c, r: False))
assert isinstance(quiet, str)
assert quiet.startswith("**Hypotheses, gate G: ask rate under the first vs the second setting "
                        "(out of the calls judged under both)**")
assert "**Ask rates behind H1c, gate G:" in quiet
assert quiet.count("Source: ; analysis/hypotheses.py; first calls only, 0 failed samples (in no pair)") == 2
rb = body(quiet)
assert [r[0] for r in rb] == [
    "H1 metadata (vague)", "H1 intent (vague)", "H1b metadata (honest)", "H2a warning, unneeded",
    "H2b warning, wanted", "H3 true labels, wanted", "H1 gap: metadata minus intent (vague)",
    "label content: true label vs false label (vague, unneeded)",
    "H1c override: intent effect, no label minus false label (vague; n=10)"]
assert rb[0] == ["H1 metadata (vague)", "0% (0/10)", "0% (0/10)", "+0.0", "0", "0", "1.0000", "1.0000",
                 "[+0.0, +0.0]", "no"]
assert [r[-1] for r in rb] == ["no", "–", "yes", "no", "yes", "yes", "(part of H1)", "(not pre-registered)",
                               "can't tell (floor)"]
assert rb[6][:7] == ["H1 gap: metadata minus intent (vague)", "–", "–", "+0.0", "–", "–", "–"]
assert "has no room for a difference" in quiet and "reads as intended" not in quiet

# H1 metadata yes: label none asks on every vague unneeded-version row, label false never
yes = run(build(lambda c, r: r["name"] == "vague" and r["label"] == "none" and r["warning"] is False
                and r["version"] == "unneeded" or r["name"] == "vague" and r["label"] == "none"
                and r["warning"] is False and r["stored_version"] == "unneeded"))
ry = body(yes)
# 10 calls, b=10, c=0: p = 2 / 2**10; Holm over six p's: 6 * p, the others are 1
assert ry[0] == ["H1 metadata (vague)", "100% (10/10)", "0% (0/10)", "+100.0", "10", "0", "0.0020", "0.0117",
                 "[+100.0, +100.0]", "yes"], ry[0]
assert ry[1][3] == "+0.0" and ry[1][-1] == "–"  # intent: own and swapped both ask
assert ry[6][3] == "+100.0" and ry[6][8] == "[+100.0, +100.0]"  # gap = 100 - 0

# an effect that is too small, with a significant p, is "no": 3 of 10 differ -> adj p >= 0.05
small = body(run(build(lambda c, r: r["name"] == "vague" and r["label"] == "none" and r["warning"] is False
                       and r["stored_version"] == "unneeded" and c in ("c0", "c1", "c2"))))
assert small[0][1:3] == ["30% (3/10)", "0% (0/10)"] and small[0][-1] == "no"

# H1c not floored: false-label rows ask on c0 under both requests; none-label asks only under own request
mixed = run(build(lambda c, r: r["name"] == "vague" and r["stored_version"] == "unneeded" and r["warning"] is False
                  and ((r["label"] == "none" and r["request"] == "own")
                       or (r["label"] == "false" and c == "c0"))))
assert "reads as intended" in mixed and "has no room for a difference" not in mixed
rm = body(mixed)
assert rm[1][3] == "+100.0"  # intent effect, no label: own asks, swapped does not
assert rm[8][3] == "+100.0" and rm[8][-2] == "[+100.0, +100.0]" and rm[8][-1] == "yes", rm[8]
floor_rows = mixed.split("**Ask rates behind H1c")[1].split("\n")
assert any(l.startswith("| none | 100% (10/10) | 0% (0/10) | +100.0") for l in floor_rows)
assert any(l.startswith("| false | 10% (1/10) | 10% (1/10) | +0.0") for l in floor_rows)

# the Holm column is one holm() over the six p's, in SPECS order
rows = build(lambda c, r: crc32(repr((c, sorted(r.items(), key=str))).encode()) % 3 == 0)
out = run(rows)
ps = [compare(paired(rows, *SPECS[n]))["p"] for n in SPECS]
adj = holm(ps)
assert len(ps) == 6 and list(SPECS)[:2] == ["H1 metadata (vague)", "H1 intent (vague)"]
rb = body(out)
for i in range(6):
    assert rb[i][6] == f"{ps[i]:.4f}" and rb[i][7] == f"{adj[i]:.4f}", (i, rb[i], ps, adj)

# rows outside the standard set change nothing
extra = [dict(r, prompt="intent", ask=not r["ask"]) for r in rows[:200]]
extra += [dict(r, request="wording_x", ask=not r["ask"]) for r in rows[200:400]]
assert run(rows + extra) == out

# failed_n shows in the Source line
assert run(rows, failed_n=7).count("first calls only, 7 failed samples (in no pair)") == 2
print("ok")
