"""Pure tests for the v0.5.0 phase-true install progress (no framework).

Run: python tests/test_progress.py
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


installer = _load("rea_progress_test", os.path.join(REPO, "helpers", "installer.py"))


def test_step_plan_apt_only():
    steps = installer.build_step_plan(["jq"], {})
    assert steps == [
        "Updating package lists",
        "Installing: jq",
        "Recording approved tools",
    ]


def test_step_plan_packages_and_non_apt():
    steps = installer.build_step_plan(["binutils"], {"prettier": "npm i -g prettier"})
    assert steps == [
        "Updating package lists",
        "Installing: binutils",
        "Running: npm i -g prettier",
        "Recording approved tools",
    ]


def test_step_plan_empty():
    assert installer.build_step_plan([], {}) == []


def test_percent_boundaries():
    assert installer.percent_for_step(0, 3) == 0
    assert installer.percent_for_step(1, 3) == 33
    assert installer.percent_for_step(2, 3) == 67
    assert installer.percent_for_step(3, 3) == 100
    assert installer.percent_for_step(9, 3) == 100
    assert installer.percent_for_step(0, 0) == 100


def test_percent_multi_package_join():
    steps = installer.build_step_plan(["jadx", "r2", "wabt"], {})
    assert steps[1] == "Installing: jadx, r2, wabt"
    assert installer.percent_for_step(1, 3) == 33


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:
                failures += 1
                print("FAIL", name, "-", exc)
    print("RESULT:", "PASS" if failures == 0 else "FAIL")
    sys.exit(1 if failures else 0)
