"""API handler: analysis history listing.

Route: /api/plugins/reverse_engineer_anything/history
Returns recent history entries (JSONL file under the workspace root). Read-only.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import state


class History(ApiHandler):
    """List recent analysis history entries."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: Input, request: Request) -> Output:
        settings = state.load_settings()
        entries = state.list_history(
            settings["workspace_root"], settings["history_limit"]
        )
        ws_filter = str(
            input.get("workspace") or request.args.get("workspace") or ""
        ).strip()
        if ws_filter:
            entries = [
                e for e in entries
                if str(e.get("workspace") or "") == ws_filter
            ]
        return {
            "entries": entries,
            "history_limit": settings["history_limit"],
            "workspace_root": settings["workspace_root"],
            "filter": ws_filter,
        }