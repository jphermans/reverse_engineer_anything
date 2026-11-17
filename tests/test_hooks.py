"""Regression tests for the reverse_engineer_anything lifecycle hooks.

Guards against the "Failed to load settings" bug: hooks.py must never import
the framework hook names (get_plugin_config / save_plugin_config) into its own
namespace, because the framework resolves those hooks itself and a module-level
import shadows them with the wrong signature. This bug was fixed in commit
8321a92, reintroduced by a stale hooks.py in the v0.2.0 release commit and
fixed again in v0.3.1.

Run with the framework runtime:
    PYTHONPATH=/a0 /opt/venv-a0/bin/python tests/test_hooks.py
Dependency-free: prints PASS/FAIL per test and exits non-zero on failure.
"""

import importlib.util
import os
import sys

sys.path.insert(0, "/a0")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(REPO, "hooks.py")


def _load_hooks():
    spec = importlib.util.spec_from_file_location("rea_hooks_test", HOOKS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hooks_do_not_shadow_framework_hook_names():
    module = _load_hooks()
    for hook in ("get_plugin_config", "save_plugin_config"):
        assert not hasattr(module, hook), (
            "hooks.py defines %s; the framework resolves this hook itself and a "
            "module-level import shadows it (causes Failed to load settings)" % hook
        )


def test_install_uses_module_import_and_runs():
    import helpers.plugins as plugins

    called = []

    def stub(name, agent=None):
        called.append(name)
        return {"workspace_root": "/tmp/rea-hooks-test-root"}

    original = plugins.get_plugin_config
    plugins.get_plugin_config = stub
    try:
        module = _load_hooks()
        module.install()
    finally:
        plugins.get_plugin_config = original
    assert called == [module.PLUGIN_NAME], "install must query its own plugin config"


def test_lifecycle_hooks_return_none():
    module = _load_hooks()
    assert module.pre_update() is None
    assert module.uninstall() is None


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
    print("RESULT %d/%d" % (len(tests) - failed, len(tests)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
