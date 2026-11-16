"""API handler: history mutations.

Route: /api/plugins/reverse_engineer_anything/history_action
Actions: clear (confirm), remove (id), note (text, optional workspace).
CSRF stays on (default) because all actions mutate user data.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import state


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
                    raise ValueError("Wissen vereist bevestiging (confirm=true).")
                removed = state.clear_history(root)
                return {"status": "ok", "action": "clear", "removed": removed}
            if action == "remove":
                entry_id = str(data.get("id") or "").strip()
                if not entry_id:
                    raise ValueError("Ontbrekend veld: id.")
                ok = state.remove_entry(root, entry_id)
                return {"status": "ok", "action": "remove", "removed_entry": ok}
            if action == "note":
                text = str(data.get("text") or "").strip()
                if not text:
                    raise ValueError("Notitie is leeg.")
                ws = str(data.get("workspace") or "").strip() or None
                entry = state.add_history(
                    root,
                    {"action": "note", "workspace": ws, "details": text[:500]},
                )
                return {"status": "ok", "action": "note", "entry": entry}
            return {
                "status": "error",
                "error": "Onbekende actie: gebruik clear, remove of note.",
            }
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}