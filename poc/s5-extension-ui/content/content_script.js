/**
 * content_script.js - YouTube Page Injection & Overlay Coordinator for Stage S5.
 */

import { SubtitleRenderer } from './subtitle_renderer.js';
import { SubtitleStateAdapter } from './subtitle_adapter.js';

let renderer = null;
let adapter = null;
let observer = null;

function findYouTubePlayer() {
  return document.querySelector('#movie_player') ||
         document.querySelector('.html5-video-player') ||
         document.querySelector('video')?.parentElement ||
         document.body;
}

function initializeOverlay() {
  const mountTarget = findYouTubePlayer();
  if (!mountTarget) return;

  if (!renderer) {
    renderer = new SubtitleRenderer(mountTarget);
    adapter = new SubtitleStateAdapter(renderer, {
      enableCoalescing: true,
      logTelemetry: true
    });
  } else {
    renderer.mount(mountTarget);
  }
}

// Listen for messages from background service worker
if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!adapter) {
      initializeOverlay();
    }

    if (message.type === 'SUBTITLE_EVENT') {
      const accepted = adapter.processMessage(message.payload);
      sendResponse({ success: accepted });
    } else if (message.type === 'CLEAR_SUBTITLES') {
      if (adapter) adapter.reset();
      sendResponse({ success: true });
    } else if (message.type === 'GET_RENDERER_TELEMETRY') {
      const telemetry = adapter ? adapter.getTelemetry() : {};
      sendResponse({ success: true, telemetry });
    }
    return true;
  });
}

// Watch for YouTube SPA player re-creation
if (typeof MutationObserver !== 'undefined') {
  observer = new MutationObserver(() => {
    const player = findYouTubePlayer();
    if (player && renderer && renderer.container !== player) {
      renderer.mount(player);
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

// Initial mount attempt
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeOverlay);
} else {
  initializeOverlay();
}
