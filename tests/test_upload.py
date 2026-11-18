"""Regression tests for the upload hardening (v0.3.2).

Covers the three points raised in review on Hub PR #701:
1. Size limits are enforced while reading, not after a full in-memory
   read; a refused upload leaves no partial output and never replaces
   an existing file.
2. Each ZIP is capped on the total size it expands to; a zip whose
   declared entries exceed the total limit is refused before any file
   is written.
3. Deleting a symlinked workspace directory is refused.

Run with the framework runtime:
    PYTHONPATH=/a0 /opt/venv-a0/bin/python tests/test_upload.py
Dependency-free: prints PASS/FAIL per test and exits non-zero on failure.
"""

import importlib.util
import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, "/a0")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_package():
    # Load the BUILD copy under test (not the live plugin dir); its internal
    # `from usr.plugins...` imports resolve against the installed helpers,
    # whose validate_name/add_history are unchanged.
    return _load("rea_upload_test", os.path.join(REPO, "helpers", "upload.py"))


def _make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, payload in files:
            zf.writestr(name, payload)
    return buf.getvalue()


def test_plain_file_limit_enforced_while_reading():
    upload = _load_package()
    with tempfile.TemporaryDirectory() as ws:
        existing = os.path.join(ws, "target.bin")
        with open(existing, "wb") as fh:
            fh.write(b"ORIGINAL")
        stream = io.BytesIO(b"x" * 2000)
        try:
            upload.store_plain_file(ws, "target.bin", stream, limit=1000)
            raise AssertionError("expected UploadError")
        except upload.UploadError:
            pass
        # Refused upload: no partial output, existing file untouched.
        assert not os.path.exists(os.path.join(ws, "target.bin.part"))
        with open(existing, "rb") as fh:
            assert fh.read() == b"ORIGINAL"


def test_plain_file_within_limit_replaces_atomically():
    upload = _load_package()
    with tempfile.TemporaryDirectory() as ws:
        target = os.path.join(ws, "ok.bin")
        upload.store_plain_file(ws, "ok.bin", io.BytesIO(b"hello"), limit=1000)
        assert open(target, "rb").read() == b"hello"
        assert not os.path.exists(target + ".part")


def test_zip_total_limit_refused_before_extraction():
    upload = _load_package()
    data = _make_zip(
        [("a.txt", "A" * 800), ("b.txt", "B" * 800)]
    )
    with tempfile.TemporaryDirectory() as ws:
        try:
            upload.extract_zip(ws, "bomb.zip", data, limit=1000, total_limit=1500)
            raise AssertionError("expected UploadError")
        except upload.UploadError:
            pass
        # Nothing was written: the declared sizes already exceed the cap.
        assert os.listdir(ws) == []


def test_zip_within_limits_extracts():
    upload = _load_package()
    data = _make_zip(
        [("sub/a.txt", "A" * 800), ("b.txt", "B" * 400)]
    )
    with tempfile.TemporaryDirectory() as ws:
        result = upload.extract_zip(ws, "ok.zip", data, limit=1000, total_limit=1500)
        assert result["extracted"] == 2
        assert os.path.getsize(os.path.join(ws, "sub", "a.txt")) == 800
        assert os.path.getsize(os.path.join(ws, "b.txt")) == 400
        assert not any(name.endswith(".part") for name in os.listdir(ws))


def test_symlinked_workspace_delete_refused():
    workspace = _load("rea_ws_test", os.path.join(REPO, "helpers", "workspace.py"))
    with tempfile.TemporaryDirectory() as root:
        outside = os.path.join(root, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(root, "link-ws"))
        try:
            workspace.delete_workspace(root, "link-ws", True)
            raise AssertionError("expected WorkspaceError")
        except workspace.WorkspaceError as exc:
            assert "symlink" in str(exc).lower()
        # The symlink itself survives the refused deletion.
        assert os.path.islink(os.path.join(root, "link-ws"))


def test_real_workspace_delete_still_works():
    workspace = _load("rea_ws_test2", os.path.join(REPO, "helpers", "workspace.py"))
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "real-ws", "sub"))
        with open(os.path.join(root, "real-ws", "sub", "f.bin"), "wb") as fh:
            fh.write(b"x" * 10)
        result = workspace.delete_workspace(root, "real-ws", True)
        assert result["removed"] is True
        assert not os.path.exists(os.path.join(root, "real-ws"))


def main():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print("PASS %s" % test.__name__)
        except AssertionError as exc:
            failed += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        except Exception as exc:  # unexpected error type is a failure too
            failed += 1
            print("FAIL %s: unexpected %r" % (test.__name__, exc))
    print("RESULT %d/%d" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())