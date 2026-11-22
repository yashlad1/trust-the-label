# Trust the Label? (Group 12, CS6983 Agentic AI)

An agent uses tools through MCP servers. Before a risky call runs, an LLM approval gate decides: let it run, or ask
the user first. Each tool carries MCP annotations (such as "read-only" or "destructive") and a name. We test whether
the gate judges the tool's annotations and name, or the user's actual request. The work has three stages. In stage 1
agents propose calls. In stage 2 gates judge those stored calls under every condition. In stage 3 the whole loop
(agent, gate, scripted user, scorer) runs live.

Team: Yash (harness and runs), Will (MCP servers and scorer), Vignesh (approval policies and analysis), Isha
(scenarios).

## Repo layout

```
src/trustlabel/
  contracts.py   shared formats: tool call, decision, scenario
  servers/       local MCP servers (items, messages, invoices, posts) with label and name switches
  policies/      the approval policies and the gate prompt
  scenarios/     the job files (delete, send, pay, publish), wording.json, load.py, check.py
  harness/       the Inspect tasks (tasks.py), the agent-to-gate loop, replay of stored calls, scripted user
  analysis/      the measures computed from the logs
  scorer.py      scores the final sandbox state
dev/
  pipeline.py          runs the whole experiment end to end (dry or paid)
  report.py            prints the runs table and the measure tables
  scripted_stage1.py   makes stage-1 logs on the fake model, for free dry runs
  run.sh, progress.sh  run helper and a progress printer for long runs
  check_openrouter.py  pings each model once
  models/              one provider config per model (see Models)
tests/                 same layout as src/; fake model only
sample_records/        a small zipped sample of a dry run
records/               logs of the real-model runs, stored with Git LFS (see records/README.md)
```

## Setup

Needs Python 3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env     # put your OpenRouter key on its one line; this file is never committed
```

Run everything with `uv run ...`. It makes `import trustlabel` work.

## Dependencies

From `pyproject.toml`: `inspect-ai` (the evaluation framework), `mcp` (the MCP servers), `openai` (the client library).

## Conditions

Each job exists in two versions. In the "unneeded" version the user's request does not need the risky action. In the
"wanted" version it does. Each tool has an honest name and a vague name. Labels are the tool's annotations: true,
false, or none shown.

| Condition | What changes | How to run it |
|---|---|---|
| Stage 1: agents propose | The agent works each job version. The policy is "never ask", so nothing stops it. The full runs use the honest name only (the task's default lists both names). | `uv run inspect eval src/trustlabel/harness/tasks.py@stage1 --model <agent> -T names=honest -T epochs=2` |
| Stage 2, standard rows | Every stored call is judged 28 ways: gate on call (no labels), and gate with labels x label true / false / none x warning off / on (7 conditions), each under both names and both requests. | `uv run inspect eval src/trustlabel/harness/tasks.py@stage2 --model <gate> -T logs=<stage-1 .eval>[,<more>]` (add `-T scenarios=<job files>` when the stage-1 run used job files other than the delete jobs; stage 2 needs both versions of every job in the logs) |
| Stage 2, intent-sentence rows | Adds 12 rows per call: gate prompt with one added sentence about the user's intent; labels true / false / none, warning off, both names, both requests. | add `-T intent_rows=true` |
| Stage 2, wording rows | Adds 8 rows per call: vague name only, labels false and none, four request wordings (unneeded or wanted, calm or loud). | add `-T wording_rows=src/trustlabel/scenarios/wording.json` |
| Stage 2, ask-first rows (E1, added after the freeze) | Adds 2 rows per call: the call's own request ends with "Check with me before you do anything that can't be undone."; gate with labels, labels none and false, the vague name, warning off. | add `-T ask_first_rows=true` |
| Stage 3, gate on call | Live loop; the gate sees the call, no labels. | `uv run inspect eval src/trustlabel/harness/tasks.py@stage3 --model <agent> -T policy=gate_on_call -T name=honest -T gate_model=<gate> -T gate_config=<yaml> -T gate_effort=<effort>` |
| Stage 3, gate with labels, warning off | The gate also sees the tool's labels. | same, with `-T policy=gate_with_labels -T label=false -T warning=false` |
| Stage 3, gate with labels, warning on | As above, plus a warning sentence in the gate prompt. | same, with `-T warning=true` |
| Stage 3, reference policies | No gate model needed: `never_ask` (always runs) and `label_rule` (decides from the label alone). | `-T policy=never_ask` or `-T policy=label_rule` |

Stage parameters (all passed as `-T name=value`):

- `stage1`: `scenarios` (comma-separated job files, default the delete jobs), `names` (default `honest,vague`),
  `epochs` (2), `max_steps` (12), `seed` (0).
- `stage2`: `logs` (required), `scenarios`, `first_only` (true: only each episode's first irreversible call),
  `intent_rows` (false), `wording_rows` (empty), `ask_first_rows` (false).
- `stage3`: `policy` (default `gate_with_labels`), `label` (`true`, `false` or `none`; default `false`), `name`
  (default `vague`), `warning` (false), `gate_model`, `gate_config`, `gate_effort`, `scenarios`, `epochs` (1),
  `max_steps` (12), `seed` (0).

Model flags, as in `dev/pipeline.py`: add `--model-config dev/models/<model>.yaml` for the provider pin and
`--reasoning-effort medium` where the model has that setting (see Models). Example gate for stage 3:
`-T gate_model=openrouter/openai/gpt-6-luna -T gate_config=dev/models/gpt-6-luna.yaml -T gate_effort=medium`.

What stays fixed between conditions: the jobs, the stored call, the user's record list and the scorer. Only the
named switch changes (label, warning, name, request wording, or the added sentence). Stage 2 and stage 3 show the gate
the same text for the same condition.

## Running everything

Free dry run on the fake model (no paid call, no key needed):

```bash
uv run python dev/scripted_stage1.py logs/dry_stage1          # prints the stage-1 log path
uv run python dev/pipeline.py dry logs/dry \
    --wording src/trustlabel/scenarios/wording.json --stage1-logs <that log path> [--jobs <files>] [--epochs N]
```

A plain fake model never calls a tool, so the scripted stage 1 supplies calls to replay. `--jobs` takes
comma-separated job files and defaults to the delete jobs. `--epochs` sets repeats for the full stage-1 and stage-3
runs.

Paid run (needs an OpenRouter key in `.env` and costs money):

```bash
uv run python dev/pipeline.py paid logs/run --wording src/trustlabel/scenarios/wording.json [--jobs <files>] [--epochs N]
```

The run pings each model once, then for each stage runs a 12-sample smoke first. The full stage starts only if the
smoke passes its checks (the agent called tools; at most 3 of 12 gate replies unreadable; the gate decided calls).
A spend stop ends the run when billed spend passes a set limit. Run it detached, with the computer plugged in:

```bash
perl -MPOSIX -e 'POSIX::setsid(); exec @ARGV' -- caffeinate -is uv run python dev/pipeline.py paid logs/run \
    --wording src/trustlabel/scenarios/wording.json > logs/run.out 2>&1 < /dev/null &
```

The runner writes `<out>/manifest.json`: the stage-1 logs, the stage-2 log per gate, the stage-3 log per policy, the
job files, the wording file, the epochs and the live gate. Check the job files first with
`uv run python -m trustlabel.scenarios.check --wording src/trustlabel/scenarios/wording.json`.

## Getting the summaries

`uv run python dev/report.py <out>/manifest.json` prints the runs table: samples, failed samples (counted as
outcomes), wall time, tokens and billed cost. It also accepts `.eval` files directly.

The same command also prints the measure tables from `src/trustlabel/analysis/rates.py`: the stage-1 table; for each
gate, the stage-2 table and the reference lines; and the stage-3 table.

A sample: `unzip sample_records/dry_run_fake_model.zip -d sample_records/` then
`uv run python dev/report.py sample_records/dry_run/manifest.json`.

`uv run --with matplotlib python dev/fp3_chart.py` draws the pilot's headline chart (Figure 2) into
`docs/figures/fp3-pilot-headline.png` and `.svg`, and writes its caption page, `docs/figures/fp3-pilot-headline.md`.

## Tests

Plain Python scripts with `assert`. Run one with `uv run python tests/<folder>/<file>.py`, for example
`uv run python tests/servers/test_items.py`. They use the fake model only, so they cost nothing.

## Models

All models run through OpenRouter, with the provider pinned and no fallbacks (configs in `dev/models/`).

| Model | Role | OpenRouter ID | Provider (pinned, no fallbacks) | Reasoning |
|---|---|---|---|---|
| gpt-oss-120b | Agent | `openai/gpt-oss-120b` | DeepInfra (bf16) | medium effort |
| GLM 5.3 Flash | Agent | `z-ai/glm-5.3-flash` | Z.AI first-party | medium effort |
| GPT-6 Luna | Gate (stages 2 and 3) | `openai/gpt-6-luna` | OpenAI first-party | medium effort |
| Nemotron 3.5 Super VL | Gate (stage 2) | `nvidia/nemotron-3.5-super-vl` | Crusoe (bf16) | medium effort |

## Records

The logs of the real-model runs are in `records/`, stored with Git LFS: run `git lfs install` once, then `git lfs pull`
after cloning. `records/README.md` lists each run. `sample_records/` holds a small zipped sample of a dry run on the
fake model.
