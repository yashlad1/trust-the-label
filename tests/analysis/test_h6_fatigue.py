from trustlabel.analysis.hypotheses import fatigue, flip_table, h6_report


def tables(out):
    """Every markdown table in out as (head cells, body rows)."""
    res, cur = [], []
    for ln in out.splitlines() + [""]:
        if ln.startswith("| ") or ln.startswith("|---"):
            cur.append(ln)
        elif cur:
            cells = [[c.strip() for c in l.strip("|").split("|")] for l in cur if not l.startswith("|---")]
            res.append((cells[0], cells[1:]))
            cur = []
    return res


def sources(out):
    return [l for l in out.splitlines() if l.startswith("Source:")]


def row(call, ask, name="vague", request="own", sv="unneeded", policy="gate_with_labels", label="none",
        warning=False, prompt="plain", kind="delete", unreadable=False, version=None, job=None):
    return dict(call=call, job=job or call, kind=kind, tool="t", answer="x", ask=ask, unreadable=unreadable,
                version=version or (sv if request == "own" else {"unneeded": "wanted", "wanted": "unneeded"}[sv]),
                name=name, request=request, stored_version=sv, policy=policy, label=label, warning=warning,
                prompt=prompt)


# ---- fatigue: 10 unneeded calls, 4 asked -> allowed 6
fr = [row(f"c{i}", i < 4) for i in range(10)]
fr += [row("w", True, sv="wanted"), row("s", True, request="swapped"),   # wrong version / request: not in u
       row("p", True, prompt="intent")]                                  # not a standard row
out = fatigue("G", [], fr, 0)
(head, body), = tables(out)
assert head[2:5] == ["approves 0% of asks", "approves 33% of asks", "approves 70% of asks"] and head[-1] == "n calls"
# 60%, (6 + 4/3)/10 = 73.3%, (6 + 2.8)/10 = 88%
assert body == [["vague", "labels: none, warning off", "60%", "73%", "88%", "10"],
                ["honest", "labels: none, warning off", "–", "–", "–", "0"]], body
assert sources(out)[0].endswith(", 0 failed samples (not in the table)")
assert "4 failed samples" in sources(fatigue("G", [], fr, 4))[0]

# ---- flip_table: label none, 10 calls: own/swapped ask (T,F)=2 (T,T)=3 (F,F)=4 (F,T)=1
pairs = [(True, False)] * 2 + [(True, True)] * 3 + [(False, False)] * 4 + [(False, True)]
qr = []
for i, (o, s) in enumerate(pairs):
    qr += [row(f"c{i}", o), row(f"c{i}", s, request="swapped")]
# gate on call: 4 calls, own asks on 3, swapped asks on none
for i in range(4):
    qr += [row(f"g{i}", i < 3, policy="gate_on_call", label=None), row(f"g{i}", False, request="swapped",
           policy="gate_on_call", label=None)]
out = flip_table("G", [], qr, 0)
(head, body), = tables(out)
assert body == [["gate on call, prompt plain", "4", "75% (3/4)", "0% (0/4)", "25% (1/4)", "0% (0/4)"],
                ["labels: none, warning off, prompt plain", "10", "20% (2/10)", "30% (3/10)", "40% (4/10)",
                 "10% (1/10)"]], body   # no row for labels false / true, no error
assert 2 + 3 + 4 + 1 == 10
assert sources(out)[0].endswith(", 0 failed samples (not in the table)") or "0 failed" in sources(out)[0]


# ---- h6_report
def build(combos, prompts, ask, unread=lambda *a: False):
    """combos: [(name, kind)]; 10 calls each; own/swapped x label none/false x prompts."""
    rs = []
    for name, kind in combos:
        for i in range(10):
            for request in ("own", "swapped"):
                for label in ("none", "false"):
                    for p in prompts:
                        rs.append(row(f"{name}-{kind}-{i}", ask(name, kind, request, label, p, i), name=name,
                                      request=request, label=label, prompt=p, kind=kind, job=f"j{i // 2}",
                                      unreadable=unread(label, p, i)))
    return rs


def ask_a(name, kind, request, label, p, i):
    if request != "own" or label != "none":
        return False
    return {("vague", "delete", "alignment"): i < 3, ("vague", "send", "alignment"): False,
            ("honest", "delete", "alignment"): i < 1, ("vague", "delete", "plain"): i < 5,
            ("vague", "send", "plain"): i < 2, ("honest", "delete", "plain"): True}[(name, kind, p)]


A = build([("vague", "delete"), ("vague", "send"), ("honest", "delete")], ("plain", "alignment"), ask_a,
          lambda label, p, i: label == "false" and i < (2 if p == "alignment" else 1))
out = h6_report("G", [], A, 0)
assert out.endswith("\n") and any(l.startswith("H6, pre-registered Nov 13") for l in out.splitlines())
t1, t2 = tables(out)
assert t1[1] == [["vague", "delete", "30% (3/10)", "50% (5/10)", "no"],
                 ["vague", "send", "0% (0/10)", "20% (2/10)", "yes"],
                 ["vague", "all kinds", "15% (3/20)", "35% (7/20)", "no"],   # 10*3 > 20
                 ["honest", "delete", "10% (1/10)", "100% (10/10)", "yes"],  # 10*1 <= 10
                 ["honest", "all kinds", "10% (1/10)", "100% (10/10)", "yes"]], t1[1]
assert len(t2[1][0]) == 8
labs = [r[:2] for r in t2[1]]
assert labs == [["vague", "H6b request effect (own vs swapped, no label)"],
                ["vague", "H6c label effect (no label vs false label, own request)"],
                ["honest", "H6b request effect (own vs swapped, no label)"],
                ["honest", "H6c label effect (no label vs false label, own request)"],
                ["all", "unreadable replies, prompt plain"], ["all", "unreadable replies, prompt alignment"]], labs
# vague alignment, 20 calls: own+none asks 3, swapped none 0; false label never asks
assert t2[1][0][2:4] == ["15% (3/20)", "0% (0/20)"] and t2[1][0][4] == "+15.0" and t2[1][0][-1] == "no"
assert t2[1][1][2:4] == ["15% (3/20)", "0% (0/20)"] and t2[1][1][-1] == "–"
# unreadable: label false, i<1 on plain -> 6 of 120; i<2 on alignment -> 12 of 120
assert t2[1][4] == ["all", "unreadable replies, prompt plain", "5% (6/120)"] + ["–"] * 5, t2[1][4]
assert t2[1][5] == ["all", "unreadable replies, prompt alignment", "10% (12/120)"] + ["–"] * 5, t2[1][5]
assert all("5 failed samples" in s for s in sources(h6_report("G", [], A, 5))) and len(sources(out)) >= 2

# rows with request wording_x or prompt intent change nothing
extra = [dict(r, prompt="intent", ask=not r["ask"]) for r in A[:100]]
extra += [dict(r, request="wording_x", ask=not r["ask"]) for r in A[100:200]]
assert h6_report("G", [], A + extra, 0) == out

# alignment only, delete only: no error, no plain column, no plain unreadable row
D = build([("vague", "delete"), ("honest", "delete")], ("alignment",), ask_a)
t1, t2 = tables(h6_report("G", [], D, 0))
assert [r[:2] for r in t1[1]] == [["vague", "delete"], ["vague", "all kinds"], ["honest", "delete"],
                                  ["honest", "all kinds"]]
assert all(r[3] == "–" for r in t1[1])
assert [r[1] for r in t2[1]][-1] == "unreadable replies, prompt alignment"
assert not any("prompt plain" in r[1] for r in t2[1])

# H6b yes: vague delete asks on every own call, never on swapped; label false never asks
Y = build([("vague", "delete")], ("alignment",), lambda n, k, rq, lb, p, i: rq == "own" and lb == "none")
t2 = tables(h6_report("G", [], Y, 0))[1][1]
# b=10, c=0: p = 2/2**10 = 0.002; difference +100, CI [+100, +100]
assert t2[0] == ["vague", "H6b request effect (own vs swapped, no label)", "100% (10/10)", "0% (0/10)", "+100.0",
                 "0.002", "[+100.0, +100.0]", "yes"], t2[0]
assert t2[1][2:4] == ["100% (10/10)", "0% (0/10)"] and t2[1][-1] == "–"   # label none asks: not floored

# H6c floor: nothing asks anywhere -> 10*ka < n
Q = build([("vague", "delete")], ("alignment",), lambda *a: False)
t2 = tables(h6_report("G", [], Q, 0))[1][1]
assert t2[0][-1] == "no" and t2[1][-1] == "floor: cannot read", t2[1]
print("ok")
