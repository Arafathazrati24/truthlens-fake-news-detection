/**
 * TruthLens — background.js
 * =========================
 * Service worker. Handles installation,
 * context menu, and cross-component messaging.
 */

// ── Install ───────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(details => {
  if (details.reason === 'install') {
    chrome.storage.local.set({ apiUrl: 'http://localhost:8000', useExplain: true });
  }

  // Right-click context menu
  chrome.contextMenus.create({
    id      : 'tl-check',
    title   : '🔍 Check with TruthLens',
    contexts: ['selection', 'page']
  });
});

// ── Context menu ──────────────────────────────────────────────
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== 'tl-check') return;
  if (info.selectionText) {
    chrome.storage.local.set({
      pendingText  : info.selectionText,
      pendingSource: 'selection'
    });
  } else {
    chrome.storage.local.set({ pendingText: null, pendingSource: 'page' });
  }
});

// ── Messages ──────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'textSelected') {
    chrome.storage.local.set({ lastSelected: msg.text });
  }
  return true;
});
