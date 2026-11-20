"""dev/report.py prints a runs table, then Stage 1/2/3 tables for manifests."""
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

from trustlabel.analysis.rates import stage2_rows

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(os.environ.get("REPORT", ROOT / "dev" / "report.py")).resolve()


def run(args, cwd):
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    return subprocess.run(
        ["uv", "run", "--project", str(ROOT), "python", str(REPORT), *args],
        cwd=cwd, capture_output=True, text=True, env=env)


with tempfile.TemporaryDirectory() as tmp:
    # manifest paths start with sample_records/dry_run/, so unzip into tmp/sample_records
    with zipfile.ZipFile(ROOT / "sample_records" / "dry_run_fake_model.zip") as z:
        z.extractall(Path(tmp) / "sample_records")
    manifest = Path(tmp) / "sample_records" / "dry_run" / "manifest.json"
    m = json.loads(manifest.read_text())

    r = run([str(manifest)], tmp)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "## Runs" in out and "## Stage 2" in out, out
    assert out.index("## Runs") < out.index("## Stage 2")
    if m.get("stage1"):
        assert out.count("Stage 1: how often each agent proposed an irreversible call (out of its episodes)") == 1
    for gate in m["stage2"]:
        t = f"Stage 2, gate {gate}: what the gate did with each call (out of the calls in that cell)"
        ref = f"Reference lines, gate {gate}: allowed rate on unneeded calls, vague name, own request (computed, not run)"
        assert out.count(t) == 1, (gate, out)
        assert out.count(ref) == 1, (gate, out)
        rows, _ = stage2_rows([Path(tmp) / m["stage2"][gate]])
        prompts = {x["prompt"] for x in rows}
        reqs = {x["request"] for x in rows}
        want = {}  # title prefix -> printed once (1) or not at all (0)
        std = any(x["request"] in ("own", "swapped") and x["prompt"] == "plain" for x in rows)
        for name in ("Hypotheses", "Ask rates behind H1c", "Fatigued user", "Paired request swap"):
            want[f"{name}, gate {gate}: "] = int(std)
        want[f"Intent sentence, gate {gate}: "] = int("intent" in prompts)
        for name in ("H6 AlignmentCheck", "H6 effects"):
            want[f"{name}, gate {gate}: "] = int("alignment" in prompts)
        want[f"Wording, gate {gate}: "] = int(any(q.endswith(("_calm", "_loud")) for q in reqs))
        has = lambda lab: any(x["label"] == lab and x["policy"] == "gate_with_labels" and x["name"] == "vague"
                              and x["version"] == "unneeded" and x["request"] == "own" and x["warning"] is False
                              for x in rows)
        plain = "plain" in prompts
        rob = int(plain and has("none") and has("false"))
        want[f"Robustness, gate {gate}: "] = rob
        want[f"Contrast, gate {gate}: "] = rob
        want[f"AlignmentCheck only, gate {gate}: "] = int(not plain and "alignment" in prompts)
        for prefix, n in want.items():
            if prefix.startswith("Fatigued user"):  # title text after the name may change
                hits = [i for i, ln in enumerate(out.splitlines()) if ln.startswith("**Fatigued user") and f"gate {gate}: " in ln]
                assert len(hits) == n, (prefix, n, out)
                continue
            assert out.count(f"**{prefix}") == n, (prefix, n, out)
            if n:
                assert out.index("## Stage 2") < out.index(f"**{prefix}"), prefix
                if "## Stage 3" in out:
                    assert out.index(f"**{prefix}") < out.index("## Stage 3"), prefix
    if m.get("stage3"):
        assert out.count("Stage 3: the live loop, per policy (out of episodes)") == 1
    live = bool(m.get("live_gate") in m["stage2"] and m.get("stage3"))
    assert out.count("## Live versus replay") == int(live), out
    assert out.count("**Live versus replay: ") == int(live), out
    if live and "## Stage 3" in out:
        assert out.index("## Stage 3") < out.index("## Live versus replay")

    for code in ("(D11)", "(D15)", "probe2", "pilot B2", "probe3", "P of S", "in C1 "):
        assert code not in out, code

    # piece: live gate named but absent from stage2
    if m.get("stage3"):
        m2 = dict(m, live_gate="nonexistent")
        mf = manifest.with_name("manifest_nolive.json")
        mf.write_text(json.dumps(m2))
        r = run([str(mf)], tmp)
        assert r.returncode == 0, r.stderr
        assert "## Live versus replay" in r.stdout, r.stdout
        assert "(live gate nonexistent has no stage-2 logs in these manifests)" in r.stdout, r.stdout

    # safe(): ValueError becomes a note, anything else propagates
    import importlib.util
    spec = importlib.util.spec_from_file_location("report_mod", REPORT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def good(gate, paths, rows, failed_n):
        return ("ok", gate, paths, rows, failed_n)

    def bad(gate, paths, rows, failed_n):
        raise ValueError("no such rows")

    def worse(gate, paths, rows, failed_n):
        raise KeyError("x")

    assert mod.safe(good, "g", [1], [2], 3) == ("ok", "g", [1], [2], 3)
    assert mod.safe(bad, "g", [], [], 0) == "**bad, gate g: not in these logs (no such rows)**\n"
    try:
        mod.safe(worse, "g", [], [], 0)
        raise SystemExit("KeyError was swallowed")
    except KeyError:
        pass

    ev = sorted((Path(tmp) / "sample_records" / "dry_run").glob("stage1-glm/*.eval"))[0]
    r = run([str(ev)], tmp)
    assert r.returncode == 0, r.stderr
    assert "## Runs" in r.stdout and "## Stage 2" not in r.stdout, r.stdout

print("checks passed")
