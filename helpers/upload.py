"""File uploads into analysis workspaces (copy-first rule).

An upload IS the analysis copy: files land directly inside the target
workspace. ZIP archives are extracted in place with zip-slip protection;
plain files are stored under their sanitized basename.
"""

import os
import shutil
import zipfile

from usr.plugins.reverse_engineer_anything.helpers import state, workspace

# Hard cap per uploaded file, independent of the framework limit (5 GB).
MAX_FILE_BYTES = 500 * 1024 * 1024


class UploadError(Exception):
    """Raised for invalid or refused uploads."""


def _safe_member_path(ws_path: str, member_name: str) -> str:
    """Resolve a zip member inside the workspace, refusing escapes."""
    name = member_name.replace("\\", "/")
    parts = [p for p in name.split("/") if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        raise UploadError("Unsafe path in archive: " + member_name)
    base = os.path.realpath(ws_path)
    path = os.path.realpath(os.path.join(base, *parts))
    if path != base and not path.startswith(base + os.sep):
        raise UploadError("Archive entry escapes the workspace: " + member_name)
    return path


def _safe_filename(filename: str) -> str:
    name = os.path.basename((filename or "").replace("\\", "/")).strip()
    if not name or name in (".", "..") or "/" in name:
        raise UploadError("Invalid filename: " + str(filename))
    return name


def store_plain_file(ws_path: str, filename: str, data: bytes) -> str:
    """Store one plain file under its sanitized basename."""
    if len(data) > MAX_FILE_BYTES:
        raise UploadError("File exceeds the 500 MB per-file limit.")
    safe = _safe_filename(filename)
    target = os.path.join(ws_path, safe)
    with open(target, "wb") as fh:
        fh.write(data)
    return target


def extract_zip(ws_path: str, filename: str, data: bytes) -> dict:
    """Extract a zip archive into the workspace with zip-slip protection."""
    if len(data) > MAX_FILE_BYTES:
        raise UploadError("Archive exceeds the 500 MB per-file limit.")
    import io

    extracted = 0
    skipped = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if info.file_size > MAX_FILE_BYTES:
                    skipped.append(info.filename)
                    continue
                target = _safe_member_path(ws_path, info.filename)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted += 1
    except zipfile.BadZipFile as exc:
        raise UploadError("Not a valid zip archive: " + str(exc))
    return {"stored": os.path.basename(filename), "extracted": extracted, "skipped": skipped}


def handle_upload(root: str, ws_name: str, filename: str, data: bytes) -> dict:
    """Route one upload into the workspace; extracts zip, stores plain files.

    The upload itself creates the workspace when it does not exist yet
    (copy-first: the upload is the analysis copy).
    """
    ws_name = workspace.validate_name(ws_name)
    base = os.path.realpath(root)
    ws_path = os.path.realpath(os.path.join(base, ws_name))
    if ws_path != base and not ws_path.startswith(base + os.sep):
        raise workspace.WorkspaceError("Name escapes the workspace root.")
    if not os.path.isdir(ws_path):
        os.makedirs(ws_path, exist_ok=True)

    if (filename or "").lower().endswith(".zip"):
        result = extract_zip(ws_path, filename, data)
        action = "upload_extract"
    else:
        stored = store_plain_file(ws_path, filename, data)
        result = {"stored": os.path.basename(stored), "extracted": 0, "skipped": []}
        action = "upload"

    state.add_history(root, {
        "action": action,
        "workspace": ws_name,
        "details": result["stored"],
    })
    return {"workspace": ws_name, **result}
