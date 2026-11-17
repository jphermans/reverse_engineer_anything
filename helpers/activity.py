"""Live activity state for the sidebar indicator.

Writes an atomic activity.json under the workspace root so the WebUI
sidebar can poll what the plugin is doing right now and what it just
finished. Kept separate from the append-only history: activity reflects
only the latest state of the most recent mutation.
"""

import json
import os
import threading

from usr.plugins.reverse_engineer_anything.helpers import state

_lock = threading.Lock()


def _activity_file(root: str) -> str:
    return os.path.join(root, "activity.json")


def _write(root: str, payload: dict) -> None:
    path = _activity_file(root)
    tmp = path + ".tmp"
    with _lock:
        os.makedirs(root, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp, path)


def start(root: str, action: str, detail: str = "") -> None:
    """Mark a mutation as running (sidebar shows a busy state)."""
    _write(
        root,
        {
            "status": "busy",
            "action": action,
            "detail": detail,
            "ts": state.utc_now(),
        },
    )


def finish(root: str, action: str, detail: str = "", ok: bool = True) -> None:
    """Record the outcome of a mutation (sidebar shows the result)."""
    _write(
        root,
        {
            "status": "done" if ok else "error",
            "action": action,
            "detail": detail,
            "ts": state.utc_now(),
        },
    )


def get_activity(root: str) -> dict:
    """Return the latest activity entry, or an idle placeholder."""
    path = _activity_file(root)
    if not os.path.isfile(path):
        return {"status": "idle", "action": "", "detail": "", "ts": ""}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {"status": "idle", "action": "", "detail": "", "ts": ""}
    if not isinstance(data, dict):
        return {"status": "idle", "action": "", "detail": "", "ts": ""}
    data.setdefault("status", "idle")
    data.setdefault("action", "")
    data.setdefault("detail", "")
    data.setdefault("ts", "")
    return data
