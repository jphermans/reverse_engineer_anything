"""Interrupted-install marker, persisted under the workspace root (PVC).

A background install lives only in memory; a pod replacement kills it and
loses all state. This marker records a running install so the API can tell
the user afterwards that the job was interrupted by a restart.
"""

import json
import os
import threading

_lock = threading.Lock()


def _path(root):
    return os.path.join(root, ".install_interrupted.json")


def mark(root, tools, packages):
    """Record that an install job started (called when the job starts)."""
    with _lock:
        os.makedirs(root, exist_ok=True)
        data = {"tools": list(tools or []), "packages": list(packages or [])}
        tmp = _path(root) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, _path(root))


def read(root):
    """Return the marker dict, or None when absent or unreadable."""
    path = _path(root)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return {
        "tools": [str(t) for t in data.get("tools", [])],
        "packages": [str(p) for p in data.get("packages", [])],
    }


def clear(root):
    """Remove the marker (called when a job finishes, done or error)."""
    with _lock:
        try:
            os.remove(_path(root))
        except FileNotFoundError:
            pass
