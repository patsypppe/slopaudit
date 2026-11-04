# 0003: Renamed from slopguard to slopaudit

Status: accepted, 2026-11-04, before the first release on PyPI.

## Context

PyPI refused to register `slopguard`: it treats names that differ only by `-`, `_` or `.` as the same, and
`slop-guard` (a prose linter for AI writing patterns) already exists. Three more projects already used the
name: `slopguards` (static checks for AI-generated code, the same purpose as this project, at
github.com/WT-MM/slopguard), `slopguard-cli` (protection against hallucinated packages) and `slopguard-ai`.
Even if a variant could be registered, users would confuse the projects.

## Decision

The project is called **slopaudit**: the package on PyPI, the import name, the command, the configuration
file (`slopaudit.toml`, `[tool.slopaudit]`), the suppression comment (`# slopaudit: ignore[...]`), the
environment variables (`SLOPAUDIT_*`) and the GitHub repository. `slopaudit` and `slop-audit` were free on
PyPI and TestPyPI when this was decided.

## Consequences

- Nothing was ever published to PyPI under the old name, so no users have to migrate. Release candidates
  `1.0.0rc1`, `1.0.0rc2` and `1.0.0` exist on TestPyPI as `slopguard`; they are test uploads only.
- There is no compatibility alias for the old command, file names or comments: a `slopguard` command would
  collide with the other projects above.
- The first PyPI release is `slopaudit 1.0.0`. The `v1.0.0` tag that pointed at the old commit published
  nothing and is moved to the renamed commit.
