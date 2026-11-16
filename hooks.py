"""Lifecycle hooks for reverse_engineer_anything.

Runs inside the Agent Zero framework runtime. This plugin ships no external
dependencies and owns no background processes: install() only prepares the
default workspace root, uninstall() preserves user data by design (workspaces
and history are user files, not plugin-owned resources).
"""

import os

from helpers.plugins import get_plugin_config

PLUGIN_NAME = "reverse_engineer_anything"
DEFAULT_ROOT = "/a0/usr/workdir/rea"


def install() -> None:
    """Prepare the default workspace root. Safe to rerun."""
    try:
        settings = get_plugin_config(PLUGIN_NAME) or {}
    except Exception:
        settings = {}
    root = str(settings.get("workspace_root") or DEFAULT_ROOT).strip() or DEFAULT_ROOT
    if root != DEFAULT_ROOT:
        # Custom root: created on demand by the API helpers, not managed here.
        return
    os.makedirs(DEFAULT_ROOT, exist_ok=True)


def pre_update() -> None:
    """Nothing to stop: no owned processes or registrations."""
    return None


def uninstall() -> None:
    """Keep user data by design.

    Workspaces and history under the configured workspace root belong to the
    user and survive uninstall. This plugin owns no services, symlinks or
    registrations, so nothing outside the plugin directory needs cleanup.
    """
    return None
