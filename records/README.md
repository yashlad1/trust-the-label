# Run records

Logs of the runs on real models, one folder per run. They are stored with Git LFS: run `git lfs install` once, then
`git lfs pull` after you clone or pull. Without Git LFS each `.eval` file is a small text pointer instead of a log.

Each file is a copy of the original Inspect log. The only change is that local home paths were made relative to the
repository root. A scan of every file found no keys, tokens, authorization headers, emails or home paths.

| folder | when | code | what ran | logs | status |
|---|---|---|---|---|---|
| `fp3-pilot-final/` | Nov 20, 2026, 2:00 to 2:37 PM EST | 89c4089 (on main as 3727b7f) | The FP3 pilot at the final code: 12 jobs (3 per kind, both versions, `dev/pilot-jobs/`), one trial each. Stage 1: gpt-oss-120b and GLM 5.3 Flash. Stage 2: GPT-6 Luna and Nemotron 3.5 Super VL, 48 rows per stored first call. Stage 3: gpt-oss-120b with GPT-6 Luna as the live gate, three policies. | 16 (9 runs and 7 smokes) | complete, 0 failed samples |

## Using a run

From the repository root:

    uv run python dev/report.py records/fp3-pilot-final/final-*/manifest.json
    uv run inspect view --log-dir records/fp3-pilot-final

The pilot has six manifests: `final-stage1` (stage 1), `final-luna-1` and `final-luna-2`, `final-nemotron35-1` and
`final-nemotron35-2` (stage 2: each gate on each agent's stored calls), and `final-stage3` (stage 3). The stage-2 logs'
settings name the stage-1 logs at `logs/fp3-pilot-final/...`, where they were when the run happened; the same files
are here under `records/fp3-pilot-final/...`.

Never edit, move or delete anything in this folder. A new run gets a new folder.
