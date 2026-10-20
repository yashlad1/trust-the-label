<!-- AI-generated (Claude Code): team README for the final project skeleton -->
# Trust the Label? (Group 12, CS6983 Agentic AI)

We test how agent approval layers handle false MCP tool annotations. The system has one agent loop, local MCP
servers, five approval policies, a scripted user and a scorer that reads the final sandbox state.

## Setup

```bash
uv sync
cp .env.example .env    # add your OpenRouter key; .env is never committed
```

## Layout

| Folder | What goes there | Owner |
|---|---|---|
| `src/trustlabel/servers/` | Local MCP servers (items, messages, invoices, posts), with label and name switches | Will |
| `src/trustlabel/scorer.py` | Reads the final sandbox state | Will |
| `src/trustlabel/policies/` | The five approval policies and the gate prompt | Vignesh |
| `src/trustlabel/analysis/` | Harm, catch, false-alarm and task-success rates; paired test with Holm correction | Vignesh |
| `src/trustlabel/scenarios/` | 40 jobs, each in an unneeded and a wanted version, with ground truth and the user's answer rules | Isha |
| `src/trustlabel/harness/` | The Inspect task, the agent-to-gate loop and the scripted user | Yash |
| `src/trustlabel/contracts.py` | Shared formats: tool call, decision, scenario. Changes need everyone they affect. | everyone |
| `tests/` | Same layout as `src/`. Mockllm and plain functions only, no paid calls. | owner of the matching folder |
| `dev/` | Run scripts and mockllm configs. `dev/scratch/` is for personal experiments and is never committed. | anyone |

`scorer.py` and `contracts.py` are added in week 1.

## Working on it

```bash
git switch main && git pull               # use team-setup until it is merged into main
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
