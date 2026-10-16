# 0003. Bundle scope: project folder only, no network

The bundle holds only what lives under `projects/<folder>` plus a manifest. Tasks, file-history, history.jsonl and session-env are excluded; the tool offers a handoff prompt for task lists. Nothing is uploaded, redacted or encrypted: the bundle is a plain file the user moves, and the README warns it contains secrets and private code.
