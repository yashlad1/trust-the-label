# G · dev/pipeline.py dry run writes a manifest with mode, command, code, models, stage3_agent, smokes, spend
import glob, json, os, re, subprocess, sys, tempfile, zipfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = os.environ.get("PIPELINE", "dev/pipeline.py")
_fx = tempfile.TemporaryDirectory()
zipfile.ZipFile(ROOT / "tests/harness/fixtures/stage1.zip").extractall(_fx.name)
SRC = glob.glob(os.path.join(_fx.name, "**", "*.eval"), recursive=True)[0]
JOBS = ",".join(f"src/trustlabel/scenarios/{k}.json" for k in ("delete", "send", "pay", "publish"))
IDS = {"gptoss": "openrouter/openai/gpt-oss-120b", "glm": "openrouter/z-ai/glm-5.3-flash",
       "luna": "openrouter/openai/gpt-6-luna"}

with tempfile.TemporaryDirectory() as tmp:
    out = os.path.join(tmp, "out")
    WORDING = "src/trustlabel/scenarios/wording.json"
    cmd = [sys.executable, PIPELINE, "dry", out, "--wording", WORDING,
           "--stage1-logs", SRC, "--jobs", JOBS, "--epochs", "1", "--no-stage2"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=ROOT)
    assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]
    m = json.load(open(os.path.join(out, "manifest.json")))

    for k in ("stage1", "stage2", "stage3", "live_gate", "jobs", "wording", "epochs",
              "stage2_skipped", "stage3_skipped", "stage1_reused"):
        assert k in m, f"missing old key {k}"
    for k in ("mode", "command", "code", "models", "stage3_agent", "stage1_unneeded", "smokes", "spend", "stop_at"):
        assert k in m, f"missing new key {k}"

    assert m["mode"] == "dry"
    assert isinstance(m["command"], list) and all(isinstance(c, str) for c in m["command"])
    assert "dry" in m["command"] and out in m["command"], m["command"]

    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    assert re.fullmatch(r"[0-9a-f]{40}", m["code"]["git_sha"]) and m["code"]["git_sha"] == sha
    assert isinstance(m["code"]["dirty"], bool)

    for key, mid in IDS.items():
        e = m["models"][key]
        assert e["model"] == mid, e
        assert e["config"].startswith("dev/models/") or "/dev/models/" in e["config"], e["config"]
        cfg = e["config"] if os.path.isabs(e["config"]) else os.path.join(os.getcwd(), e["config"])
        assert e["provider"] == yaml.safe_load(open(cfg)), e
        assert "effort" in e
        assert isinstance(e["connections"], int) and not isinstance(e["connections"], bool)

    u = m["stage1_unneeded"]
    assert set(u) == {"gptoss", "glm"} and all(type(v) is int for v in u.values()), u
    assert m["stage3_agent"] in ("gptoss", "glm")
    assert u[m["stage3_agent"]] == max(u.values())
    other = "glm" if m["stage3_agent"] == "gptoss" else "gptoss"
    assert u[m["stage3_agent"]] >= u[other]

    assert isinstance(m["smokes"], dict) and len(m["smokes"]) >= 1
    for step, path in m["smokes"].items():
        assert os.path.exists(path), (step, path)

    for k in ("spend", "stop_at"):
        assert isinstance(m[k], (int, float)) and not isinstance(m[k], bool), k
    assert m["spend"] == 0

    assert m["jobs"] == JOBS and m["wording"] == WORDING
    assert m["stage1"] == SRC.split(","), m["stage1"]

print("checks passed")
