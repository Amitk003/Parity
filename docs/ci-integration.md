# CI integration

## What CI does

`.github/workflows/parity-ci.yml` runs two jobs on every push to `main` and every pull request.

**lint-test** runs on every push and pull request. It installs dev dependencies, runs `ruff check src tests`, and runs `pytest -q`. This job is fast and needs no database.

**parity-live** runs on pushes to `main` only. It starts Postgres and Db2 with Docker Compose, builds the Linux bridge image, seeds the sample data, and runs `parity run --dir samples --bridge`. Exit code 0 means every sample query matched on real databases. Exit code 1 fails the job. The HTML report, JSON summary, and history file are uploaded as an artifact.

## Seed script

`scripts/seed_sample.py` creates the `demo_users` table in Postgres, inserts three rows, syncs schema and data to Db2, and prints the shared checksum. It runs inside the bridge container, where the `ibm_db` driver works. It uses the same environment variables as the CLI, so a local run and a CI run behave the same.

## Why two jobs

The unit tests catch most breakage in seconds. The live job is slower because the Db2 image is large, so it only gates `main`. A contributor gets fast feedback on every pull request, and a slow end to end proof lands on every merge.

## Local proof

Before this branch, the live behavior was demonstrated by hand on the same commands: the sample run returned exit 0 with all three queries MATCH after the aggregate alias fix. A seeded mismatch returns exit 1 and fails the job. That behavior is the contract the workflow enforces.

## Known limit

The live job depends on Docker image pull time for Db2. On a first run that takes minutes. Cache the image layer in a later branch if CI gets slow.
