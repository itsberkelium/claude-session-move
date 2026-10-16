# claude-session-move

Move a Claude Code terminal session from one Mac to another. Export on one machine, import on the other, then `claude --resume`.

> **Warning: a bundle contains your whole conversation.** Transcripts can hold secrets (tokens, `.env` contents that were printed) and private code. The bundle is a plain, unencrypted `.tar.gz`. Move it yourself (AirDrop, USB stick, synced folder), never post it anywhere, and delete it when you are done. This tool uploads nothing and makes no network calls.

Current version: **0.1.0** (see [CHANGELOG.md](CHANGELOG.md)). `claude-session-move --version` prints it.

## Install

One Python 3.9+ file, standard library only. Copy it onto your PATH:

```sh
python3 claude-session-move install
```

This copies the script to `~/.local/bin` (change it with `--prefix DIR`) and tells you the one line to add to `~/.zshrc` if that folder is not on your PATH. It never edits your shell files. Running `install` again upgrades the installed copy.

## Use

On the first Mac, from the project directory:

```sh
claude-session-move export latest -o ~/Desktop/mysession.claude-session.tar.gz
```

On the second Mac, from the cloned repo of the same project (any path, any username):

```sh
claude-session-move import ~/Desktop/mysession.claude-session.tar.gz
```

It prints the exact `cd ... && claude --resume <id>` command to run.

Other commands: `list` (sessions of a directory), `doctor <bundle|session-id>` (alias `verify`), `handoff-prompt`, `cleanup <session-id>`, `install`.

`cleanup <session-id> [--dir DIR] [--backups]` deletes an imported session (transcript and its `<id>/` folder) from the project folder of `DIR`, and with `--backups` its import backups too. It asks first, needs `--yes` without a terminal, and `--dry-run` previews. It cannot tell an imported session from an original one, so check the listed paths before you confirm.
Flags: `--dry-run` on export and import (changes nothing), `--memory` (also bundle `memory/`), `--no-sidecar`, `--force`, `--dir`, `--project-folder`.
Run `claude-session-move export` with no session in a terminal to pick from a list.

## What is and is not moved

- **Moved:** the transcript, its `<id>/` folder (subagents, tool results), optionally `memory/`.
- **Not moved:** open task lists, file-history/rewind checkpoints, prompt history, MCP servers, permissions, hooks, login. Run `claude-session-move handoff-prompt`, paste the output into the session, and save the reply if you need the tasks.
- **The code is not moved.** Push your repo and pull it on the other Mac; otherwise the session refers to files that are not there.
- Claude Code should be the same version or newer on the importing Mac. The tool warns otherwise.

## How it works

- Transcripts live in `$CLAUDE_CONFIG_DIR/projects/<folder>/` (default `~/.claude`). `<folder>` is the project path with every non-alphanumeric character replaced by `-`.
- On import only the `cwd` field is rewritten to the new path. Message text and tool output are history and stay as they are.
- An existing session id is never overwritten without `--force`; the old files are copied to `<config>/session-move-backups/<time>/` first.
- Paths over 200 characters or with non-ASCII characters cannot be mapped reliably. Use `--project-folder NAME`.
- The target directory is resolved with `realpath` (on macOS `/tmp` is `/private/tmp`); Claude Code looks sessions up under the resolved path.
- `doctor` checks by file and never runs Claude, so nothing calls the API. A real `claude --resume` of an imported session was tested by hand and worked.

## Tests

```sh
python3 -m unittest discover -s tests
```

They use a fake config directory in a temp folder and never touch `~/.claude`.

## License

MIT. Keep the copyright notice when you copy or modify it.
