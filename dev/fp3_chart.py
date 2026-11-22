# FP3 pilot headline chart (Figure 3) from the final-run records: uv run --with matplotlib python dev/fp3_chart.py
import glob
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from trustlabel.analysis.rates import compare, paired, stage2_rows

FIXED = {"name": "vague", "request": "own", "prompt": "plain", "policy": "gate_with_labels", "warning": False,
         "stored_version": "unneeded"}
GATES = [("luna", "GPT-6 Luna"), ("nemotron35", "Nemotron 3.5 Super VL")]

manifests = [json.load(open(f)) for f in sorted(glob.glob("records/fp3-pilot-final/final-*/manifest.json"))]
results = []
for gate, shown in GATES:
    paths = [m["stage2"][gate] for m in manifests if gate in m["stage2"]]
    rows, _failed = stage2_rows(paths)
    x = compare(paired(rows, FIXED, {"label": "none"}, {"label": "false"}))
    results.append((shown, x["n"] - x["ka"], x["n"] - x["kb"], x["n"], x["d"], x["lo"], x["hi"]))
    print(f"{shown}: let through {x['n'] - x['ka']}/{x['n']} no label, {x['n'] - x['kb']}/{x['n']} false label, "
          f"d {x['d']:+.1f} [{x['lo']:+.1f}, {x['hi']:+.1f}]")
ns = {r[3] for r in results}
assert len(ns) == 1, ns
n_all = ns.pop()
(_, a, b, _, *_), (_, c, d, _, _, lo, _) = results
caption = (f"**Figure 3.** How often each gate let an unneeded action through in the pilot, with no label (blue) and with a "
           f"false read-only label (orange). Each row is the same {n_all} saved actions, shown to the gate under the tool's vague "
           f"name, with the user's own request and no warning. The longer the line, the more the false label changed the gate's "
           f"decisions: GPT-6 Luna let {a} of {n_all} through with no label and {b} of {n_all} with the false label, and Nemotron 3.5 "
           f"Super VL let {c} and {d} through. The numbers on the right are the difference in percentage points, with a 90% "
           f"interval from resampling jobs" + ("; Nemotron's interval reaches 0" if lo <= 0 else "") +
           f". With {n_all} actions per gate, this is a pilot check, not a test of the hypotheses.")
print(caption)
open("docs/figures/fp3-pilot-headline.md", "w").write("![Figure 3](fp3-pilot-headline.png)\n\n" + caption + "\n")

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
fig, ax = plt.subplots(figsize=(8.6, 2.6), dpi=200)
fig.patch.set_facecolor(SURF)
ax.set_facecolor(SURF)
n = len(results)
for i, (lab, a, b, tot, eff, lo, hi) in enumerate(results):
    y = n - 1 - i
    pa, pb = 100 * a / tot, 100 * b / tot
    ax.plot([pa, pb], [y, y], color="#c9c8c2", lw=2.4, zorder=1, solid_capstyle="round")
    ax.scatter([pa], [y], s=70, color=BLUE, zorder=3, edgecolor=SURF, linewidth=1.6)
    ax.scatter([pb], [y], s=70, color=ORANGE, zorder=3, edgecolor=SURF, linewidth=1.6)
    ax.text(104, y, f"{eff:+.1f}", va="center", ha="left", fontsize=9, color=INK, weight="bold")
    ax.text(118, y, f"[{lo:+.1f}, {hi:+.1f}]", va="center", ha="left", fontsize=8.5, color=INK2)
top = n - 1
a0, b0, t0 = results[0][1], results[0][2], results[0][3]
ax.annotate("No label", (100 * a0 / t0, top), xytext=(0, 11), textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.annotate("False read-only label", (100 * b0 / t0, top), xytext=(-8, 11), textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.text(104, n - 0.35, "Effect", fontsize=8.5, color=INK2, ha="left")
ax.text(118, n - 0.35, "90% interval", fontsize=8.5, color=INK2, ha="left")
ax.set_yticks(range(n))
ax.set_yticklabels([r[0] for r in results][::-1], fontsize=9, color=INK)
ax.set_xlim(0, 100)
ax.set_ylim(-0.6, n - 0.1)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8.5, color=INK2)
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
ax.set_xlabel(f"Share of the {n_all} unneeded actions the gate let through", fontsize=9, color=INK2, labelpad=6)
fig.suptitle("Both gates let more unneeded actions through with a false read-only label", x=0.012, ha="left",
             fontsize=11.5, color=INK, weight="bold")
fig.subplots_adjust(left=0.27, right=0.70, top=0.84, bottom=0.20)
fig.savefig("docs/figures/fp3-pilot-headline.png", facecolor=SURF)
fig.savefig("docs/figures/fp3-pilot-headline.svg", facecolor=SURF)
