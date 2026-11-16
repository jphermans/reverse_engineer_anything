import { createStore } from "/js/AlpineStore.js";
import { callJsonApi, fetchApi } from "/js/api.js";
import {
  toastFrontendError,
  toastFrontendSuccess,
} from "/components/notifications/notification-store.js";

const API = "/plugins/reverse_engineer_anything";

export const store = createStore("reaStore", {
  loaded: false,
  busy: false,
  // tools
  categories: [],
  summary: { available: 0, total: 0, missing: [] },
  // workspaces
  workspaceRoot: "",
  workspaces: [],
  newWorkspaceName: "",
  // history
  history: [],
  historyLimit: 200,
  noteText: "",
  noteWorkspace: "",
  // uploads
  uploadWorkspace: "",
  uploadBusy: false,

  init() {},

  onOpen() {
    this.refreshAll();
  },

  cleanup() {},

  async refreshAll() {
    this.busy = true;
    try {
      await Promise.all([this.loadTools(), this.loadWorkspaces(), this.loadHistory()]);
      this.loaded = true;
    } finally {
      this.busy = false;
    }
  },

  async loadTools() {
    try {
      const data = await callJsonApi(`${API}/tools`, {});
      this.categories = data.categories || [];
      this.summary = data.summary || { available: 0, total: 0, missing: [] };
    } catch (e) {
      toastFrontendError("Failed to load tool inventory: " + e.message, "Reverse Engineer Anything");
    }
  },

  async loadWorkspaces() {
    try {
      const data = await callJsonApi(`${API}/workspaces`, {});
      this.workspaces = data.workspaces || [];
      this.workspaceRoot = data.workspace_root || "";
    } catch (e) {
      toastFrontendError("Failed to load workspaces: " + e.message, "Reverse Engineer Anything");
    }
  },

  async loadHistory() {
    try {
      const data = await callJsonApi(`${API}/history`, {});
      this.history = data.entries || [];
      this.historyLimit = data.history_limit || 200;
    } catch (e) {
      toastFrontendError("Failed to load history: " + e.message, "Reverse Engineer Anything");
    }
  },

  async createWorkspace() {
    const name = (this.newWorkspaceName || "").trim();
    if (!name || this.busy) return;
    this.busy = true;
    try {
      const res = await callJsonApi(`${API}/workspace`, { action: "create", name });
      if (res.status === "ok") {
        this.newWorkspaceName = "";
        toastFrontendSuccess(`Workspace '${name}' created.`, "Reverse Engineer Anything");
        await Promise.all([this.loadWorkspaces(), this.loadHistory()]);
      } else {
        toastFrontendError(res.error || "Create failed.", "Reverse Engineer Anything");
      }
    } catch (e) {
      toastFrontendError("Create failed: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
    }
  },

  async deleteWorkspace(name) {
    if (this.busy) return;
    if (!window.confirm(`Really delete workspace '${name}'? All files in this workspace will be lost.`)) return;
    this.busy = true;
    try {
      const res = await callJsonApi(`${API}/workspace`, { action: "delete", name, confirm: true });
      if (res.status === "ok") {
        toastFrontendSuccess(`Workspace '${name}' deleted.`, "Reverse Engineer Anything");
        await Promise.all([this.loadWorkspaces(), this.loadHistory()]);
      } else {
        toastFrontendError(res.error || "Delete failed.", "Reverse Engineer Anything");
      }
    } catch (e) {
      toastFrontendError("Delete failed: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
    }
  },

  async addNote() {
    const text = (this.noteText || "").trim();
    if (!text || this.busy) return;
    this.busy = true;
    try {
      const res = await callJsonApi(`${API}/history_action`, {
        action: "note",
        text,
        workspace: (this.noteWorkspace || "").trim() || null,
      });
      if (res.status === "ok") {
        this.noteText = "";
        await this.loadHistory();
      } else {
        toastFrontendError(res.error || "Failed to save note.", "Reverse Engineer Anything");
      }
    } catch (e) {
      toastFrontendError("Failed to save note: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
    }
  },

  async removeEntry(id) {
    if (this.busy) return;
    this.busy = true;
    try {
      await callJsonApi(`${API}/history_action`, { action: "remove", id });
      await this.loadHistory();
    } catch (e) {
      toastFrontendError("Delete failed: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
    }
  },

  async clearHistory() {
    if (this.busy) return;
    if (!window.confirm("Clear the entire analysis history?")) return;
    this.busy = true;
    try {
      await callJsonApi(`${API}/history_action`, { action: "clear", confirm: true });
      await this.loadHistory();
    } catch (e) {
      toastFrontendError("Clear failed: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
    }
  },

  async uploadFiles(fileList) {
    if (this.uploadBusy) return;
    const name = (this.uploadWorkspace || "").trim();
    if (!name) {
      toastFrontendError("Enter a workspace name for the upload first.", "Reverse Engineer Anything");
      return;
    }
    const files = Array.from(fileList || []);
    if (!files.length) return;
    this.uploadBusy = true;
    try {
      const fd = new FormData();
      fd.append("workspace", name);
      for (const file of files) fd.append("files", file, file.name);
      const res = await fetchApi(`${API}/upload`, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      const failed = (data.uploads || []).filter((u) => u.status === "error");
      if (data.status === "ok" && !failed.length) {
        const parts = (data.uploads || []).map(
          (u) => u.filename + (u.extracted ? ` (extracted ${u.extracted} files)` : "")
        );
        toastFrontendSuccess(
          "Uploaded into '" + name + "': " + parts.join(", "),
          "Reverse Engineer Anything"
        );
      } else {
        const msg = (failed[0] && failed[0].error) || data.error || "Upload failed.";
        toastFrontendError(msg, "Reverse Engineer Anything");
      }
      await Promise.all([this.loadWorkspaces(), this.loadHistory()]);
    } catch (e) {
      toastFrontendError("Upload failed: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.uploadBusy = false;
    }
  },

  get toolLabel() {
    const s = this.summary || {};
    return `${s.available ?? 0}/${s.total ?? 0}`;
  },

  get toolClass() {
    const missing = (this.summary && this.summary.missing) || [];
    if (!this.loaded) return "loading";
    return missing.length === 0 ? "ok" : "warn";
  },

  formatBytes(n) {
    if (!Number.isFinite(n)) return "";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  },

  openWorkbench() {
    const url = "/plugins/reverse_engineer_anything/webui/rea-modal.html";
    if (typeof window.openModal === "function") {
      window.openModal(url);
    } else {
      import("/js/modals.js")
        .then((m) => {
          const fn = m.openModal || m.default;
          if (typeof fn === "function") fn(url);
          else toastFrontendError("Opening modals is not available.", "Reverse Engineer Anything");
        })
        .catch(() => toastFrontendError("Failed to open modal.", "Reverse Engineer Anything"));
    }
  },
});