# Table 5: the pilot's runs

## For the report

**Table 5.** The pilot's full runs at the final code (Nov 20, 2026). Smoke runs are not shown. No sample failed.

| Stage | Model | Samples | Wall time (min) | Tokens per sample |
|---|---|--:|--:|--:|
| 1 | gpt-oss-120b (agent) | 24 | 6.4 | 5,424 |
| 1 | GLM 5.3 Flash (agent) | 24 | 2.2 | 4,154 |
| 2 | GPT-6 Luna, on gpt-oss-120b's calls | 960 | 13.8 | 1,047 |
| 2 | GPT-6 Luna, on GLM 5.3 Flash's calls | 672 | 8.8 | 1,147 |
| 2 | Nemotron 3.5 Super VL, on gpt-oss-120b's calls | 960 | 14.6 | 1,564 |
| 2 | Nemotron 3.5 Super VL, on GLM 5.3 Flash's calls | 672 | 9.4 | 1,639 |
| 3 | gpt-oss-120b with GPT-6 Luna, gate on call | 24 | 7.7 | 10,467 |
| 3 | gpt-oss-120b with GPT-6 Luna, labels, no warning | 24 | 7.8 | 10,405 |
| 3 | gpt-oss-120b with GPT-6 Luna, labels, warning | 24 | 5.0 | 9,974 |

*Note.* Wall time runs from a run's start to its end. Tokens per sample counts every model in the run.

For the text that cites the table:

> Every run finished, with no failed sample in the 9 full runs (3,384 samples) or the 7 smoke runs (84), and every
> answered call came from its pinned provider (Table 5). A stage-2 decision took about 5 seconds and 1,300 tokens; a
> live stage-3 episode took about 33 seconds of work and 10,300 tokens. Eight stage-2 replies (0.2%), all from
> Nemotron 3.5 Super VL, could not be read and were counted as asks.

## Record

**Source.** `records/fp3-pilot-final/`, through its six `manifest.json` files (`final-stage1`, `final-luna-1`,
`final-luna-2`, `final-nemotron35-1`, `final-nemotron35-2`, `final-stage3`), read with
`inspect_ai.log.read_eval_log`. Each manifest also lists its stage's smoke runs. n = 9 full runs (3,384 samples) and 7
smoke runs (84 samples).

**Command.** `uv run python dev/report.py records/fp3-pilot-final/final-*/manifest.json` prints each row's samples,
failed samples, wall time and input, output and total tokens. Tokens per sample is the total tokens divided by the
samples. For some models the total is larger than input plus output; the table uses the total as the provider
reported it.

**Average per sample, by stage (9 full runs, 3,384 samples)**

| Stage | Runs | Samples | Time per sample (s) | Tokens per sample |
|---|--:|--:|--:|--:|
| 1 | 2 | 48 | 25.7 | 4,789 |
| 2 | 4 | 3,264 | 5.1 | 1,341 |
| 3 | 3 | 72 | 32.8 | 10,282 |

*Note.* Time per sample is the mean of Inspect's working time for each sample, which leaves out time spent waiting
for a free connection; counting that wait, a stage-3 sample averages 93.5 s. Tokens per sample is the stage's total
tokens divided by its samples.

**Checks.**

- **Failed samples:** 0 of 3,384 in the full runs and 0 of 84 in the smoke runs. A failed sample errored or has no
  result from its stage's scorer.
- **Smoke runs:** all 7 passed (2 in stage 1, 4 in stage 2, 1 in stage 3) by the launcher's own check in
  `dev/pipeline.py`: the log finished, no sample errored, and the stage's own test held. In stage 1 the agent called
  tools; in stage 2 all 12 samples were scored and at most 3 replies were unreadable; in stage 3 the gate decided
  calls.
- **Pinned providers:** all 4,405 answered model calls, in the full runs and the smoke runs, came from their pinned
  provider: DeepInfra for gpt-oss-120b, Z.AI for GLM 5.3 Flash, OpenAI for GPT-6 Luna and Crusoe for Nemotron 3.5
  Super VL. The reply names only the provider, so this check cannot see the pinned precision (bf16).
- **Too many requests:** the logs do not record attempts that a provider turned away as too many requests. Inspect
  retries such an attempt itself, each call's retry count and request ids are empty in these logs, and the
  adaptive-connection history, which would show a cut after rate limits, was turned off for this run. What the logs do
  show is that no model call ended in an error.
- **Unreadable replies:** 0.2% (8/3,264) of the stage-2 replies could not be read, all from Nemotron 3.5 Super VL (5
  of 960 on gpt-oss-120b's calls and 3 of 672 on GLM 5.3 Flash's); GPT-6 Luna had none. They count as asks.
  `parser-check.md` shows that each one begins with ALLOW or ASK joined to the next word.
- **Three counts agree.** The numbers above were counted three ways, and every number they share agrees: the
  `dev/report.py` command above; a recount straight from the logs that uses neither `dev/report.py` nor
  `src/trustlabel/analysis/`; and a third count that applies the launcher's smoke check, the stage averages and the
  provider check. The `dev/report.py` table on these records also matches the same table printed from the original
  logs on Nov 20.
