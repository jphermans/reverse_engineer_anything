"""Settings and history storage for reverse_engineer_anything."""

import json
import os
import threading
from datetime import datetime, timezone

from helpers import plugins

PLUGIN_NAME = "reverse_engineer_anything"
DEFAULT_ROOT = "/a0/usr/workdir/rea"
DEFAULT_HISTORY_LIMIT = 200
DEFAULT_MAX_TOTAL_MB = 10240

_lock = threading.Lock()


def load_settings() -> dict:
    """Resolve plugin settings with safe defaults."""
    try:
        settings = plugins.get_plugin_config(PLUGIN_NAME) or {}
    except Exception:
        settings = {}
    root = str(settings.get("workspace_root") or DEFAULT_ROOT).strip() or DEFAULT_ROOT
    try:
        limit = int(settings.get("history_limit") or DEFAULT_HISTORY_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_HISTORY_LIMIT
    limit = max(10, min(limit, 2000))
    try:
        quota_mb = int(settings.get("max_total_mb") or 0)
    except (TypeError, ValueError):
        quota_mb = DEFAULT_MAX_TOTAL_MB
    quota_mb = max(0, min(quota_mb, 1000000))
    return {
        "workspace_root": root,
        "history_limit": limit,
        "max_total_mb": quota_mb,
    }


def history_file(root: str) -> str:
    return os.path.join(root, "history.jsonl")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_history(root: str, entry: dict) -> dict:
    """Append one history entry; returns the stored entry with id and ts."""
    stored = dict(entry)
    stored.setdefault("id", str(int(datetime.now().timestamp() * 1000)))
    stored.setdefault("ts", utc_now())
    line = json.dumps(stored, ensure_ascii=False)
    with _lock:
        os.makedirs(root, exist_ok=True)
        with open(history_file(root), "a", encoding="utf-8") as fh:
            print(line, file=fh)
    return stored


def list_history(root: str, limit: int) -> list:
    """Return the most recent entries in chronological order."""
    path = history_file(root)
    if not os.path.isfile(path):
        return []
    entries = []
    with _lock:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entries.append(json.loads(stripped))
                except json.JSONDecodeError:
                    continue
    return entries[-limit:]


def clear_history(root: str) -> int:
    """Delete the history file; returns the number of removed entries."""
    path = history_file(root)
    count = 0
    with _lock:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                count = sum(1 for line in fh if line.strip())
            os.remove(path)
    return count


def remove_entry(root: str, entry_id: str) -> bool:
    """Remove one entry by id; returns True when found and removed."""
    path = history_file(root)
    if not os.path.isfile(path):
        return False
    kept = []
    found = False
    with _lock:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError:
                    kept.append(stripped)
                    continue
                if str(obj.get("id")) == str(entry_id):
                    found = True
                    continue
                kept.append(stripped)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for line in kept:
                print(line, file=fh)
        os.replace(tmp, path)
    return found
