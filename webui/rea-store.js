import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";
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
      toastFrontendError("Tool-inventaris ophalen mislukt: " + e.message, "Reverse Engineer Anything");
    }
  },

  async loadWorkspaces() {
    try {
      const data = await callJsonApi(`${API}/workspaces`, {});
      this.workspaces = data.workspaces || [];
      this.workspaceRoot = data.workspace_root || "";
    } catch (e) {
      toastFrontendError("Werkruimtes ophalen mislukt: " + e.message, "Reverse Engineer Anything");
    }
  },

  async loadHistory() {
    try {
      const data = await callJsonApi(`${API}/history`, {});
      this.history = data.entries || [];
      this.historyLimit = data.history_limit || 200;
    } catch (e) {
      toastFrontendError("Historiek ophalen mislukt: " + e.message, "Reverse Engineer Anything");
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
        toastFrontendSuccess(`Werkruimte '${name}' aangemaakt.`, "Reverse Engineer Anything");
        await Promise.all([this.loadWorkspaces(), this.loadHistory()]);
      } else {
        toastFrontendError(res.error || "Aanmaken mislukt.", "Reverse Engineer Anything");
      }
    } catch (e) {
      toastFrontendError("Aanmaken mislukt: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
    }
  },

  async deleteWorkspace(name) {
    if (this.busy) return;
    if (!window.confirm(`Werkruimte '${name}' echt verwijderen? Alle bestanden in deze werkruimte gaan verloren.`)) return;
    this.busy = true;
    try {
      const res = await callJsonApi(`${API}/workspace`, { action: "delete", name, confirm: true });
      if (res.status === "ok") {
        toastFrontendSuccess(`Werkruimte '${name}' verwijderd.`, "Reverse Engineer Anything");
        await Promise.all([this.loadWorkspaces(), this.loadHistory()]);
      } else {
        toastFrontendError(res.error || "Verwijderen mislukt.", "Reverse Engineer Anything");
      }
    } catch (e) {
      toastFrontendError("Verwijderen mislukt: " + e.message, "Reverse Engineer Anything");
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
        toastFrontendError(res.error || "Notitie opslaan mislukt.", "Reverse Engineer Anything");
      }
    } catch (e) {
      toastFrontendError("Notitie opslaan mislukt: " + e.message, "Reverse Engineer Anything");
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
      toastFrontendError("Verwijderen mislukt: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
    }
  },

  async clearHistory() {
    if (this.busy) return;
    if (!window.confirm("De volledige analysehistoriek wissen?")) return;
    this.busy = true;
    try {
      await callJsonApi(`${API}/history_action`, { action: "clear", confirm: true });
      await this.loadHistory();
    } catch (e) {
      toastFrontendError("Wissen mislukt: " + e.message, "Reverse Engineer Anything");
    } finally {
      this.busy = false;
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
          else toastFrontendError("Modal openen niet beschikbaar.", "Reverse Engineer Anything");
        })
        .catch(() => toastFrontendError("Modal openen mislukt.", "Reverse Engineer Anything"));
    }
  },
});