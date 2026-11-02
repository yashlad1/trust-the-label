<!-- AI-generated (Claude Code): team README for the final project skeleton -->
# Trust the Label? (Group 12, CS6983 Agentic AI)

We test how agent approval layers handle false MCP tool annotations. The system has one agent loop, local MCP
servers, five approval policies, a scripted user and a scorer that reads the final sandbox state.

## Setup

Everyone works in the same environment: Python 3.13 (pinned in `.python-version`) and the exact package versions in
`uv.lock` (inspect-ai 0.3.282, mcp 2.3.0, openai 3.35.1).

```bash
# 1. install uv once (https://docs.astral.sh/uv/)
curl -LsSf https://astral.sh/uv/install.sh | sh                  # macOS / Linux
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"       # Windows

# 2. from the repo folder: Python 3.13 and the locked packages
uv python install 3.13
uv sync --locked

# 3. check: prints 3.13.x and the three versions above, then the items-server test passes
uv run python -c "import sys, importlib.metadata as m; print(sys.version.split()[0], *(f'{p} {m.version(p)}' for p in ('inspect-ai', 'mcp', 'openai')))"
uv run python tests/servers/test_items.py

# 4. your key
cp .env.example .env    # add your OpenRouter key; .env is never committed
```

Run everything through `uv run ...` so it uses this environment. To add a dependency, run `uv add <package>` and
commit `pyproject.toml` and `uv.lock` together in their own pull request.

## Layout

| Folder | What goes there | Owner |
|---|---|---|
| `src/trustlabel/servers/` | Local MCP servers (items, messages, invoices, posts), with label and name switches | Will |
| `src/trustlabel/scorer.py` | Reads the final sandbox state | Will |
| `src/trustlabel/policies/` | The five approval policies and the gate prompt | Vignesh |
| `src/trustlabel/analysis/` | Agent proposal rates, gate outcomes, harm and task success; paired tests with Holm correction | Vignesh |
| `src/trustlabel/scenarios/` | 40 jobs, each in an unneeded and a wanted version, with ground truth and the user's answer rules | Isha |
| `src/trustlabel/harness/` | The Inspect task, the agent-to-gate loop and the scripted user | Yash |
| `src/trustlabel/contracts.py` | Shared formats: tool call, decision, scenario. Changes need everyone they affect. | everyone |
| `tests/` | Same layout as `src/`. Mockllm and plain functions only, no paid calls. | owner of the matching folder |
| `dev/` | Run scripts and mockllm configs. `dev/scratch/` is for personal experiments and is never committed. | anyone |

`scorer.py` and `contracts.py` are added in week 1.

## Working on it

```bash
git switch main && git pull
git switch -c <name>/<topic>              # e.g. will/items-server
# work and commit
git push -u origin <name>/<topic>         # then open a pull request into main
git fetch && git merge origin/main        # stay current: merge, don't rebase and force-push
```

One branch per piece of the week plan, merged by Sunday.

## Rules

- Nobody pushes to main directly. Every change goes in through a pull request with one teammate's review.
- Each pull request touches only its author's folders, except a change to `contracts.py`.
- Tests make no paid model calls.
- Never commit `.env`, keys, logs or raw `.eval` files. Zip logs and commit them only when needed.
- Tag AI-assisted code as the course AI policy requires. Everyone explains their own files in the live code walkthrough.
- Every paid model run goes through Yash.
