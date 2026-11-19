"""Disk quota for the workspace root (pure logic).

Enforces the optional max_total_mb setting at upload time and during zip
expansion. 0 or missing disables the limit.
"""

import os


def root_usage(root):
    """Total bytes of all files under root (best effort)."""
    total = 0
    if not os.path.isdir(root):
        return 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, filename))
            except OSError:
                pass
    return total


def limit_bytes(settings):
    """Return the quota in bytes, or None when disabled."""
    try:
        mb = int(settings.get("max_total_mb") or 0)
    except (TypeError, ValueError):
        return None
    if mb <= 0:
        return None
    return mb * 1000 * 1000


def check(settings, root, incoming=0):
    """Raise QuotaExceeded when adding incoming bytes would pass the limit."""
    cap = limit_bytes(settings)
    if cap is None:
        return
    used = root_usage(root)
    if used + max(0, incoming) > cap:
        raise QuotaExceeded(
            "Workspace root is full: %d of %d bytes used; refusing %d more. "
            "Delete workspaces or raise max_total_mb in settings."
            % (used, cap, max(0, incoming))
        )


class QuotaExceeded(Exception):
    """Raised when an operation would exceed max_total_mb."""
