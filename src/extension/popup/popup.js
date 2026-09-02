/**
 * popup.js - Controller for YouTube Live Translate Popup.
 */

document.addEventListener('DOMContentLoaded', async () => {
  const toggleBtn = document.getElementById('toggleBtn');
  const statusBadge = document.getElementById('statusBadge');
  const runtimeState = document.getElementById('runtimeState');
  const audioDuration = document.getElementById('audioDuration');
  const subtitlesCount = document.getElementById('subtitlesCount');
  const tabNotice = document.getElementById('tabNotice');

  // Settings elements
  const fontSizeSelect = document.getElementById('fontSizeSelect');
  const bottomOffsetRange = document.getElementById('bottomOffsetRange');
  const offsetVal = document.getElementById('offsetVal');
  const opacitySelect = document.getElementById('opacitySelect');

  // Diagnostics elements
  const transportSelect = document.getElementById('transportSelect');
  const wsField = document.getElementById('wsField');
  const bridgeUrl = document.getElementById('bridgeUrl');

  let isCapturing = false;
  let isYouTubeTab = false;
  let activeTab = null;
  let updateInterval = null;

  // 1. Detect Active Tab
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    activeTab = tab;
    if (tab && tab.url && (tab.url.includes('youtube.com/watch') || tab.url.includes('youtube.com/live'))) {
      isYouTubeTab = true;
      tabNotice.style.display = 'none';
      toggleBtn.disabled = false;
    } else {
      isYouTubeTab = false;
      tabNotice.style.display = 'block';
    }
  } catch (e) {
    console.warn('Tab detection error:', e);
  }

  // 2. Load Persisted Settings
  chrome.storage.local.get(['fontSize', 'bottomOffset', 'provisionalOpacity', 'transportType', 'wsUrl'], (res) => {
    if (res) {
      if (res.fontSize) fontSizeSelect.value = res.fontSize;
      if (res.bottomOffset) {
        bottomOffsetRange.value = res.bottomOffset;
        offsetVal.textContent = res.bottomOffset;
      }
      if (res.provisionalOpacity) opacitySelect.value = String(res.provisionalOpacity);
      if (res.transportType) {
        transportSelect.value = res.transportType;
        wsField.style.display = res.transportType === 'websocket' ? 'flex' : 'none';
      }
      if (res.wsUrl) bridgeUrl.value = res.wsUrl;
    }
  });

  // 3. Settings Event Listeners
  function saveAndApplySettings() {
    const settings = {
      fontSize: fontSizeSelect.value,
      bottomOffset: Number(bottomOffsetRange.value),
      provisionalOpacity: Number(opacitySelect.value),
      transportType: transportSelect.value,
      wsUrl: bridgeUrl.value
    };
    chrome.storage.local.set(settings);

    // Notify active tab content script
    if (activeTab && activeTab.id) {
      chrome.tabs.sendMessage(activeTab.id, {
        type: 'APPLY_SETTINGS',
        settings: settings
      }).catch(() => {});
    }
  }

  fontSizeSelect.addEventListener('change', saveAndApplySettings);
  bottomOffsetRange.addEventListener('input', () => {
    offsetVal.textContent = bottomOffsetRange.value;
    saveAndApplySettings();
  });
  opacitySelect.addEventListener('change', saveAndApplySettings);

  transportSelect.addEventListener('change', () => {
    wsField.style.display = transportSelect.value === 'websocket' ? 'flex' : 'none';
    saveAndApplySettings();
  });
  bridgeUrl.addEventListener('change', saveAndApplySettings);

  // 4. Refresh Runtime Status
  async function refreshStatus() {
    chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
      if (response && response.success && response.state) {
        const state = response.state;
        isCapturing = state.isCapturing;

        const currentStatus = state.status || (isCapturing ? 'RUNNING' : 'READY');
        statusBadge.textContent = currentStatus;
        statusBadge.className = 'badge ' + currentStatus.toLowerCase();

        if (state.status === 'NOT_INSTALLED') {
          runtimeState.textContent = 'Runtime Not Installed';
          statusBadge.className = 'badge badge-error';
        } else if (state.status === 'ERROR') {
          runtimeState.textContent = state.errorMessage || 'Runtime Error';
        } else if (state.status === 'DEGRADED') {
          runtimeState.textContent = 'Degraded (Reconnecting)';
        } else {
          runtimeState.textContent = isCapturing ? 'Streaming Active' : 'Local AI (Ready)';
        }

        const durSec = (state.metrics.durationMs / 1000).toFixed(1);
        audioDuration.textContent = `${durSec}s`;
        subtitlesCount.textContent = state.metrics.subtitlesReceived || 0;

        if (isCapturing) {
          toggleBtn.textContent = 'Stop Live Translation';
          toggleBtn.className = 'btn btn-stop';
        } else {
          toggleBtn.textContent = 'Start Live Translation';
          toggleBtn.className = 'btn btn-primary';
        }
      }
    });
  }

  // 5. Toggle Live Translation
  toggleBtn.addEventListener('click', async () => {
    if (!isCapturing) {
      if (!activeTab || !activeTab.id) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        activeTab = tab;
      }
      if (!activeTab) return;

      const currentTransport = transportSelect.value || 'native';
      const currentWsUrl = bridgeUrl.value || 'ws://127.0.0.1:8765';

      toggleBtn.disabled = true;
      chrome.runtime.sendMessage({
        type: 'START_CAPTURE',
        tabId: activeTab.id,
        tabTitle: activeTab.title,
        transportType: currentTransport,
        wsUrl: currentWsUrl
      }, (resp) => {
        toggleBtn.disabled = false;
        refreshStatus();
      });
    } else {
      toggleBtn.disabled = true;
      chrome.runtime.sendMessage({ type: 'STOP_CAPTURE' }, () => {
        toggleBtn.disabled = false;
        refreshStatus();
      });
    }
  });

  refreshStatus();
  updateInterval = setInterval(refreshStatus, 500);

  window.addEventListener('unload', () => {
    if (updateInterval) clearInterval(updateInterval);
  });
});
