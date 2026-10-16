# Changelog

Versions follow `MAJOR.MINOR.PATCH`. The version lives in `TOOL_VERSION` in `claude-session-move` and is written to every bundle manifest.

## Next: 0.2.0 (in development)

GUI over the core functions. `TOOL_VERSION` stays `0.1.0` until the GUI work is done, then becomes `0.2.0` in the release commit.

## 0.1.0 - 2026-10-16

First release. Single-file Python 3.9+ CLI, standard library only, no network.

- `export`: bundle one session (transcript, `<id>/` sidecar, optional `memory/`) as `.claude-session.tar.gz` with a sha256 manifest (`schema_version` 1). Warns if the session may still be running.
- `import`: derive the project folder from the real target path, rewrite only `cwd`, refuse collisions without `--force`, back up first, reject unsafe tar entries, create files as `0600`.
- `doctor` / `verify`: check a bundle or an imported session.
- `list`, `handoff-prompt`, `cleanup`, `install`, and `--dry-run` for export and import.
- Honors `CLAUDE_CONFIG_DIR`. Refuses paths over 200 characters or with non-ASCII characters unless `--project-folder` is given.
- Real `claude --resume` of an imported session confirmed by hand.
