from itertools import product

from trustlabel.analysis.hypotheses import intent_report, wording_report

CALLS = [(f"c{i}", f"j{i // 2}") for i in range(10)]
OTHER = {"unneeded": "wanted", "wanted": "unneeded"}


def row(call, job, request, sv, version, prompt, label, ask):
    return dict(call=call, job=job, kind="k", tool="t", answer="x", unreadable=False, name="vague",
                request=request, stored_version=sv, version=version, prompt=prompt, label=label,
                policy="gate_with_labels", warning=False, ask=ask)


def build_intent(ask):
    """ask(call, row_without_ask) -> bool over the full crossing of the intent-report conditions."""
    rows = []
    for (c, j), req, sv, prompt, lab in product(CALLS, ("own", "swapped"), ("unneeded", "wanted"),
                                                ("plain", "intent"), ("none", "false")):
        r = row(c, j, req, sv, sv if req == "own" else OTHER[sv], prompt, lab, False)
        rows.append(dict(r, ask=ask(c, r)))
    return rows


def distract(rows):
    """Rows the intent report must ignore: a wording request and the alignment prompt, all asking."""
    extra = []
    for (c, j), prompt, lab in product(CALLS, ("plain", "intent"), ("none", "false")):
        extra.append(row(c, j, "wording_x", "wanted", "wanted", prompt, lab, True))
    for (c, j), lab in product(CALLS, ("none", "false")):
        extra.append(row(c, j, "own", "unneeded", "unneeded", "alignment", lab, True))
    return rows + extra


def body(out):
    return [[c.strip() for c in ln.strip("|").split("|")] for ln in out.splitlines() if ln.startswith("| ")][1:]


INTENT_LABELS = [
    "label effect, plain prompt (no label vs false label)",
    "label effect, intent sentence (no label vs false label)",
    "intent effect, plain prompt (own vs wanted request)",
    "H4a intent effect, intent sentence (own vs wanted request)",
    "asks on wanted calls: intent sentence vs plain (no label)",
    "H4b label effect shrinks: plain minus intent sentence (per call; n=10)"]

# case A: with no label, the intent prompt asks on own requests only
A_rows = build_intent(lambda c, r: r["label"] == "none" and r["prompt"] == "intent" and r["request"] == "own"
                      and r["stored_version"] == "unneeded")
A = intent_report("G", [], A_rows, 7)
assert A.startswith("**Intent sentence, gate G:")
assert A.count(", 7 failed samples (in no pair)") == 1 and A.rstrip().endswith(", 7 failed samples (in no pair)")
ra = body(A)
assert [r[0] for r in ra] == INTENT_LABELS, [r[0] for r in ra]
assert ra[3] == [INTENT_LABELS[3], "100% (10/10)", "0% (0/10)", "+100.0", "0.0020", "[+100.0, +100.0]", "yes"], ra[3]
assert ra[1][1:3] == ["100% (10/10)", "0% (0/10)"] and ra[1][-1] == "–"  # label effect, intent sentence
assert ra[0][1:4] == ["0% (0/10)", "0% (0/10)", "+0.0"] and ra[0][-1] == "–"
assert ra[2][-1] == "–" and ra[4][-1] == "–" and ra[4][1] == "0% (0/20)"
# plain 0 - intent 1 per call: the label effect grew, so the shrink is -100
assert ra[5][1:3] == ["–", "–"] and ra[5][3] == "-100.0" and ra[5][4] == "–" and ra[5][-1] == "no", ra[5]
# rows the report must ignore leave it unchanged
assert intent_report("G", [], distract(A_rows), 7) == A

# case B: only the plain prompt shows a label effect, the intent sentence shows none
B_rows = build_intent(lambda c, r: r["label"] == "none" and r["prompt"] == "plain" and r["request"] == "own"
                      and r["stored_version"] == "unneeded")
rb = body(intent_report("G", [], B_rows, 0))
assert rb[3][1:3] == ["0% (0/10)", "0% (0/10)"] and rb[3][-1] == "no"
assert rb[5][3] == "+100.0" and rb[5][5] == "[+100.0, +100.0]" and rb[5][-1] == "yes", rb[5]
assert rb[5][0].endswith("(per call; n=10)")

# case C: plain none-label asks on 5 calls, intent none-label on all 10: shrink = (5*0 + 5*-1)/10 = -50
C_rows = build_intent(lambda c, r: r["label"] == "none" and r["request"] == "own" and r["stored_version"] == "unneeded"
                      and (r["prompt"] == "intent" or c in ("c0", "c1", "c2", "c3", "c4")))
rc = body(intent_report("G", [], C_rows, 0))
assert rc[5][3] == "-50.0" and rc[5][-1] == "no", rc[5]


def build_wording(ask):
    rows = []
    for (c, j), req, lab in product(CALLS, ("unneeded_calm", "unneeded_loud", "wanted_calm", "wanted_loud",
                                            "own", "swapped"), ("none", "false")):
        r = row(c, j, req, "unneeded", "unneeded", "plain", lab, False)
        rows.append(dict(r, ask=ask(c, r)))
    return rows


WORD_LABELS = [
    "H5a intent, calm wording (unneeded vs wanted), no label",
    "H5b high-stakes words, unneeded (loud vs calm), no label",
    "intent, loud wording (unneeded vs wanted), no label",
    "high-stakes words, wanted (loud vs calm), no label",
    "intent, calm wording (unneeded vs wanted), false label"]

# calm unneeded asks (no label); everything else, including every plain own/swapped row's asks, is checked apart
W_rows = build_wording(lambda c, r: r["label"] == "none" and r["request"] == "unneeded_calm")
W = wording_report("G", [], W_rows, 3)
assert W.startswith("**Wording, gate G:")
assert W.count(", 3 failed samples (in no pair)") == 1 and W.rstrip().endswith(", 3 failed samples (in no pair)")
rw = body(W)
assert [r[0] for r in rw] == WORD_LABELS, [r[0] for r in rw]
assert rw[0] == [WORD_LABELS[0], "100% (10/10)", "0% (0/10)", "+100.0", "0.0020", "[+100.0, +100.0]", "yes"], rw[0]
assert rw[1][1:4] == ["0% (0/10)", "100% (10/10)", "-100.0"] and rw[1][-1] == "no"
assert [r[-1] for r in rw[2:]] == ["–", "–", "–"]
# plain own/swapped rows do not change the wording report
assert wording_report("G", [], build_wording(lambda c, r: (r["label"] == "none" and r["request"] == "unneeded_calm")
                                             or r["request"] in ("own", "swapped")), 3) == W
# nothing asks: H5a is "no"
assert body(wording_report("G", [], build_wording(lambda c, r: False), 0))[0][-1] == "no"
print("ok")
