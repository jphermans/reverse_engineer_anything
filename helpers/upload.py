"""File uploads into analysis workspaces (copy-first rule).

An upload IS the analysis copy: files land directly inside the target
workspace. ZIP archives are extracted in place with zip-slip protection;
plain files are stored under their sanitized basename.

Limits are enforced while the data flows, not after a full in-memory
read: plain files are streamed to disk in bounded chunks and refused at
the first byte past the per-file limit, ZIP data is read with the same
per-file cap, and every archive is additionally capped on the total
size it expands to. Declared entry sizes are checked before extraction
and the actual written bytes are counted during it, so a lying header
cannot bypass the cap. Refused uploads leave no partial output, and
existing files are replaced only after a complete, valid read.
"""

import os
import zipfile

from usr.plugins.reverse_engineer_anything.helpers import quota, state, workspace

# Hard cap per uploaded file, independent of the framework limit (5 GB).
MAX_FILE_BYTES = 500 * 1024 * 1024
# Cap on the total size a single ZIP may expand to across all entries.
MAX_ZIP_TOTAL_BYTES = 1024 * 1024 * 1024
# Read/write chunk size; bounds peak memory while streaming.
CHUNK_SIZE = 1024 * 1024


class UploadError(Exception):
    """Raised for invalid or refused uploads."""


def _fmt_limit(limit: int) -> str:
    mb, rest = divmod(limit, 1024 * 1024)
    return "%d MB" % mb if rest == 0 else "%d bytes" % limit


def _discard(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


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


def read_limited(stream, limit: int = MAX_FILE_BYTES) -> bytes:
    """Read a stream in chunks, refusing the first byte past the limit."""
    chunks = []
    total = 0
    while True:
        chunk = stream.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise UploadError(
                "Upload exceeds the %s per-file limit." % _fmt_limit(limit)
            )
        chunks.append(chunk)
    return b"".join(chunks)


def store_plain_file(
    ws_path: str, filename: str, stream, limit: int = MAX_FILE_BYTES
) -> str:
    """Stream one plain file to disk under its sanitized basename.

    The per-file limit is enforced while reading, so an oversized upload
    is refused long before it could be fully buffered. The file lands
    first under a .part name and is moved into place only after a
    complete read, so an existing file is never left half-written.
    """
    safe = _safe_filename(filename)
    target = os.path.join(ws_path, safe)
    partial = target + ".part"
    written = 0
    try:
        with open(partial, "wb") as dst:
            while True:
                chunk = stream.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit:
                    raise UploadError(
                        "File exceeds the %s per-file limit." % _fmt_limit(limit)
                    )
                dst.write(chunk)
        os.replace(partial, target)
    except Exception:
        _discard(partial)
        raise
    return target


def extract_zip(
    ws_path: str,
    filename: str,
    data: bytes,
    limit: int = MAX_FILE_BYTES,
    total_limit: int = MAX_ZIP_TOTAL_BYTES,
) -> dict:
    """Extract a zip archive into the workspace with zip-slip protection.

    Expansion is capped twice: declared entry sizes are checked against
    the per-entry and total limits before extraction, and the actual
    bytes written are counted during the copy, so a lying header cannot
    bypass the total cap.
    """
    import io

    extracted = 0
    skipped = []
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            entries = [info for info in zf.infolist() if not info.is_dir()]
            if sum(info.file_size for info in entries) > total_limit:
                raise UploadError(
                    "Archive expands beyond the %s total extraction limit."
                    % _fmt_limit(total_limit)
                )
            for info in entries:
                if info.file_size > limit:
                    skipped.append(info.filename)
                    continue
                if total + info.file_size > total_limit:
                    raise UploadError(
                        "Archive expands beyond the %s total extraction limit."
                        % _fmt_limit(total_limit)
                    )
                target = _safe_member_path(ws_path, info.filename)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                partial = target + ".part"
                try:
                    with zf.open(info) as src, open(partial, "wb") as dst:
                        while True:
                            chunk = src.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            total += len(chunk)
                            if total > total_limit:
                                raise UploadError(
                                    "Archive expands beyond the %s total "
                                    "extraction limit." % _fmt_limit(total_limit)
                                )
                            dst.write(chunk)
                    os.replace(partial, target)
                except Exception:
                    _discard(partial)
                    raise
                extracted += 1
    except zipfile.BadZipFile as exc:
        raise UploadError("Not a valid zip archive: " + str(exc))
    return {
        "stored": os.path.basename(filename),
        "extracted": extracted,
        "skipped": skipped,
    }


def handle_upload(
    root: str, ws_name: str, filename: str, stream, settings=None
) -> dict:
    """Route one upload into the workspace; extracts zip, stores plain files.

    The upload itself creates the workspace when it does not exist yet
    (copy-first: the upload is the analysis copy). The file content is
    consumed as a stream with the size limit enforced while reading.
    When settings carry max_total_mb, the workspace root disk quota is
    enforced: zips get a shrunken total-expansion cap and a plain file
    that pushes usage past the cap is removed again.
    """
    ws_name = workspace.validate_name(ws_name)
    base = os.path.realpath(root)
    ws_path = os.path.realpath(os.path.join(base, ws_name))
    if ws_path != base and not ws_path.startswith(base + os.sep):
        raise workspace.WorkspaceError("Name escapes the workspace root.")
    if not os.path.isdir(ws_path):
        os.makedirs(ws_path, exist_ok=True)

    if (filename or "").lower().endswith(".zip"):
        data = read_limited(stream)
        _quota_gate(settings, root, incoming=len(data))
        result = extract_zip(
            ws_path, filename, data, total_limit=_zip_total_cap(settings, root)
        )
        action = "upload_extract"
    else:
        _quota_gate(settings, root, incoming=0)
        stored = store_plain_file(ws_path, filename, stream)
        _quota_after_store(settings, root, stored)
        result = {"stored": os.path.basename(stored), "extracted": 0, "skipped": []}
        action = "upload"

    state.add_history(root, {
        "action": action,
        "workspace": ws_name,
        "details": result["stored"],
    })
    return {"workspace": ws_name, **result}


def _quota_gate(settings, root: str, incoming: int) -> None:
    """Refuse before writing when usage (plus incoming) passes the cap."""
    if not settings:
        return
    try:
        quota.check(settings, root, incoming=incoming)
    except quota.QuotaExceeded as exc:
        raise UploadError(str(exc))


def _zip_total_cap(settings, root: str) -> int:
    """Shrink the zip total cap to the remaining quota headroom."""
    cap = quota.limit_bytes(settings or {})
    if cap is None:
        return MAX_ZIP_TOTAL_BYTES
    remaining = max(0, cap - quota.root_usage(root))
    return max(1024, min(MAX_ZIP_TOTAL_BYTES, remaining))


def _quota_after_store(settings, root: str, stored: str) -> None:
    """Post-check for plain files; removes the file when over the cap."""
    cap = quota.limit_bytes(settings or {})
    if cap is None:
        return
    if quota.root_usage(root) > cap:
        _discard(stored)
        raise UploadError(
            "Upload exceeds the workspace disk quota (max_total_mb setting)."
        )
