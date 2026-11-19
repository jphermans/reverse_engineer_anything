import { createStore } from "/js/AlpineStore.js";
import { callJsonApi, fetchApi, getCsrfToken } from "/js/api.js";
import { getStore } from "/js/AlpineStore.js";
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
  uploadProgress: 0,
  historyFilter: "",
  fileWs: "", filePath: "", fileEntries: [], fileLoading: false,
  installBusy: false,
  installProgress: null,
  restoreMissing: [], restoreChecked: false,
  // live activity (sidebar indicator)
  activity: { status: "idle", action: "", detail: "", ts: "" },
  activityTimer: null,
  sidebarOpen: false,
  toolsWarned: false,

  init() {},
  startSidebar() {
    this.sidebarOpen = false;
    this.startActivityPolling();
    if (!this.loaded) this.loadTools();
  },

  stopSidebar() {
    this.sidebarOpen = false;
    this.stopActivityPolling();
  },

  onOpen() {
    this.refreshAll();
    this.checkRestore();
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
      this.warnMissingTools();
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
      const data = await callJsonApi(`${API}/history`, {
        workspace: (this.historyFilter || "").trim(),
      });
      this.history = data.entries || [];
      this.historyLimit = data.history_limit || 200;
    } catch (e) {
      toastFrontendError("Failed to load history: " + e.message, "Reverse Engineer Anything");
    }
  },

  async createWorkspace() {
    const name = (this.newWorkspaceName || "").trim();
    if (!name || this.busy) return;
    if (!this.wsNameValid(name)) {
      toastFrontendError(
        "Invalid name: use letters, digits, dot, dash or underscore (max 64, start with a letter or digit).",
        "Reverse Engineer Anything"
      );
      return;
    }
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
    if (!this.wsNameValid(name)) {
      toastFrontendError(
        "Invalid workspace name: use letters, digits, dot, dash or underscore (max 64, start with a letter or digit).",
        "Reverse Engineer Anything"
      );
      return;
    }
    const files = Array.from(fileList || []);
    if (!files.length) return;
    this.uploadBusy = true;
    try {
      const fd = new FormData();
      fd.append("workspace", name);
      for (const file of files) fd.append("files", file, file.name);
      this.uploadProgress = 0;
      const token = await getCsrfToken();
      const data = await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `/api${API}/upload`);
        xhr.setRequestHeader("X-CSRF-Token", token);
        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable) {
            this.uploadProgress = Math.round((ev.loaded / ev.total) * 100);
          }
        };
        xhr.onload = () => {
          try { resolve(JSON.parse(xhr.responseText || "{}")); }
          catch (e) { resolve({}); }
        };
        xhr.onerror = () => reject(new Error("network error"));
        xhr.send(fd);
      });
      this.uploadProgress = 100;
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

  wsNameValid(name) {
    return /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/.test((name || "").trim());
  },

  downloadUrl(ws, path) {
    return `/api${API}/files?action=download&workspace=${encodeURIComponent(ws)}` +
      `&path=${encodeURIComponent(path)}`;
  },

  async openFiles(ws) {
    this.fileWs = ws;
    this.filePath = "";
    this.fileEntries = [];
    await this.loadFiles();
  },

  async loadFiles() {
    if (!this.fileWs) return;
    this.fileLoading = true;
    try {
      const data = await callJsonApi(`${API}/files`, {
        action: "list",
        workspace: this.fileWs,
        path: this.filePath || "",
      });
      this.fileEntries = data.entries || [];
    } catch (e) {
      toastFrontendError("Failed to list files: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.fileLoading = false;
    }
  },

  async openDir(name) {
    this.filePath = this.filePath ? this.filePath + "/" + name : name;
    await this.loadFiles();
  },

  goUpDir() {
    const parts = this.filePath.split("/");
    parts.pop();
    this.filePath = parts.join("/");
    this.loadFiles();
  },

  closeFiles() {
    this.fileWs = "";
    this.filePath = "";
    this.fileEntries = [];
  },

  async planInstall(tools, label) {
    if (this.installBusy) return;
    this.installBusy = true;
    try {
      const data = await callJsonApi(`${API}/tools_install`, { action: "plan", tools });
      if (data.status !== "ok") {
        toastFrontendError(data.error || "Plan failed.", "Reverse Engineer Anything");
        return;
      }
      const packages = (data.plan && data.plan.packages) || [];
      const nonApt = (data.plan && data.plan.non_apt) || {};
      const extras = Object.keys(nonApt).map((t) => t + ": " + nonApt[t]);
      const msg = [
        "Install " + label + "?",
        "Packages: " + (packages.join(", ") || "(none)"),
        extras.length ? "Other: " + extras.join(", ") : "",
        "Download: " + data.download_human,
        "Disk: " + data.disk_human,
        data.command ? "Command: " + data.command : "",
      ].filter(Boolean).join("\n");
      if (!window.confirm(msg)) return;
      const res = await callJsonApi(`${API}/tools_install`, {
        action: "install", tools, confirm: true,
      });
      if (res.status !== "ok") {
        toastFrontendError(res.error || "Install failed.", "Reverse Engineer Anything");
        return;
      }
      toastFrontendSuccess("Installation started: " + label, "Reverse Engineer Anything");
      this.installProgress = { percent: 0, step: "Starting", elapsed: 0, log_tail: [] };
      this.pollInstallJob(res.job && res.job.id);
    } catch (e) {
      toastFrontendError("Install failed: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.installBusy = false;
    }
  },

  async pollInstallJob(jobId) {
    const delay = (ms) => new Promise((r) => setTimeout(r, ms));
    for (let i = 0; i < 600; i++) {
      await delay(3000);
      let data;
      try {
        data = await callJsonApi(`${API}/tools_install`, { action: "status", job_id: jobId });
      } catch (e) {
        continue;
      }
      const job = data.job;
      if (job && job.state === "running" && job.progress) {
        this.installProgress = {
          percent: job.progress.percent || 0,
          step: job.progress.step || "Working",
          steps_total: job.progress.steps_total || 0,
          step_index: job.progress.step_index || 0,
          elapsed: job.progress.elapsed || 0,
          log_tail: job.log_tail || [],
        };
      }
      if (!job) {
        if (data.interrupted) {
          this.installProgress = null;
          toastFrontendError(
            "Installation was interrupted by a server restart: " + (data.interrupted.tools || []).join(", "),
            "Reverse Engineer Anything"
          );
          return;
        }
        continue;
      }
      if (job.state === "done") {
        this.installProgress = null;
        toastFrontendSuccess("Installed: " + (job.tools || []).join(", "), "Reverse Engineer Anything");
        await this.loadTools();
        this.checkRestore();
        return;
      }
      if (job.state === "error") {
        this.installProgress = null;
        toastFrontendError("Install failed: " + (job.error || "unknown"), "Reverse Engineer Anything");
        await this.loadTools();
        return;
      }
    }
    toastFrontendError("Install timed out waiting for status.", "Reverse Engineer Anything");
  },

  async checkRestore() {
    if (this.restoreChecked) return;
    try {
      const st = await callJsonApi(`${API}/tools_install`, { action: "status" });
      if (st && st.interrupted && (st.interrupted.tools || []).length) {
        toastFrontendError(
          "A previous tool installation was interrupted by a restart: " + st.interrupted.tools.join(", ")
            + ". Install the tools again to restore them.",
          "Reverse Engineer Anything"
        );
      }
    } catch (e) { /* status endpoint unavailable; ignore */ }
    try {
      const data = await callJsonApi(`${API}/tools_install`, { action: "restore_status" });
      this.restoreMissing = data.missing || [];
      this.restoreChecked = true;
    } catch (e) {
      // Restore check stays silent on errors.
    }
  },

  async restoreTools() {
    const missing = this.restoreMissing.slice();
    if (!missing.length) return;
    await this.planInstall(missing, "previously installed tools: " + missing.join(", "));
  },

  analyzeWorkspace(ws) {
    try {
      const chat = getStore("chatInput");
      if (!chat) throw new Error("chat input store not found");
      chat.message =
        "Analyze the workspace " + ws + " with leanrea. Workspace path: " +
        (this.workspaceRoot || "").replace(/\/$/, "") + "/" + ws +
        ". Start with fast-path recon, work on evidence, and report findings.";
      toastFrontendSuccess(
        "Analysis prompt placed in the chat input. Review and send.",
        "Reverse Engineer Anything"
      );
    } catch (e) {
      toastFrontendError("Could not fill the chat input: " + e.message, "Reverse Engineer Anything");
    }
  },

  warnMissingTools() {
    if (this.toolsWarned) return;
    const missing = (this.summary && this.summary.missing) || [];
    if (!missing.length) return;
    this.toolsWarned = true;
    toastFrontendWarning(
      "Missing RE tools: " + missing.join(", ") +
      ". See the Tools tab for install commands (nothing is installed automatically).",
      "Reverse Engineer Anything"
    );
  },

  startActivityPolling() {
    if (this.activityTimer) return;
    this.pollActivity();
    this.activityTimer = setInterval(() => this.pollActivity(), 4000);
  },

  stopActivityPolling() {
    if (this.activityTimer) {
      clearInterval(this.activityTimer);
      this.activityTimer = null;
    }
  },

  async pollActivity() {
    try {
      const data = await callJsonApi(`${API}/activity`, {});
      this.activity = {
        status: data.status || "idle",
        action: data.action || "",
        detail: data.detail || "",
        ts: data.ts || "",
      };
    } catch (e) {
      // Sidebar indicator stays silent on polling errors.
    }
  },

  get activityVisible() {
    return this.sidebarOpen;
  },

  get activityStatusClass() {
    const s = this.activity && this.activity.status;
    if (s === "busy") return "busy";
    if (s === "done") return "done";
    if (s === "error") return "error";
    return "idle";
  },

  get activityLabel() {
    const a = this.activity || {};
    if (a.status === "busy") return "Working: " + (a.detail || a.action || "...");
    if (a.status === "done") return "Done: " + (a.detail || a.action || "");
    if (a.status === "error") return "Failed: " + (a.detail || a.action || "");
    return "Idle";
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

  formatElapsed(sec) {
    const s = Math.max(0, Math.floor(sec || 0));
    const m = Math.floor(s / 60);
    const h = Math.floor(m / 60);
    if (h > 0) return h + "h " + (m % 60) + "m";
    if (m > 0) return m + "m " + (s % 60) + "s";
    return s + "s";
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