"""API handler: on-demand RE tool installation (explicit approval only).

Route: /api/plugins/reverse_engineer_anything/tools_install
Actions (POST, CSRF on):
- plan     {tools: [..]} or {bundle: name}: validate against the whitelist
           and estimate download/disk sizes via apt-get simulation. Read-only.
- install  same request + confirm=true: start the apt install in the
           background. Never starts without the explicit confirm flag.
- status   {job_id?}: poll the running/last job.
- restore_status: which approved tools are missing after a pod replacement.

Nothing is ever installed automatically: the UI shows the plan (package
names, download size, disk size, exact command) and the user approves it.
"""

import asyncio

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import (
    job_markers,
    state,
    tool_install,
    tool_state,
    tools_inventory,
)


class ToolsInstall(ApiHandler):
    """Plan, approve and monitor RE tool installations."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: Input, request: Request) -> Output:
        data = input if isinstance(input, dict) else {}
        action = str(data.get("action") or "").strip()
        settings = state.load_settings()
        root = settings["workspace_root"]

        if action == "plan":
            tools, error = _resolve_request(data)
            if error:
                return {"status": "error", "error": error}
            # Run the apt simulation in a worker thread; a blocking call
            # here froze the whole event loop (and with it the WebUI).
            payload = await asyncio.to_thread(tool_install.plan_payload, root, tools)
            payload["status"] = "ok"
            return payload

        if action == "install":
            if not data.get("confirm"):
                return {
                    "status": "error",
                    "error": "Installation requires confirmation (confirm=true) after showing the plan.",
                }
            tools, error = _resolve_request(data)
            if error:
                return {"status": "error", "error": error}
            if tool_install.busy():
                return {
                    "status": "error",
                    "error": "Another installation is already running; try again when it finishes.",
                }
            planned = await asyncio.to_thread(tool_install.plan_payload, root, tools)
            invalid = planned["plan"]["invalid"]
            if invalid:
                return {
                    "status": "error",
                    "error": "Not installable through the plugin: " + ", ".join(invalid),
                }
            job = tool_install.start(
                root,
                planned["plan"]["valid"],
                planned["plan"]["packages"],
                planned["plan"]["non_apt"],
            )
            if job is None:
                return {
                    "status": "error",
                    "error": "Another installation is already running; try again when it finishes.",
                }
            return {
                "status": "ok",
                "job": {
                    "id": job["id"],
                    "state": job["state"],
                    "tools": job["tools"],
                    "packages": job["packages"],
                },
            }

        if action == "status":
            job = tool_install.get_job(str(data.get("job_id") or ""))
            result = {"status": "ok", "job": None}
            if job is None:
                # No in-memory job. A pod replacement kills running jobs;
                # surface the persisted marker so the loss is explicit.
                interrupted = job_markers.read(root)
                if interrupted:
                    result["interrupted"] = {"tools": interrupted["tools"]}
                return result
            import time as _time

            result["job"] = {
                "id": job["id"],
                "state": job["state"],
                "tools": job["tools"],
                "packages": job["packages"],
                "error": job["error"],
                "log_tail": job["log"][-8:],
                "progress": {
                    "percent": job.get("step_percent", 100 if job["state"] == "done" else 0),
                    "step": job.get("step_label", ""),
                    "step_index": job.get("step_index", 0),
                    "steps_total": len(job.get("steps") or []),
                    "elapsed": int(_time.time() - job.get("started", _time.time())),
                },
            }
            return result

        if action == "restore_status":
            inventory = tools_inventory.build_inventory()
            available = {
                entry["name"]
                for cat in inventory["categories"]
                for entry in cat["tools"]
                if entry["available"]
            }
            result = tool_state.restore_names(root, available)
            return {"status": "ok", **result}

        return {
            "status": "error",
            "error": "Unknown action: use plan, install, status or restore_status.",
        }


def _resolve_request(data):
    """Accept either a tools list or a bundle name; returns (tools, error)."""
    from usr.plugins.reverse_engineer_anything.helpers import installer

    bundle = str(data.get("bundle") or "").strip()
    if bundle:
        tools = installer.bundle_tools(bundle)
        if tools is None:
            return None, "Unknown bundle: " + bundle
        return list(tools), None
    tools = data.get("tools")
    if isinstance(tools, str):
        tools = [tools]
    if not isinstance(tools, list) or not tools:
        return None, "Missing field: tools (list) or bundle."
    return [str(t) for t in tools], None
