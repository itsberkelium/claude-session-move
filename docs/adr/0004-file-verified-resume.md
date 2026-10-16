# 0004. Resume is file-verified, not run

`claude -p --resume` calls the model API and appending a turn changes the copy. The tool and its tests therefore check that the transcript sits at the right path, is valid JSONL, and matches the session id and `cwd`. The folder name rule is documented as "non-alphanumerics become `-`", truncated at 200 characters plus a hash; the tool refuses over-200 and non-ASCII paths and offers `--project-folder`.
