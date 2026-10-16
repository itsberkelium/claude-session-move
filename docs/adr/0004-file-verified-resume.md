# 0004. Resume is file-verified, not run

`claude -p --resume` calls the model API and appending a turn changes the copy. The tool and its tests therefore check that the transcript sits at the right path, is valid JSONL, and matches the session id and `cwd`. The folder name rule is documented as "non-alphanumerics become `-`", truncated at 200 characters plus a hash; the tool refuses over-200 and non-ASCII paths and offers `--project-folder`.

## Confirmed 2026-10-16

A real `claude --resume` of an imported copy worked. The target was `/tmp/restore-test/some-repo`, and the project folder was derived from its resolved path (`/private/tmp/...`). So the tool uses `realpath` for the target directory, and `doctor` warns when a session is stored under the unresolved form.
