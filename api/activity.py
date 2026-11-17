"""API handler: live plugin activity for the sidebar indicator.

Route: /api/plugins/reverse_engineer_anything/activity
Returns what the plugin is doing right now (busy) and what it just
finished (done/error). Read-only.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import activity, state


class Activity(ApiHandler):
    """Report the latest plugin activity for the sidebar."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        # Read-only; keep auth but skip CSRF so sidebar polling works.
        return False

    async def process(self, input: Input, request: Request) -> Output:
        settings = state.load_settings()
        return activity.get_activity(settings["workspace_root"])
