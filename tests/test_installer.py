"""Pure mapping tests for the installer whitelist (no apt, no framework).

Run: python tests/test_installer.py
"""

import importlib.util
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = _load("rea_installer_test", os.path.join(REPO, "helpers", "installer.py"))


def test_plan_whitelist_only():
    result = installer.plan(["jadx", "not-a-tool", "", "jadx"])
    assert result["valid"] == ["jadx"]
    assert result["invalid"] == ["not-a-tool"]
    assert result["packages"] == ["jadx"]


def test_plan_dedupes_packages():
    result = installer.plan(["nm", "readelf", "objdump"])
    assert result["packages"] == ["binutils"]


def test_plan_non_apt_commands():
    result = installer.plan(["ilspycmd", "prettier"])
    assert "ilspycmd" in result["non_apt"]
    assert "prettier" in result["non_apt"]
    assert result["packages"] == []


def test_bundle_resolution():
    tools = installer.bundle_tools("essentials")
    assert tools and "jadx" in tools
    assert installer.bundle_tools("nope") is None
    planned = installer.plan(tools)
    assert "jadx" in planned["packages"]


def test_to_bytes_locale_handling():
    assert installer._to_bytes("12.3", "kB") == 12300
    assert installer._to_bytes("1,234", "kB") == 1234000
    assert installer._to_bytes("45,6", "MB") == 45600000
    assert installer._to_bytes("147", "MB") == 147000000


def test_estimate_parses_sim_output():
    text = (
        "Need to get 12.3 kB of archives.\n"
        "after this operation, 45,6 MB of additional disk space will be used.\n"
    )
    download, disk = installer._parse_sim_output(text)
    assert download == 12300
    assert disk == 45600000


def test_estimate_zero_packages():
    assert installer.estimate([]) == {"download_bytes": 0, "disk_bytes": 0}


def test_human_bytes():
    assert installer.human_bytes(0) == "0 B"
    assert installer.human_bytes(1500) == "1.5 kB"


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
