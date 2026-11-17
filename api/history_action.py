"""API handler: history mutations.

Route: /api/plugins/reverse_engineer_anything/history_action
Actions: clear (confirm), remove (id), note (text, optional workspace).
CSRF stays on (default) because all actions mutate user data.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import activity, state


class HistoryAction(ApiHandler):
    """Clear, remove or append analysis history entries."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: Input, request: Request) -> Output:
        data = input if isinstance(input, dict) else {}
        action = str(data.get("action") or "").strip()
        settings = state.load_settings()
        root = settings["workspace_root"]
        try:
            if action == "clear":
                if not data.get("confirm"):
                    raise ValueError("Clearing requires confirmation (confirm=true).")
                activity.start(root, "history_clear", "all entries")
                removed = state.clear_history(root)
                activity.finish(root, "history_clear", f"{removed} entries cleared")
                return {"status": "ok", "action": "clear", "removed": removed}
            if action == "remove":
                entry_id = str(data.get("id") or "").strip()
                if not entry_id:
                    raise ValueError("Missing field: id.")
                ok = state.remove_entry(root, entry_id)
                activity.finish(
                    root,
                    "history_remove",
                    "entry removed" if ok else "entry not found",
                    ok=True,
                )
                return {"status": "ok", "action": "remove", "removed_entry": ok}
            if action == "note":
                text = str(data.get("text") or "").strip()
                if not text:
                    raise ValueError("Note is empty.")
                ws = str(data.get("workspace") or "").strip() or None
                activity.start(root, "note", (text[:60] + ("…" if len(text) > 60 else "")))
                entry = state.add_history(
                    root,
                    {"action": "note", "workspace": ws, "details": text[:500]},
                )
                activity.finish(
                    root,
                    "note",
                    "note saved" + (f" in {ws}" if ws else ""),
                )
                return {"status": "ok", "action": "note", "entry": entry}
            return {
                "status": "error",
                "error": "Unknown action: use clear, remove or note.",
            }
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}