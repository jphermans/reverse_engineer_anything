"""API handler: workspace listing.

Route: /api/plugins/reverse_engineer_anything/workspaces
Returns analysis workspaces under the configured root. Read-only.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import state, workspace


class Workspaces(ApiHandler):
    """List analysis workspaces."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: Input, request: Request) -> Output:
        settings = state.load_settings()
        root = settings["workspace_root"]
        return {
            "workspace_root": root,
            "workspaces": workspace.list_workspaces(root),
        }