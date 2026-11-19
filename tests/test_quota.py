"""Pure tests for the workspace disk quota (no framework).

Run: python tests/test_quota.py
"""

import importlib.util
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quota = _load("rea_quota_test", os.path.join(REPO, "helpers", "quota.py"))


def test_limit_disabled_by_default():
    assert quota.limit_bytes({}) is None
    assert quota.limit_bytes({"max_total_mb": 0}) is None
    assert quota.limit_bytes({"max_total_mb": "junk"}) is None


def test_limit_bytes_conversion():
    assert quota.limit_bytes({"max_total_mb": 1}) == 1000 * 1000
    assert quota.limit_bytes({"max_total_mb": -5}) is None


def test_root_usage_counts_files():
    with tempfile.TemporaryDirectory() as root:
        assert quota.root_usage(root) == 0
        sub = os.path.join(root, "ws")
        os.makedirs(sub)
        with open(os.path.join(sub, "a.bin"), "wb") as fh:
            fh.write(b"x" * 100)
        with open(os.path.join(root, "b.bin"), "wb") as fh:
            fh.write(b"y" * 50)
        assert quota.root_usage(root) == 150


def test_check_passes_under_cap():
    with tempfile.TemporaryDirectory() as root:
        quota.check({"max_total_mb": 1}, root, incoming=500)


def test_check_raises_over_cap():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "f.bin"), "wb") as fh:
            fh.write(b"x" * 999900)  # 999900 used + 200 incoming passes the 1 MB cap
        try:
            quota.check({"max_total_mb": 1}, root, incoming=200)
            raise AssertionError("expected QuotaExceeded")
        except quota.QuotaExceeded:
            pass


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print("PASS %s" % test.__name__)
        except AssertionError as exc:
            failed += 1
            print("FAIL %s: %s" % (test.__name__, exc))
        except Exception as exc:
            failed += 1
            print("FAIL %s: unexpected %r" % (test.__name__, exc))
    print("RESULT %d/%d" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
