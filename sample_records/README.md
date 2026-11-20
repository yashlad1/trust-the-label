# Sample run records

dry_run_fake_model.zip holds one complete dry run of the experiment on Inspect's fake model (mockllm): two stage-1 runs (one per agent seat), stage 2 for both gate seats with the standard, intent-sentence and wording rows, and the three stage-3 policies, plus the manifest and the scripted stage-1 log the dry run replayed. The fake model calls no tools and gives no real verdicts, so these records show the format of the logs and the manifest, not real behaviour. The records of the real-model runs are in `records/`; see `records/README.md`.

Open it from the repo root:

    unzip sample_records/dry_run_fake_model.zip -d sample_records/
    uv run python dev/report.py sample_records/dry_run/manifest.json

Each .eval file is an Inspect log; open one with `uv run inspect view --log-dir sample_records/dry_run`. Contents: 13 log files, 2.1 MB zipped; jobs: the 10 delete jobs, one trial.
