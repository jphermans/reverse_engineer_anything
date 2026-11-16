import { store } from "/plugins/reverse_engineer_anything/webui/rea-store.js";

function waitForElement(selector, timeoutMs = 10000) {
  const found = document.querySelector(selector);
  if (found) return Promise.resolve(found);
  return new Promise((resolve) => {
    const timeout = globalThis.setTimeout(() => {
      observer.disconnect();
      resolve(document.querySelector(selector));
    }, timeoutMs);
    const observer = new MutationObserver(() => {
      const element = document.querySelector(selector);
      if (!element) return;
      globalThis.clearTimeout(timeout);
      observer.disconnect();
      resolve(element);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
}

// Register the REA workbench as a right-canvas surface (v0.2.1).
// Order 50 puts the icon after Jev Router (45) in the canvas rail.
export default async function registerReaSurface(surfaces) {
  surfaces.registerSurface({
    id: "rea",
    title: "Reverse Engineer Anything",
    icon: "travel_explore",
    order: 50,
    modalPath: "/plugins/reverse_engineer_anything/webui/rea-panel.html",
    async open() {
      await waitForElement('[data-surface-id="rea"] .rea-workbench');
      await store.onOpen();
    },
    async close() {
      store.cleanup();
    },
  });
}
