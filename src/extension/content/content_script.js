/**
 * content_script.js - YouTube Page Injection & Overlay Coordinator.
 * Handles SPA navigation, ad transitions, player recreation, and subtitle rendering.
 */

import { SubtitleRenderer } from './subtitle_renderer.js';
import { SubtitleStateAdapter } from './subtitle_adapter.js';

let renderer = null;
let adapter = null;
let observer = null;
let currentVideoId = null;

function findYouTubePlayer() {
  return document.querySelector('#movie_player') ||
         document.querySelector('.html5-video-player') ||
         document.querySelector('video')?.parentElement ||
         document.body;
}

function getVideoIdFromUrl() {
  try {
    const url = new URL(window.location.href);
    if (url.pathname.startsWith('/watch')) {
      return url.searchParams.get('v');
    }
    if (url.pathname.startsWith('/live/')) {
      return url.pathname.split('/live/')[1]?.split('?')[0];
    }
  } catch (e) {}
  return null;
}

function loadSavedSettings() {
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(['fontSize', 'bottomOffset', 'provisionalOpacity'], (res) => {
      if (renderer && res) {
        renderer.applySettings(res);
      }
    });
  }
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
    loadSavedSettings();
  } else {
    renderer.mount(mountTarget);
    loadSavedSettings();
  }
}

function handleNavigation() {
  const newVideoId = getVideoIdFromUrl();
  if (newVideoId !== currentVideoId) {
    currentVideoId = newVideoId;
    if (adapter) {
      adapter.reset();
    }
    initializeOverlay();
  }
}

// Listen for messages from background service worker
if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!adapter) {
      initializeOverlay();
    }

    if (message.type === 'SUBTITLE_EVENT') {
      // Check if YouTube ad is currently active
      const player = findYouTubePlayer();
      const isAd = player && (player.classList.contains('ad-showing') || player.classList.contains('ad-interrupting'));
      if (isAd) {
        // Suppress subtitle overlay display during advertisements
        if (renderer) renderer.clear();
        sendResponse({ success: true, suppressed: 'ad' });
        return true;
      }

      const accepted = adapter.processMessage(message.payload);
      sendResponse({ success: accepted });
    } else if (message.type === 'CLEAR_SUBTITLES') {
      if (adapter) adapter.reset();
      sendResponse({ success: true });
    } else if (message.type === 'APPLY_SETTINGS') {
      if (renderer) renderer.applySettings(message.settings);
      sendResponse({ success: true });
    } else if (message.type === 'GET_RENDERER_TELEMETRY') {
      const telemetry = adapter ? adapter.getTelemetry() : {};
      sendResponse({ success: true, telemetry });
    }
    return true;
  });
}

// Watch for YouTube SPA navigation events
window.addEventListener('yt-navigate-finish', handleNavigation);
window.addEventListener('yt-page-data-updated', handleNavigation);
window.addEventListener('popstate', handleNavigation);

// Watch for YouTube SPA player re-creation and DOM mutations
if (typeof MutationObserver !== 'undefined') {
  observer = new MutationObserver(() => {
    const player = findYouTubePlayer();
    if (player && renderer && renderer.container !== player) {
      renderer.mount(player);
      loadSavedSettings();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

// Initial mount attempt
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    currentVideoId = getVideoIdFromUrl();
    initializeOverlay();
  });
} else {
  currentVideoId = getVideoIdFromUrl();
  initializeOverlay();
}
