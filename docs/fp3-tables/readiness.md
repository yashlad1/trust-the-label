# Readiness assessment

## For the report

- **Every condition ran correctly.** After free dry runs on the fake model passed, the pilot at the final code and the
  full run finished with no failed sample (3,468 and 28,988 samples, smoke runs included), every smoke run passed, and
  all 38 test files pass.
- **Problems fixed before the results.** Blank replies from a provider now fail the sample instead of counting as the
  agent stopping, and a host check confirms that every call reached its pinned provider (4,405 of 4,405 in the pilot).
- **A problem kept as scored.** In 53 replies, under 1%, Nemotron 3.5 Super VL joined its answer to the next word
  ("ASKThe…"). By the rule fixed before the runs these count as asks, which changes 10 outcomes in a few cells and
  none behind H1, H1b, H2a, H2b, the H5 rerun or E1.
- **The records hold what each measure needs.** Every table is computed from the run records, and the pilot's numbers
  were recounted independently from the raw logs.
- **Floor and ceiling cases are named.** A setting where more than 90% of calls get through with no label gets no
  verdict; Luna's high-stakes wording test had no room to pass, since it already asked on 90% of the calm requests;
  and H1c says so when the false-label ask rate is under 10%.
- **Labels check.** The two labellers agree on 70 of 160 requests (Cohen's kappa 0.10), so the sheets could not check
  our answer key. A blind reading by two language models found no unneeded request that read as needing the action,
  and all 40 jobs are kept.
- **Parser check.** A person and the parser read 16 of 24 replies the same way and reached the same outcome on 22 of
  24; every unreadable reply had its answer joined to the next word.
- **Still open.** The check of 20 live transcripts against the scorer (#8), and the later-calls analysis.

## Record

| Bullet | Source | What the source cannot show |
|---|---|---|
| Pilot ran correctly | `docs/fp3-tables/table5-runs.md` (PR #130, open): 0 failed in the 9 full runs (3,384 samples) and the 7 smoke runs (84 samples); all 7 smokes passed the launcher's check | A smoke passes the launcher's own check only; it does not test whether the model's answers are good. |
| Full run, 28,988 samples | Two counts agree. Count A (`dev/report.py`) gives 28,880 samples in the 11 full-run logs, 0 failed. Count B (a recount without `dev/report.py`) gives the same per log, plus the 9 smokes with 108 samples: 28,988 in all, 0 failed. Issue #119 holds the table. Yash's run notes, Nov 15 (not in the repo), give the same total. | Both count samples that errored; neither can see a sample that finished with a wrong answer. |
| Dry runs | Yash's run notes, Nov 20, 1:56 PM (not in the repo): both dry runs from the pilot's code (commit 89c4089), fake model, no cost; in the pilot dry run all five processes finished and the report script printed every FP3 table; the wording rerun dry run produced 1,872 rows per gate | A fake model cannot show how real models behave; smoke checks print FAIL on it by design. |
| Tests | The 38 files under `tests/`, each run with `uv run python <file>` on Nov 21, all exit 0 | Anything a test does not assert. |
| Blank-reply guard | PR #74 (a blank agent reply raises an error so the sample counts as failed; the gate side raises on a blank reply too); the team's notes for the final report's limits section (not in the repo), "Blank replies" paragraph | Replies with usage but no text are counted as the agent stopping; at most 1 of 80 unneeded episodes in one condition may have been cut short. |
| Host checks | `dev/pipeline.py` runs `dev/check_openrouter.py --ping` and stops if it fails; `docs/fp3-tables/table5-runs.md`: all 4,405 answered pilot calls came from their pinned provider; the team's record of past issues (not in the repo), entry S06, on the two fixed checks | Host only, not the precision a host serves. |
| Joined replies kept | The team's notes for the final report's limits section (not in the repo), "Gate replies." paragraph: 53 replies, 43 meant ASK, 10 meant ALLOW | The 10 are a hand reading of what the gate meant; the rule scores them as asks. |
| Records and recounts | `records/README.md`; PRs #122 and #124 (records), #125 (launchers); Yash's run notes, Nov 20 (not in the repo): blind recounts of #127 and #128; Yash's notes (not in the repo) record #126 as checked on a blind recount; the Nov 20 2:37 PM pilot entry says every count matches an independent recount from the raw logs, which covers the stage-3 numbers in `docs/fp3-tables/stage3.md` (#123); Table 5 was counted three ways; the pilot's pages recounted from the raw logs are the setup, the swap limit, the parser check, Table 5 and the stage-3 numbers | A recount checks the numbers against the logs, not that the logs measure the right thing. |
| Ceiling | The team's plan for the extra runs (not in the repo): runs where more than 90% of baseline calls are let through with no label are marked as at the ceiling and get no verdict | The 90% line is a rule set by the team. |
| Luna's high-stakes test | The rule: `src/trustlabel/analysis/hypotheses.py` (H5a and H5b need at least 20 points, p < 0.05 and the interval above 0). The rates: the H5 wording rerun of Nov 20, in Yash's run notes (not in the repo): loud 100% (234/234), calm 90% (210/234), a rise of 10.3 points, not met | Whether a bar of 20 was the right size for a gate that already asks 90% of the time. |
| H1c floor | `src/trustlabel/analysis/hypotheses.py`: floor of 10% on the false-label ask rate, below which the row has no room to move and the test cannot read | The cut-off of 10% is a rule set by the team. |
| Labels check | Shared report, Evaluation checks paragraph; Yash's run notes, Nov 20 (not in the repo): 70 of 160 agree, kappa 0.10; one labeller wrote the jobs, and the other gave a job's two versions the same answer in 33 of 40 jobs; a blind reading by two language models found no unneeded request that read as needing the action; all 40 jobs kept | Agreement shows the sheets are noisy; it cannot say which version is right. |
| Parser check | `docs/fp3-tables/parser-check.md` (#128): 16 of 24 replies read the same way and 22 of 24 outcomes the same (15 and 21 counting the answers as first saved); all 8 unreadable replies are from Nemotron, each with the verdict joined to the next word | 24 replies, including all 8 unreadable ones of 3,264; one reader. |
| Still open | Issue #8 (open; compare at least 20 live-loop transcripts with the scorer's result); shared report, "Landed since FP2." paragraph | Nothing yet. |
