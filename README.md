# Reverse Engineer Anything (Agent Zero plugin)

![Version](https://img.shields.io/badge/version-v0.2.1-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Agent%20Zero-orange)

Agent Zero plugin v0.2.1: the workbench for reverse engineering with the leanrea method.

## Based on leanrea

This plugin is built on [leanrea](https://github.com/aicodeking/leanrea), the skill that gives the agent the reverse engineering method (route by magic bytes, work on a copy, slice instead of reading, answer from evidence). The tool inventory categories and the copy-first workspaces follow the leanrea router and rules directly.

## What does this plugin do?

The [leanrea skill](https://github.com/aicodeking/leanrea) gives the agent the *method* to reverse engineer software. This plugin provides the *workplace* in the Agent Zero WebUI:

1. **Tool inventory** - live overview of reverse engineering tools in the container, grouped per leanrea category (basic, native binaries, Electron/JS, mobile, firmware, WASM, data/network, Go/Rust/.NET, decompilers). Per tool: available or not, what it does, and a proposed install command when missing.
2. **Workspaces** - managed analysis directories under one root (default `/a0/usr/workdir/rea`), following the leanrea rule: always work on a copy. Create and delete from the WebUI; names are validated and stay inside the root.
3. **History** - log of workspace actions and notes (JSONL in the workspace root), with a limit setting and separate delete actions.

**Missing tools are proposed, never auto-installed.** The inventory is read-only: it never downloads or installs anything on its own. Every missing tool shows a proposed install command (for example `apt-get install file`), and when an analysis actually needs that tool the agent proposes running it and waits for your approval. Manually installed tools do not survive a pod recreation; the inventory will flag them as missing again.

The plugin adds no analysis capability; the agent runs the analysis itself with the leanrea skill and the tools in the container. The plugin makes the work visible, repeatable and cleanable.

## Installation

Copy the plugin directory to `/a0/usr/plugins/reverse_engineer_anything/` (or install via zip/git in the Plugins screen). Once loaded, the **Reverse Engineer Anything** workbench opens from the vertical canvas rail on the right edge of the screen, next to Files, Swarm, Harness and Jev Router. On narrow screens (769 px and below) the rail is hidden and a floating button below the top bar opens the same workbench. The workbench is responsive down to phone widths.

The plugin has no external dependencies, no credentials and no background processes. `install()` only creates the default workspace root; with a custom root that happens automatically on first use.

## Settings (Settings > Developer)

| Setting | Default | Meaning |
|---|---|---|
| `workspace_root` | `/a0/usr/workdir/rea` | Directory where workspaces are created |
| `history_limit` | `200` (10-2000) | Maximum number of retained history entries |

## API

| Route | Method | Function |
|---|---|---|
| `/api/plugins/reverse_engineer_anything/tools` | GET/POST | Tool inventory per category (read-only) |
| `/api/plugins/reverse_engineer_anything/workspaces` | GET/POST | Workspace listing (read-only) |
| `/api/plugins/reverse_engineer_anything/workspace` | POST | `create` (name) or `delete` (name + confirm) |
| `/api/plugins/reverse_engineer_anything/history` | GET/POST | History listing (read-only) |
| `/api/plugins/reverse_engineer_anything/history_action` | POST | `note` (text, workspace?), `remove` (id), `clear` (confirm) |
| `/api/plugins/reverse_engineer_anything/upload` | POST | Multipart upload (`workspace` + `files`); zips are extracted into the workspace |

Mutation routes use the standard Agent Zero CSRF policy; read-only routes allow GET polling.

## Using it with the agent

Example prompt for an analysis job:

> Analyze this app with leanrea. Use a workspace `myapp-v1` (create it if it does not exist) and put all your extractions there; log important findings as notes in the REA history.

The agent can also call the API routes itself to update the workbench, and consult the tool inventory before choosing an approach.

## Uninstall

Remove the plugin via the Plugins screen. The workspace root (with workspaces and history) deliberately survives: that is user data. Delete `/a0/usr/workdir/rea` yourself if you no longer need it.

## Uploading files

Open the workbench (canvas rail on desktop, floating button on narrow screens), go to the **Workspaces** tab:

1. Type the workspace name to upload into (for example `app-v1`); it is created automatically on first upload.
2. Click **Upload** and select one or more files.
3. A folder does not upload directly: zip it first (for example `myapp.zip`). Zips are extracted automatically into the workspace, so the original folder structure is preserved.
4. The upload is the analysis copy; the original on your computer is never touched. Then ask the agent in chat to analyze that workspace with leanrea.

## Versions

| Label | Release | Highlights |
|---|---|---|
| `v0.1.0` | Initial release | Tool inventory, workspaces, history, WebUI workbench (modal) |
| `v0.2.0` | Upload feature | Upload files/zips into workspaces with zip-slip protection, floating launcher button |
| `v0.2.1` | Canvas rail | Workbench as right-canvas surface next to Files, Swarm, Harness and Jev Router; floating button now mobile-only; A0 plugin badges |

Tags are published in the repository for every release (`git tag` / GitHub releases list).

## License

MIT - see [LICENSE](LICENSE).
