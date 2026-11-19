"""Regression tests for the v0.4.2 install-hang fix (no framework, no apt).

The original bug: the apt size simulation ran as a blocking subprocess.run
inside the async API handler and froze the event loop for up to 120s while
apt locks were held. These tests guard the fix:

Run: python tests/test_install_api.py
"""

import asyncio
import importlib.util
import os
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


markers = _load("rea_markers_test", os.path.join(REPO, "helpers", "job_markers.py"))
installer = _load("rea_installer2_test", os.path.join(REPO, "helpers", "installer.py"))


def test_marker_roundtrip_and_clear():
    with tempfile.TemporaryDirectory() as root:
        assert markers.read(root) is None
        markers.mark(root, ["jq"], ["jq"])
        data = markers.read(root)
        assert data == {"tools": ["jq"], "packages": ["jq"]}
        markers.mark(root, ["jadx", "r2"], [])
        data = markers.read(root)
        assert data["tools"] == ["jadx", "r2"]
        markers.clear(root)
        assert markers.read(root) is None
        markers.clear(root)  # idempotent


def test_marker_tolerates_corrupt_file():
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, ".install_interrupted.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        assert markers.read(root) is None
        os.remove(path)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("[1,2]")
        assert markers.read(root) is None


def test_simulate_timeout_raises_clear_error():
    real_run = subprocess.run

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 45))

    subprocess.run = fake_run
    try:
        try:
            installer._apt_simulate(["jq"])
        except RuntimeError as exc:
            assert "45s" in str(exc)
            assert "apt is probably busy" in str(exc)
        else:
            raise AssertionError("expected RuntimeError on simulation timeout")
    finally:
        subprocess.run = real_run


def test_handler_uses_worker_thread_for_simulation():
    """Static guard: the plan/install actions must not call plan_payload
    directly on the event loop anymore."""
    src = open(os.path.join(REPO, "api", "tools_install.py"), encoding="utf-8").read()
    assert "import asyncio" in src
    assert src.count("asyncio.to_thread(tool_install.plan_payload") == 2
    assert "payload = tool_install.plan_payload(" not in src
    assert "if tool_install.busy():" in src


def test_to_thread_keeps_event_loop_live():
    """Runtime proof of the pattern used in the handler: while a slow
    simulation runs in a worker thread, the loop keeps serving tasks."""
    def slow_runner(_packages):
        time.sleep(0.3)
        return ""

    async def main():
        ticks = []

        async def ticker():
            for _ in range(30):
                ticks.append(time.monotonic())
                await asyncio.sleep(0.02)

        task = asyncio.create_task(ticker())
        await asyncio.to_thread(installer.estimate, ["jq"], runner=slow_runner)
        task.cancel()
        return ticks

    ticks = asyncio.run(main())
    # A blocking call would have produced at most one tick before/after.
    assert len(ticks) >= 5, "event loop was starved during the simulation"


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
