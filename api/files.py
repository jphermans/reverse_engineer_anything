"""API handler: workspace file listing and download (read-only).

Route: /api/plugins/reverse_engineer_anything/files
GET params: action=list|download, workspace=<name>, path=<relative>
Auth applies; CSRF stays off so plain session-cookie links can download.
Every resolved path must stay inside the workspace; symlinks that leave
the workspace are refused (same guard as v0.3.2).
"""

import os

from flask import send_file
from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import state, workspace

MAX_LIST_ENTRIES = 2000


class Files(ApiHandler):
    """List and download files inside one workspace."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: Input, request: Request) -> Output:
        data = input if isinstance(input, dict) else {}
        action = str(data.get("action") or request.args.get("action") or "").strip()
        ws_name = str(data.get("workspace") or request.args.get("workspace") or "").strip()
        rel = str(data.get("path") or request.args.get("path") or "").strip()

        if action not in ("list", "download"):
            return {"status": "error", "error": "Unknown action: use list or download."}

        settings = state.load_settings()
        try:
            base = _resolve_workspace(settings["workspace_root"], ws_name)
            target = _resolve_inside(base, rel)
        except workspace.WorkspaceError as exc:
            return {"status": "error", "error": str(exc)}

        if action == "list":
            return _list_dir(target, ws_name, rel)
        return _download(target, rel)


def _resolve_workspace(root, ws_name):
    """Validate and resolve the workspace dir, refusing symlinks and escapes."""
    ws_name = workspace.validate_name(ws_name)
    root_real = os.path.realpath(root)
    unresolved = os.path.join(root_real, ws_name)
    if os.path.islink(unresolved):
        raise workspace.WorkspaceError("Workspace is a symlink; refusing to access it.")
    base = os.path.realpath(unresolved)
    if base != root_real and not base.startswith(root_real + os.sep):
        raise workspace.WorkspaceError("Name escapes the workspace root.")
    if not os.path.isdir(base):
        raise workspace.WorkspaceError("Workspace does not exist.")
    return base


def _resolve_inside(base, rel):
    """Resolve rel inside base; refuse .. parts and symlinks leaving base."""
    parts = [p for p in rel.replace("\\", "/").split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise workspace.WorkspaceError("Path escapes the workspace: " + rel)
    unresolved = os.path.join(base, *parts) if parts else base
    if os.path.islink(unresolved):
        resolved = os.path.realpath(unresolved)
        if resolved != base and not resolved.startswith(base + os.sep):
            raise workspace.WorkspaceError("Symlinked path escapes the workspace: " + rel)
    path = os.path.realpath(unresolved)
    if path != base and not path.startswith(base + os.sep):
        raise workspace.WorkspaceError("Path escapes the workspace: " + rel)
    return path


def _list_dir(target, ws_name, rel):
    """Bounded directory listing (max 2000 entries)."""
    if not os.path.isdir(target):
        return {"status": "error", "error": "Not a directory: " + rel}
    try:
        names = sorted(os.listdir(target))
    except OSError as exc:
        return {"status": "error", "error": "List failed: " + str(exc)}
    entries = []
    for name in names[:MAX_LIST_ENTRIES]:
        path = os.path.join(target, name)
        entry = {"name": name, "is_dir": os.path.isdir(path)}
        if not entry["is_dir"]:
            try:
                entry["size"] = os.path.getsize(path)
            except OSError:
                entry["size"] = 0
        entries.append(entry)
    return {
        "status": "ok",
        "workspace": ws_name,
        "path": rel,
        "entries": entries,
        "truncated": len(names) > MAX_LIST_ENTRIES,
    }


def _download(target, rel):
    """Stream one file as an attachment."""
    if os.path.isdir(target):
        return {"status": "error", "error": "Cannot download a directory."}
    if not os.path.isfile(target):
        return {"status": "error", "error": "File not found: " + rel}
    return send_file(target, as_attachment=True)
