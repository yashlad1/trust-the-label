"""Check that the study's 5 OpenRouter models are reachable and harness-compatible.

Run: dev/py.sh python dev/check_openrouter.py [flags]

1. (no flags, FREE, no key)  public endpoints JSON per model: pinned provider endpoint exists,
   supports tools (+ reasoning where we send effort), context, price. Exit 1 on any failure.
2. --key       (FREE, needs OPENROUTER_API_KEY)  prints usage/limit from /api/v1/key.
3. --ping --yes  *** PAID *** (cents) one real generate() call per model with a ping tool, sent exactly like
   the runs (provider pin, temperature 1.0, reasoning effort, no max_tokens).
   Without --yes it only prints what it would do. --only <name> limits to one model.
"""
import argparse
import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

# name -> (OpenRouter id, yaml file, we send reasoning effort "medium")
MODELS = {
    "glm-5.3-flash": ("z-ai/glm-5.3-flash", "glm-5.3-flash.yaml", True),
    "qwen3.8-flash": ("qwen/qwen3.8-flash", "qwen3.8-flash.yaml", False),
    "gpt-6-luna": ("openai/gpt-6-luna", "gpt-6-luna.yaml", True),
    "haiku": ("anthropic/claude-haiku-5.5", "haiku.yaml", True),
    "gpt-oss-120b": ("openai/gpt-oss-120b", "gpt-oss-120b.yaml", True),
}
MODELS_DIR = Path(__file__).parent / "models"
API = "https://openrouter.ai/api/v1"


def load_cfg(fname):
    return yaml.safe_load((MODELS_DIR / fname).read_text())


def get_json(url, key=None):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"} if key else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pick_endpoint(endpoints, pin):
    # pin is the YAML provider.order[0], matched against each endpoint's "tag" (e.g. "deepinfra/bf16",
    # "z-ai/fp8", "openai"). Exact tag wins; else the first tag under that provider prefix.
    exact = [e for e in endpoints if e["tag"] == pin]
    return (exact or [e for e in endpoints if e["tag"].startswith(pin + "/")] or [None])[0]


def free_check():
    print(f"OPENROUTER_API_KEY: {'set' if os.environ.get('OPENROUTER_API_KEY') else 'missing'}\n")
    print("| model | found | pinned endpoint | tools | reasoning | context | $/1M in | $/1M out | uptime 30m |")
    print("|---|---|---|---|---|---|---|---|---|")
    bad = []
    for name, (mid, fname, effort) in MODELS.items():
        cfg = load_cfg(fname)
        pin = cfg["provider"]["order"][0]
        try:
            eps = get_json(f"{API}/models/{mid}/endpoints")["data"]["endpoints"]
        except Exception as e:
            print(f"| {name} | no ({e}) | | | | | | | |")
            bad.append(f"{name}: model not found / unreachable")
            continue
        ep = pick_endpoint(eps, pin)
        if ep is None:
            print(f"| {name} | yes | {pin}: NOT FOUND | | | | | | |")
            bad.append(f"{name}: no endpoint with tag {pin}")
            continue
        sp = ep["supported_parameters"]
        tools = "tools" in sp
        reasoning = "reasoning" in sp  # JSON also lists "reasoning_effort"; qwen has reasoning but no effort
        if not tools:
            bad.append(f"{name}: endpoint {ep['tag']} lacks tools")
        if effort and not (reasoning and "reasoning_effort" in sp):
            bad.append(f"{name}: endpoint {ep['tag']} lacks reasoning/reasoning_effort")
        if cfg.get("reasoning_enabled") and not reasoning:
            bad.append(f"{name}: endpoint {ep['tag']} lacks reasoning (yaml sets reasoning_enabled)")
        p = ep["pricing"]
        per_m = lambda k: f"{float(p[k]) * 1e6:.3f}" if p.get(k) else "?"
        up = ep.get("uptime_last_30m")
        print(f"| {name} | yes | {ep['tag']} | {'yes' if tools else 'NO'} | "
              f"{'yes' if reasoning else 'NO'}{' (effort sent)' if effort else ' (none sent)'} | "
              f"{ep['context_length']} | {per_m('prompt')} | {per_m('completion')} | {up} |")
    print("\nFAIL:\n  " + "\n  ".join(bad) if bad else "\nall checks passed")
    return 1 if bad else 0


def key_check():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        print("OPENROUTER_API_KEY missing")
        return 1
    d = get_json(f"{API}/key", key)["data"]
    print({k: d.get(k) for k in ("usage", "limit", "limit_remaining", "is_free_tier")})
    return 0


async def ping(only):
    from inspect_ai.model import ChatMessageUser, GenerateConfig, get_model
    from inspect_ai.tool import tool

    @tool(name="ping")
    def ping_tool():
        async def execute() -> str:
            """Ping the server.

            Returns:
                The string pong.
            """
            return "pong"
        return execute

    rc = 0
    for name, (mid, fname, effort) in MODELS.items():
        if only and name != only:
            continue
        try:
            model = get_model(f"openrouter/{mid}", **load_cfg(fname))
            # the runs' config: a max_tokens cap would starve reasoning (Anthropic needs a budget of 1024+)
            cfg = GenerateConfig(temperature=1.0, **({"reasoning_effort": "medium"} if effort else {}))
            out = await model.generate(
                [ChatMessageUser(content="Call the ping tool once, then stop.")],
                tools=[ping_tool()], config=cfg)
            u = out.usage
            print(f"{name}: ok | tool_call={bool(out.message.tool_calls)} | stop={out.stop_reason} | "
                  f"in={u and u.input_tokens} out={u and u.output_tokens} | text={out.completion[:80]!r}")
            rc |= not out.message.tool_calls
        except Exception as e:
            print(f"{name}: ERROR {type(e).__name__}: {str(e)[:300]}")
            rc = 1
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", action="store_true")
    ap.add_argument("--ping", action="store_true")
    ap.add_argument("--yes", action="store_true", help="confirm the PAID --ping")
    ap.add_argument("--only", choices=list(MODELS))
    a = ap.parse_args()
    if a.key:
        return key_check()
    if a.ping:
        if not a.yes:
            names = [a.only] if a.only else list(MODELS)
            print(f"PAID: would make 1 generate() call (run config, no max_tokens) to each of {names} via OpenRouter. "
                  "Nothing called. Re-run with --yes to proceed.")
            return 1
        return asyncio.run(ping(a.only))
    return free_check()


if __name__ == "__main__":
    sys.exit(main())
