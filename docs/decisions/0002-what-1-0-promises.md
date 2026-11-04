# 0002: What 1.0 promises

Status: accepted, 2026-11-04.

## Context

The release checklist asked for two things before dropping the `rc` suffix: running the model-assisted
commands against a live provider, and running the Docker sandbox backend once. Neither had happened.
Everything else was verified: 201 tests on Python 3.10 to 3.13, a published and installed release
candidate, a real project scanned with its false positives fixed, and 0 critical or high findings on
1.59 million lines of well-reviewed code.

## Decision

Release 1.0.0 now, and draw the line of the stability promise around what is verified.

| Covered by 1.0 (breaking changes wait for 2.0) | Experimental (may change in a minor release) |
| --- | --- |
| `scan` and every rule marked `stable` | `scan --spec --llm` |
| JSON, SARIF, Markdown and terminal output, exit codes | `gen-tests` |
| `slopaudit.toml`, suppressions, baselines | `fix` |
| `regress`, `bench`, `rules`, `explain`, `init` | The Docker sandbox backend |
| `slopaudit.scan()` and `slopaudit.scan_source()` | Rules marked `experimental` |
| The GitHub Action and the pre-commit hook | |

## Consequences

- The experimental commands say so in `--help`, the docs and the changelog.
- Moving an item from the right column to the left needs the evidence the checklist asked for: a recorded
  run against a live provider, or a Docker run. Issues track both.
