import importlib.machinery
import importlib.util
import io
import json
import os
import tarfile
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_loader = importlib.machinery.SourceFileLoader("csm", os.path.join(HERE, "..", "claude-session-move"))
_spec = importlib.util.spec_from_loader("csm", _loader)
csm = importlib.util.module_from_spec(_spec)
_loader.exec_module(csm)

SID = "26a02a86-fac0-4339-90e0-1fbc9fe64ce5"


def read(path):
    with open(path) as fh:
        return fh.read()


def make_session(cfg, project, sid=SID, old=False, branch="master"):
    """Write a fake transcript (+ sidecar + memory) for `project` under the fake config dir."""
    folder = csm.encode_project_path(project)
    base = os.path.join(cfg, "projects", folder)
    os.makedirs(os.path.join(base, sid, "tool-results"))
    os.makedirs(os.path.join(base, "memory"))
    lines = [
        {"type": "last-prompt", "sessionId": sid},
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": "<command-name>x</command-name>"},
         "cwd": project, "sessionId": sid},
        {"type": "user", "message": {"role": "user", "content": "Fix the login bug in %s" % project},
         "cwd": project, "sessionId": sid, "version": "2.1.301", "gitBranch": branch},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
         "cwd": project + "/src", "sessionId": sid, "version": "2.1.301", "gitBranch": branch},
    ]
    path = os.path.join(base, sid + ".jsonl")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(l, separators=(",", ":")) for l in lines) + "\n")
    if old:
        t = time.time() - 3600
        os.utime(path, (t, t))
    with open(os.path.join(base, sid, "tool-results", "r1.txt"), "w") as fh:
        fh.write("big output")
    with open(os.path.join(base, "memory", "note.md"), "w") as fh:
        fh.write("remember")
    return base, path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.realpath(self.tmp.name)
        self.cfg = os.path.join(self.root, "claude")
        self.msgs = []
        self.log = self.msgs.append

    def mkdir(self, *parts):
        p = os.path.join(self.root, *parts)
        os.makedirs(p, exist_ok=True)
        return p

    def export(self, project, **kw):
        out = os.path.join(self.root, "b.claude-session.tar.gz")
        kw.setdefault("force", True)
        csm.export_session(self.cfg, project, SID, out=out, log=self.log, **kw)
        return out


class EncodingTests(unittest.TestCase):
    def test_non_alphanumerics_become_dashes(self):
        self.assertEqual(csm.encode_project_path("/Users/a/Code/x"), "-Users-a-Code-x")
        self.assertEqual(csm.encode_project_path("/Users/a/.t3/my repo_2"), "-Users-a--t3-my-repo-2")

    def test_long_and_non_ascii_refused(self):
        with self.assertRaises(csm.ToolError):
            csm.encode_project_path("/" + "a" * 250)
        with self.assertRaises(csm.ToolError):
            csm.encode_project_path("/Users/çağrı/x")

    def test_config_dir_env(self):
        self.assertEqual(csm.config_dir({"CLAUDE_CONFIG_DIR": "/tmp/zz"}), "/tmp/zz")
        self.assertTrue(csm.config_dir({}).endswith("/.claude"))


class ExportImportTests(Base):
    def test_round_trip_to_different_path_and_username(self):
        src = self.mkdir("Users", "work", "Code", "repo")
        make_session(self.cfg, src, old=True)
        bundle = self.export(src, memory=True)
        manifest, members = csm.open_bundle(bundle)
        self.assertEqual(manifest["project_path"], src)
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["claude_code_version"], "2.1.301")
        self.assertIn("sidecar/%s/tool-results/r1.txt" % SID, members)
        self.assertIn("memory/note.md", members)

        dst_cfg = os.path.join(self.root, "other-claude")
        dst = self.mkdir("Users", "me", "dev", "repo")
        res = csm.import_bundle(dst_cfg, bundle, dst, log=self.log, claude_version="2.1.301")
        path = os.path.join(dst_cfg, "projects", res["folder"], SID + ".jsonl")
        self.assertEqual(res["folder"], csm.encode_project_path(dst))
        rows = [json.loads(l) for l in read(path).splitlines()]
        cwds = [r["cwd"] for r in rows if "cwd" in r]
        self.assertEqual(cwds, [dst, dst, dst + "/src"])
        text = read(path)
        self.assertIn("Fix the login bug in %s" % src, text)  # message text is history: untouched
        self.assertTrue(os.path.isfile(os.path.join(dst_cfg, "projects", res["folder"], SID, "tool-results", "r1.txt")))
        self.assertTrue(os.path.isfile(os.path.join(dst_cfg, "projects", res["folder"], "memory", "note.md")))
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertIn("claude --resume %s" % SID, "\n".join(self.msgs))
        self.assertEqual(csm.doctor_session(dst_cfg, dst, SID), ([], []))

    def test_path_with_spaces(self):
        src = self.mkdir("My Work", "the repo")
        make_session(self.cfg, src, old=True)
        bundle = self.export(src)
        dst = self.mkdir("Personal Stuff", "the repo")
        dst_cfg = os.path.join(self.root, "c2")
        res = csm.import_bundle(dst_cfg, bundle, dst, log=self.log)
        self.assertEqual(res["folder"], csm.encode_project_path(dst))
        self.assertIn("'%s'" % dst, "\n".join(self.msgs))  # quoted in the resume command
        self.assertEqual(csm.doctor_session(dst_cfg, dst, SID), ([], []))

    def test_collision_without_force_then_force_backs_up(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        bundle = self.export(src)
        dst_cfg = os.path.join(self.root, "c2")
        dst = self.mkdir("b")
        csm.import_bundle(dst_cfg, bundle, dst, log=self.log)
        folder = csm.encode_project_path(dst)
        target = os.path.join(dst_cfg, "projects", folder, SID + ".jsonl")
        with open(target, "a") as fh:
            fh.write('{"type":"marker","sessionId":"%s"}\n' % SID)
        with self.assertRaises(csm.ToolError) as ctx:
            csm.import_bundle(dst_cfg, bundle, dst, log=self.log)
        self.assertIn("--force", str(ctx.exception))
        self.assertIn("marker", read(target))  # untouched
        csm.import_bundle(dst_cfg, bundle, dst, force=True, log=self.log)
        self.assertNotIn("marker", read(target))
        found = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(dst_cfg, "session-move-backups")) for f in fs
                 if f == SID + ".jsonl"]
        self.assertEqual(len(found), 1)
        self.assertIn("marker", read(found[0]))

    def test_memory_skip_unless_force(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        bundle = self.export(src, memory=True)
        dst_cfg = os.path.join(self.root, "c2")
        dst = self.mkdir("b")
        mem = os.path.join(dst_cfg, "projects", csm.encode_project_path(dst), "memory")
        os.makedirs(mem)
        with open(os.path.join(mem, "note.md"), "w") as fh:
            fh.write("mine")
        csm.import_bundle(dst_cfg, bundle, dst, log=self.log)
        self.assertEqual(read(os.path.join(mem, "note.md")), "mine")
        csm.import_bundle(dst_cfg, bundle, dst, force=True, log=self.log)
        self.assertEqual(read(os.path.join(mem, "note.md")), "remember")

    def test_target_must_exist(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        bundle = self.export(src)
        with self.assertRaises(csm.ToolError):
            csm.import_bundle(self.cfg, bundle, os.path.join(self.root, "nope"), log=self.log)

    def test_no_sidecar_and_no_memory_by_default(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        _, members = csm.open_bundle(self.export(src, sidecar=False))
        self.assertEqual(sorted(members), ["manifest.json", "transcript/%s.jsonl" % SID])

    def test_old_claude_version_warns(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        bundle = self.export(src)
        dst = self.mkdir("b")
        csm.import_bundle(os.path.join(self.root, "c2"), bundle, dst, log=self.log, claude_version="2.0.1")
        self.assertIn("warning: exported with Claude Code 2.1.301", "\n".join(self.msgs))

    def test_active_session_warning(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=False)
        self.export(src)
        self.assertIn("may still be running", "\n".join(self.msgs))

    def test_export_refuses_to_replace_bundle(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        out = self.export(src)
        with self.assertRaises(csm.ToolError):
            csm.export_session(self.cfg, src, SID, out=out, force=False, log=self.log)


class DryRunTests(Base):
    def tree(self, root):
        return sorted(os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs)

    def test_export_dry_run_writes_nothing(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        out = os.path.join(self.root, "never.tar.gz")
        csm.export_session(self.cfg, src, SID, out=out, dry_run=True, log=self.log)
        self.assertFalse(os.path.exists(out))

    def test_import_dry_run_writes_nothing(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        bundle = self.export(src, memory=True)
        dst_cfg = os.path.join(self.root, "c2")
        dst = self.mkdir("b")
        csm.import_bundle(dst_cfg, bundle, dst, dry_run=True, log=self.log)
        self.assertFalse(os.path.exists(dst_cfg))
        self.assertIn("dry run", "\n".join(self.msgs))


class BundleSafetyTests(Base):
    def rewrite_bundle(self, bundle, mutate):
        out = os.path.join(self.root, "evil.tar.gz")
        with tarfile.open(bundle) as src, tarfile.open(out, "w:gz") as dst:
            for m in src.getmembers():
                data = src.extractfile(m).read()
                m2, data2 = mutate(m, data)
                if m2 is not None:
                    dst.addfile(m2, io.BytesIO(data2))
        return out

    def good(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        return self.export(src), self.mkdir("b")

    def test_corrupt_file_is_not_a_bundle(self):
        path = os.path.join(self.root, "junk.tar.gz")
        with open(path, "wb") as fh:
            fh.write(b"not a tarball")
        with self.assertRaises(csm.ToolError):
            csm.import_bundle(self.cfg, path, self.mkdir("b"), log=self.log)
        errors, _ = csm.doctor_bundle(path)
        self.assertTrue(errors)

    def test_truncated_gzip(self):
        bundle, dst = self.good()
        with open(bundle, "rb") as fh:
            data = fh.read()
        with open(bundle, "wb") as fh:
            fh.write(data[: len(data) // 2])
        with self.assertRaises(csm.ToolError):
            csm.import_bundle(self.cfg, bundle, dst, log=self.log)

    def test_edited_transcript_fails_checksum(self):
        bundle, dst = self.good()

        def mutate(m, data):
            if m.name.endswith(".jsonl"):
                data = data + b'{"type":"x"}\n'
                m.size = len(data)
            return m, data
        evil = self.rewrite_bundle(bundle, mutate)
        errors, _ = csm.doctor_bundle(evil)
        self.assertTrue(any("Checksum mismatch" in e for e in errors))
        with self.assertRaises(csm.ToolError):
            csm.import_bundle(os.path.join(self.root, "c2"), evil, dst, log=self.log)
        self.assertFalse(os.path.exists(os.path.join(self.root, "c2")))

    def test_path_traversal_entry_rejected(self):
        bundle, dst = self.good()

        def mutate(m, data):
            if m.name.endswith(".jsonl"):
                m.name = "../../escape.jsonl"
            return m, data
        evil = self.rewrite_bundle(bundle, mutate)
        with self.assertRaises(csm.ToolError) as ctx:
            csm.open_bundle(evil)
        self.assertIn("unsafe path", str(ctx.exception))

    def test_symlink_entry_rejected(self):
        bundle, _ = self.good()
        out = os.path.join(self.root, "link.tar.gz")
        with tarfile.open(bundle) as src, tarfile.open(out, "w:gz") as dst:
            for m in src.getmembers():
                dst.addfile(m, src.extractfile(m))
            link = tarfile.TarInfo("sidecar/x")
            link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
            dst.addfile(link)
        with self.assertRaises(csm.ToolError):
            csm.open_bundle(out)

    def test_invalid_jsonl_line_reported(self):
        src = self.mkdir("a")
        _, path = make_session(self.cfg, src, old=True)
        with open(path, "a") as fh:
            fh.write("{broken\n")
        bundle = self.export(src)
        errors, _ = csm.doctor_bundle(bundle)
        self.assertTrue(any("line 5 is not valid JSON" in e for e in errors), errors)


class DoctorAndCliTests(Base):
    def test_doctor_session_cwd_not_rewritten(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        errors, _ = csm.doctor_session(self.cfg, src, SID)
        self.assertEqual(errors, [])
        other = self.mkdir("b")
        folder = csm.encode_project_path(other)
        # Simulate a hand-copied (not rewritten) session.
        os.makedirs(os.path.join(self.cfg, "projects", folder))
        src_t = os.path.join(self.cfg, "projects", csm.encode_project_path(src), SID + ".jsonl")
        with open(src_t) as a, open(os.path.join(self.cfg, "projects", folder, SID + ".jsonl"), "w") as b:
            b.write(a.read())
        errors, _ = csm.doctor_session(self.cfg, other, SID)
        self.assertTrue(any("cwd" in e for e in errors), errors)

    def test_doctor_missing_session(self):
        errors, _ = csm.doctor_session(self.cfg, self.mkdir("a"), SID)
        self.assertTrue(any("not found" in e for e in errors))

    def test_listing_title_skips_meta_and_sorts(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        rows = csm.list_sessions(self.cfg, csm.encode_project_path(src))
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["title"].startswith("Fix the login bug"))

    def test_pick_latest_and_no_tty_error(self):
        rows = [{"id": "b", "mtime": 2, "size": 1, "title": "t"}, {"id": "a", "mtime": 1, "size": 1, "title": "t"}]
        self.assertEqual(csm.pick_session(rows, "latest"), "b")
        with self.assertRaises(csm.ToolError):
            csm.pick_session(rows, None, stdin=io.StringIO(), stdout=io.StringIO())

    def test_cli_end_to_end_exit_codes(self):
        src = self.mkdir("a")
        make_session(self.cfg, src, old=True)
        env = {"CLAUDE_CONFIG_DIR": self.cfg}
        out = os.path.join(self.root, "cli.claude-session.tar.gz")
        buf = io.StringIO()
        self.assertEqual(csm.run(["export", "latest", "--dir", src, "-o", out], env=env, stdout=buf), 0)
        self.assertEqual(csm.run(["doctor", out], env=env, stdout=io.StringIO()), 0)
        self.assertEqual(csm.run(["handoff-prompt"], env=env, stdout=buf), 0)
        with open(out, "r+b") as fh:
            fh.truncate(40)
        self.assertEqual(csm.run(["doctor", out], env=env, stdout=io.StringIO()), 1)


if __name__ == "__main__":
    unittest.main()
