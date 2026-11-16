"""API handler: workspace mutations.

Route: /api/plugins/reverse_engineer_anything/workspace
Actions: create (name), delete (name + confirm). CSRF stays on (default).
Workspace names are validated and confined to the configured root.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import state, workspace


class Workspace(ApiHandler):
    """Create or delete an analysis workspace."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: Input, request: Request) -> Output:
        data = input if isinstance(input, dict) else {}
        action = str(data.get("action") or "").strip()
        settings = state.load_settings()
        root = settings["workspace_root"]
        try:
            if action == "create":
                result = workspace.create_workspace(root, data.get("name"))
                return {"status": "ok", "action": "create", **result}
            if action == "delete":
                result = workspace.delete_workspace(
                    root, data.get("name"), bool(data.get("confirm"))
                )
                return {"status": "ok", "action": "delete", **result}
            return {"status": "error", "error": "Onbekende actie: gebruik create of delete."}
        except workspace.WorkspaceError as exc:
            return {"status": "error", "error": str(exc)}