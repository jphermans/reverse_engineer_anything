"""Approved-install state, persisted under the workspace root (PVC).

Records which RE tools the user explicitly approved for installation so a
replacement pod can offer a one-click restore. Nothing is installed
automatically: the state only feeds the restore proposal in the UI.
"""

import json
import os
import threading

from usr.plugins.reverse_engineer_anything.helpers import state

_lock = threading.Lock()


def _state_file(root):
    return os.path.join(root, ".installed_tools.json")


def load(root):
    """Return the tolerant dict: tools + bundles name->timestamp maps."""
    path = _state_file(root)
    if not os.path.isfile(path):
        return {"tools": {}, "bundles": {}}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"tools": {}, "bundles": {}}
    if not isinstance(data, dict):
        return {"tools": {}, "bundles": {}}
    result = {"tools": {}, "bundles": {}}
    for key in ("tools", "bundles"):
        value = data.get(key)
        if isinstance(value, dict):
            result[key] = {str(k): str(v) for k, v in value.items()}
    return result


def record(root, kind, name, ts=""):
    """Record one approved install (kind tool or bundle); returns the state."""
    if kind not in ("tool", "bundle"):
        raise ValueError("kind must be tool or bundle")
    key = "tools" if kind == "tool" else "bundles"
    with _lock:
        current = load(root)
        current[key][str(name)] = ts or state.utc_now()
        path = _state_file(root)
        os.makedirs(root, exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(current, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    return current


def restore_names(root, available_names):
    """Split recorded tools into missing (restore candidates) and present."""
    recorded = load(root)
    present_set = set(available_names or [])
    missing = [n for n in recorded["tools"] if n not in present_set]
    return {
        "missing": sorted(missing),
        "present": sorted(n for n in recorded["tools"] if n in present_set),
        "bundles": sorted(recorded["bundles"]),
    }
