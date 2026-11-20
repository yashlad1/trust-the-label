# E1 · stage 2 "ask me first" rows: the call's own request plus one fixed sentence
import glob, json, os, tempfile, zipfile
from pathlib import Path
from trustlabel.harness.replay import ASK_FIRST
from trustlabel.harness.tasks import stage2

ROOT = Path(__file__).resolve().parents[2]
_fx = tempfile.TemporaryDirectory()
zipfile.ZipFile(ROOT / "tests/harness/fixtures/stage1.zip").extractall(_fx.name)
LOG = glob.glob(os.path.join(_fx.name, "**", "*.eval"), recursive=True)[0]
JOBS = ",".join(f"src/trustlabel/scenarios/{k}.json" for k in ("delete", "send", "pay", "publish"))
os.chdir(ROOT)


def dump(x):
    return json.dumps(x if isinstance(x, str) else [m.model_dump(exclude={"id"}) for m in x], default=str, sort_keys=True)


def key(s):
    c = s.metadata["call"]
    return c["episode"], c["position"]


base = list(stage2(LOG, JOBS).dataset)
on = list(stage2(LOG, JOBS, ask_first_rows=True).dataset)

# 1. off by default
assert not any(s.metadata["request"] == "own_ask_first" for s in base)

# 2. defaults unchanged, plus 2 new samples per stored first call
new = [s for s in on if s.metadata["request"] == "own_ask_first"]
rest = [s for s in on if s.metadata["request"] != "own_ask_first"]
assert len(rest) == len(base) and len(new) > 0
for a, b in zip(base, rest):
    assert (a.id, dump(a.input), a.metadata) == (b.id, dump(b.input), b.metadata), a.id
calls = {key(s) for s in base}
assert len(new) == 2 * len(calls), (len(new), len(calls))

for c in calls:
    pair = [s for s in new if key(s) == c]
    # 3. metadata
    assert sorted(s.metadata["label"] for s in pair) == ["false", "none"], c
    for s in pair:
        m = s.metadata
        assert (m["shown_name"], m["policy"], m["warning"], m["prompt"]) == ("vague", "gate_with_labels", False, "plain")
        # 4. shown is the call's own job with only request changed
        own = m["call"]["scenario"]
        want = dict(own, request=own["request"] + " " + ASK_FIRST)
        assert m["shown"] == want, c
        # 5. input equals the matching "own" sample's input, own request replaced
        ref = [r for r in base if key(r) == c and r.metadata["request"] == "own" and r.metadata["shown_name"] == "vague"
               and r.metadata["policy"] == "gate_with_labels" and r.metadata["label"] == m["label"]
               and r.metadata["warning"] is False and r.metadata["prompt"] == "plain"]
        assert len(ref) == 1, (c, len(ref))
        old = json.dumps(own["request"])[1:-1]
        assert old in dump(ref[0].input)
        assert dump(s.input) == dump(ref[0].input).replace(old, json.dumps(own["request"] + " " + ASK_FIRST)[1:-1]), c

# 6. unique ids
ids = [s.id for s in on]
assert len(ids) == len(set(ids))

print("checks passed")
