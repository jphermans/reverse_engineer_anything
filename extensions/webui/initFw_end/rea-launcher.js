import { store } from "/plugins/reverse_engineer_anything/webui/rea-store.js";

// Floating REA launcher at the right edge of the chat area (v0.2.0).
// Replaces the sidebar indicator: keeps the left column clean and stays
// reachable on narrow screens, where the chat navigation buttons are always
// visible as well. Position mirrors #chat-nav-buttons (bottom-right) but sits
// top-right so the two never overlap.
export default function initReaLauncher() {
  if (document.getElementById("rea-launcher")) return;
  const wrapper = document.getElementById("chat-area-wrapper");
  if (!wrapper) return;

  const btn = document.createElement("button");
  btn.id = "rea-launcher";
  btn.type = "button";
  btn.title = "Reverse Engineer Anything";
  btn.setAttribute("aria-label", "Open the Reverse Engineer Anything workbench");

  const icon = document.createElement("x-icon");
  icon.setAttribute("name", "travel_explore");
  btn.appendChild(icon);

  btn.addEventListener("click", () => store.openWorkbench());
  wrapper.appendChild(btn);

  const style = document.createElement("style");
  style.textContent = `
    #rea-launcher {
      position: absolute;
      top: calc(72px + env(safe-area-inset-top, 0px));
      right: calc(var(--spacing-md) + env(safe-area-inset-right, 0px));
      z-index: 100;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 44px;
      min-height: 44px;
      padding: var(--spacing-xs);
      border: none;
      border-radius: 50%;
      background: var(--color-panel);
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
      cursor: pointer;
      color: inherit;
      opacity: 0.85;
      transition: opacity 0.2s ease;
    }
    #rea-launcher:hover { opacity: 1; }
    /* The top bar (time-date-container) spans the top-right corner at every
       width and sits above this button, so keep the launcher below the bar
       to stay reachable on all screen sizes. On desktop widths the vertical
       canvas rail occupies the right edge, so shift the launcher left of it. */
    @media (min-width: 769px) {
      #rea-launcher { right: 60px; }
    }
  `;
  document.head.appendChild(style);
}
