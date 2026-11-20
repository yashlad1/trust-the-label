from trustlabel.analysis.rates import KEY_FIELDS, Pair, compare, paired, pick
from trustlabel.analysis.stats import mcnemar_p

BASE = dict(name="n1", request="r1", stored_version="v1", policy="p1", label="true", warning="w0", prompt="x")


def row(call, ask, job="j1", **over):
    return dict(BASE, call=call, job=job, ask=ask, **over)


# pick
rows = [row("c1", True), row("c2", False, label="lies"), row("c3", True, label="lies")]
assert [r["call"] for r in pick(rows, {"label": "lies"})] == ["c2", "c3"]
assert [r["call"] for r in pick(rows, {"label": "lies", "ask": True})] == ["c3"]
try:
    pick(rows, {"label": "none"})
    raise SystemExit("pick should raise ValueError")
except ValueError:
    pass
assert pick([], {"label": "none"}) == []

# paired: c3 only under a, c4 only under b
T, L = {"label": "true"}, {"label": "lies"}
rows = [
    row("c2", True), row("c1", False), row("c3", True),
    row("c1", True, label="lies"), row("c2", True, label="lies"), row("c4", False, label="lies"),
    row("c1", True, policy="p2"),  # other fixed value, ignored
]
out = paired(rows, {"policy": "p1"}, T, L)
assert [p.call for p in out] == ["c1", "c2"]
assert [(p.a, p.b) for p in out] == [(False, True), (True, True)]
call, job, a, b = out[0]
assert (call, job, a, b) == ("c1", "j1", False, True)
p = out[1]
assert (p.call, p.job, p.a, p.b) == ("c2", "j1", True, True)

# a field not named in a/b must also match: prompt differs -> no pair
rows = [row("c1", True, prompt="x"), row("c1", False, label="lies", prompt="y"),
        row("c2", True, prompt="x"), row("c2", False, label="lies", prompt="x")]
out = paired(rows, {"policy": "p1"}, T, L)
assert [p.call for p in out] == ["c2"]

# ambiguous duplicates
rows = [row("c1", True), row("c1", False), row("c1", True, label="lies")]
try:
    paired(rows, {"policy": "p1"}, T, L)
    raise SystemExit("paired should raise AssertionError")
except AssertionError:
    pass

assert "call" not in KEY_FIELDS and len(KEY_FIELDS) == 7

# compare, by hand: 8 pairs (a, b)
data = [(True, False), (True, False), (True, True), (False, True),
        (False, False), (True, False), (False, False), (True, True)]
pairs = [Pair("c%d" % i, "j%d" % (i % 3), a, b) for i, (a, b) in enumerate(data)]
r = compare(pairs)
assert (r["n"], r["ka"], r["kb"], r["b"], r["c"]) == (8, 5, 3, 3, 1), r
assert r["d"] == 25.0  # 100 * (3 - 1) / 8
assert r["p"] == mcnemar_p(3, 1)
assert -100 <= r["lo"] <= r["hi"] <= 100

r = compare([])
assert r["n"] == 0 and r["d"] == 0.0

print("ok")
