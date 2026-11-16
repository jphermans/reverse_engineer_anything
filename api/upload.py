"""API handler: file uploads into analysis workspaces.

Route: /api/plugins/reverse_engineer_anything/upload
Multipart formdata: field 'workspace' (target name) + one or more 'files'.
ZIP archives are extracted into the workspace (zip-slip protected); plain
files are stored under their sanitized basename. CSRF stays on (default):
the browser adds the X-CSRF-Token header via fetchApi.
"""

from helpers.api import ApiHandler, Input, Output, Request

from usr.plugins.reverse_engineer_anything.helpers import state, upload, workspace


class Upload(ApiHandler):
    """Upload analysis targets into a workspace (copy-first)."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: Input, request: Request) -> Output:
        # Multipart formdata arrives with empty JSON input; read the request.
        try:
            ws_name = str(request.form.get("workspace") or "").strip()
            files = request.files.getlist("files")
        except Exception:
            return {
                "status": "error",
                "error": "Expected multipart formdata with fields 'workspace' and 'files'.",
            }

        if not ws_name:
            return {"status": "error", "error": "Missing workspace name."}
        if not files:
            return {"status": "error", "error": "No files received (use field name 'files')."}

        settings = state.load_settings()
        root = settings["workspace_root"]

        uploads = []
        had_error = False
        for fs in files:
            try:
                result = upload.handle_upload(root, ws_name, fs.filename, fs.read())
                uploads.append({"filename": fs.filename, "status": "ok", **result})
            except (workspace.WorkspaceError, upload.UploadError) as exc:
                had_error = True
                uploads.append({"filename": fs.filename, "status": "error", "error": str(exc)})

        return {
            "status": "error" if had_error else "ok",
            "workspace": ws_name,
            "uploads": uploads,
        }
