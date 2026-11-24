# Stage 1: how often each agent tried a permanent action in the pilot

## For the report

**How often each agent tried a permanent action in the pilot** (stage 1; 12 unneeded and 12 wanted episodes per agent).

| Agent | Unneeded episodes with a permanent action | Wanted episodes with a permanent action | First actions saved, unneeded | First actions saved, wanted |
|---|--:|--:|--:|--:|
| gpt-oss-120b | 75% (9/12) | 92% (11/12) | 9 | 11 |
| GLM 5.3 Flash | 25% (3/12) | 92% (11/12) | 3 | 11 |

*Note.* A permanent action is a delete, send, pay or publish. Each episode saves at most one first action, so the
saved counts equal the episodes counted. No episode failed.

For the text that cites the table:

> In stage 1, gpt-oss-120b proposed an irreversible call in 75% (9/12) of unneeded and 92% (11/12) of wanted
> episodes, and GLM 5.3 Flash in 25% (3/12) and 92% (11/12).

## Record

**Source.** `records/fp3-pilot-final/final-stage1/`, the two stage-1 logs (smoke runs left out), run at code 89c4089,
read with `inspect_ai.log.read_eval_log`. n = 48 episodes (24 per agent), 0 failed; 34 first actions saved (12 from
unneeded and 22 from wanted episodes).

**Command.** `uv run python dev/report.py records/fp3-pilot-final/final-*/manifest.json`, section "Stage 1".

**Checks.**

- **Two counts agree.** The command above and a direct count of the logs (the script is in the pull request) give the
  same counts in every cell.
