"""Workspace management following the leanrea copy-first rule.

A workspace is a directory under the configured workspace root that holds
copies of analysis targets and their extraction output. Names are strictly
validated and every resolved path must stay inside the root.
"""

import os
import re
import shutil

from usr.plugins.reverse_engineer_anything.helpers import state

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class WorkspaceError(Exception):
    """Raised for invalid or refused workspace operations."""


def validate_name(name: str) -> str:
    name = str(name or "").strip()
    if not NAME_RE.match(name):
        raise WorkspaceError(
            "Ongeldige naam: gebruik letters, cijfers, punt, streep of "
            "underscore (max 64 tekens, begint met letter of cijfer)."
        )
    return name


def _workspace_path(root: str, name: str) -> str:
    base = os.path.realpath(root)
    path = os.path.realpath(os.path.join(base, name))
    if path != base and not path.startswith(base + os.sep):
        raise WorkspaceError("Naam valt buiten de werkruimte-root.")
    return path


def list_workspaces(root: str) -> list:
    """Return workspace directories with sizes and entry counts."""
    base = os.path.realpath(root)
    result = []
    if not os.path.isdir(base):
        return result
    for entry in sorted(os.listdir(base)):
        path = os.path.join(base, entry)
        if not os.path.isdir(path):
            continue
        files = 0
        size = 0
        for dirpath, _dirnames, filenames in os.walk(path):
            for filename in filenames:
                files += 1
                try:
                    size += os.path.getsize(os.path.join(dirpath, filename))
                except OSError:
                    pass
        result.append({
            "name": entry,
            "path": path,
            "files": files,
            "bytes": size,
        })
    return result


def create_workspace(root: str, name: str) -> dict:
    name = validate_name(name)
    path = _workspace_path(root, name)
    os.makedirs(path, exist_ok=True)
    state.add_history(root, {"action": "workspace_create", "workspace": name, "details": path})
    return {"name": name, "path": path}


def delete_workspace(root: str, name: str, confirm: bool) -> dict:
    name = validate_name(name)
    if not confirm:
        raise WorkspaceError("Verwijderen vereist bevestiging (confirm=true).")
    path = _workspace_path(root, name)
    if not os.path.isdir(path):
        raise WorkspaceError("Werkruimte bestaat niet.")
    shutil.rmtree(path)
    state.add_history(root, {"action": "workspace_delete", "workspace": name, "details": path})
    return {"name": name, "removed": True}