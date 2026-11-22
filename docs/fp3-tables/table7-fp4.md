# Table 7: the full run

## For the report

**Table 7.** What the full run ran on Nov 15, 2026, by stage and model (11 logs, 28,880 samples).

| Stage | Model and role | Design | Samples |
|---|---|---|--:|
| 1 | gpt-oss-120b (agent) | 80 versions x 2 repeats | 160 |
| 1 | GLM 5.3 Flash (agent) | 80 versions x 2 repeats | 160 |
| 2 | GPT-6 Luna (gate) | every saved first call, every condition | 13,104 |
| 2 | Nemotron 3.5 Super VL (gate) | every saved first call, every condition | 13,104 |
| 2 | Llama 4 Maverick (AlignmentCheck seat) | every saved first call, AlignmentCheck rows only | 1,872 |
| 3 | gpt-oss-120b with GPT-6 Luna as the live gate | 3 policies x 160 episodes | 480 |

*Note.* The 9 smoke runs (12 samples each) are not shown; all passed. No sample failed. A sample is one agent episode
in stage 1 (one version, one repeat), one gate decision on one saved first call under one condition in stage 2, and one
live episode with the gate deciding the agent's calls in stage 3. In stage 2 the agent's calls come from both stage-1
agents. The AlignmentCheck seat runs only the AlignmentCheck rows (8 per saved call; the other gates run 56).

### Time and cost

The whole run took about 4 hours 5 minutes, from 4:26 PM to 8:31 PM EST on Nov 15 (the stages overlapped). A stage-2
decision took about 4 seconds of work from GPT-6 Luna, 7 from Llama 4 Maverick and 14 from Nemotron 3.5 Super VL; a
live stage-3 episode took about 26 seconds of work (77 with waiting) and about 9,900 tokens.

| Stage | Model | Samples | Time per sample (s) | Tokens per sample |
|---|---|--:|--:|--:|
| 1 | gpt-oss-120b (agent) | 160 | 18.2 | 5,638 |
| 1 | GLM 5.3 Flash (agent) | 160 | 15.7 | 3,672 |
| 2 | GPT-6 Luna | 13,104 | 3.9 | 1,213 |
| 2 | Llama 4 Maverick | 1,872 | 6.6 | 2,510 |
| 2 | Nemotron 3.5 Super VL | 13,104 | 13.6 | 1,742 |
| 3 | gpt-oss-120b with GPT-6 Luna, gate on call | 160 | 18.6 | 9,928 |
| 3 | gpt-oss-120b with GPT-6 Luna, labels, no warning | 160 | 28.3 | 9,701 |
| 3 | gpt-oss-120b with GPT-6 Luna, labels, warning | 160 | 31.0 | 10,143 |

*Note.* Time per sample is the mean of Inspect's working time, which leaves out time spent waiting for a free
connection. Counting that wait, a stage-3 sample takes 56.1, 83.8 and 91.9 s (same row order); in the other stages the
two differ by under 1 s. Tokens per sample counts every model in the run (stage 3: agent and gate). Stage-2 rows pool
the two logs of a model, weighted by samples.

## Record

**Source.** `records/fp4/`, through its 8 manifests (`fp4-stage1`, `fp4-luna-1`, `fp4-luna-2`, `fp4-maverick-1`,
`fp4-maverick-2`, `fp4-nemotron35-1`, `fp4-nemotron35-2`, `fp4-stage3`). n = 20 logs and 28,988 samples including the
9 smoke runs (108 samples); the 11 full-run logs hold 28,880.

**Command.** `uv run python dev/report.py $(find records/fp4 -name manifest.json)` prints each full-run log's samples,
failed samples, wall time and tokens. Time per sample and tokens per sample in the second table are the log means
pooled by samples; the whole-run wall time is the first smoke start (4:25:56 PM) to the last full-run end (8:31:19 PM),
245.4 min.

**Per-stage clock time (start of first log to end of last, EST).** Stage 1: 4:25:56 to 5:02:40 PM (36.7 min, smoke
included). Stage 2: 5:02:56 PM to 8:31:19 PM (208.4 min). Stage 3: 5:03:03 to 6:48:48 PM (105.8 min). Stages 2 and 3
ran at the same time.

**Checks.**

- **Two counts agree.** The `dev/report.py` table and an independent recount straight from the logs (per-log samples,
  failed samples, start and end times, working and total time per sample, tokens) agree on every number they share.
- **Failed samples:** 0 of 28,988 (0 of 28,880 in the full runs, 0 of 108 in the smoke runs).
- **Smoke runs:** all 9 passed (2 in stage 1, 6 in stage 2, 1 in stage 3) by the launcher's rule: the log finished,
  no sample errored, and the stage's own test held. Stage 1: the agent called tools. Stage 2: all 12 samples were
  scored and at most 3 replies were unreadable (the smokes had 0). Stage 3: the gate decided calls.
- **Why the Maverick seat has fewer samples.** Its stage-2 logs are set to run only the AlignmentCheck rows
  (task argument `alignment_rows` is `only`, with `intent_rows` False and no wording rows), while the Luna and
  Nemotron logs run all rows (`alignment_rows` is `add`, with intent and wording rows on). That is 8 samples per saved
  first call against 56: 1,872 / 8 = 234 saved calls, 13,104 / 56 = 234. This was a design decision of Nov 13: the Maverick seat runs only the AlignmentCheck rows (Yash's run notes, not in
  the repo).
- **Too many requests:** Inspect logs do not record attempts that a provider turned away as too many requests, so
  this method cannot see retried attempts; it shows only that no sample ended in an error.
