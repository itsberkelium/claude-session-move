# Glossary

**Session**: one Claude Code conversation, stored as `<session-id>.jsonl` in a project folder.

**Transcript**: the `<session-id>.jsonl` file. One JSON object per line. The only file `claude --resume` strictly needs.

**Sidecar**: the optional `<session-id>/` folder next to a transcript, holding `subagents/` and `tool-results/`.

**Project folder**: `<config-dir>/projects/<name>`, where `<name>` is derived from a working directory. Holds transcripts, sidecars and `memory/`.

**Config dir**: `$CLAUDE_CONFIG_DIR` if set, otherwise `~/.claude`.

**Project path**: the absolute working directory a session ran in. Recorded as `cwd` on transcript lines.

**Bundle**: the single `.claude-session.tar.gz` file that `export` writes and `import` reads. Contains a manifest, the transcript, optionally the sidecar and memory.

**Manifest**: `manifest.json` at the bundle root: schema version, original project path, session id, tool and Claude Code versions, creation time, and a sha256 per file.

**Handoff prompt**: text the user pastes into a running session to make it write down state the bundle cannot carry (open tasks, next steps).

**Not carried**: state outside `projects/<folder>`: tasks, file-history, `history.jsonl`, session-env, MCP servers, permissions, hooks, auth, and the repo's code itself.
