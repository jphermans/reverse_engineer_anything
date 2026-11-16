"""API handler: leanrea tool inventory.

Route: /api/plugins/reverse_engineer_anything/tools
Returns the categorized tool availability for this container. Read-only.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import tools_inventory


class Tools(ApiHandler):
    """Report available reverse engineering tools per category."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    @classmethod
    def requires_csrf(cls) -> bool:
        # Read-only inventory; keep auth but skip CSRF so GET polling works.
        return False

    async def process(self, input: Input, request: Request) -> Output:
        return tools_inventory.build_inventory()