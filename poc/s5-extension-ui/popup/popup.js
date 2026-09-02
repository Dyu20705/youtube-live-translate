/**
 * popup.js - Controls for starting/stopping Live Translation.
 */

document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('toggleBtn');
  const statusBadge = document.getElementById('statusBadge');
  const runtimeState = document.getElementById('runtimeState');
  const audioDuration = document.getElementById('audioDuration');
  const subtitlesCount = document.getElementById('subtitlesCount');
  const bridgeUrl = document.getElementById('bridgeUrl');

  let isCapturing = false;
  let updateInterval = null;

  async function refreshStatus() {
    chrome.runtime.sendMessage({ type: 'GET_STATUS' }, (response) => {
      if (response && response.success && response.state) {
        const state = response.state;
        isCapturing = state.isCapturing;
        
        statusBadge.textContent = state.status || (isCapturing ? 'RUNNING' : 'READY');
        statusBadge.className = 'badge ' + (state.status ? state.status.toLowerCase() : (isCapturing ? 'running' : ''));

        runtimeState.textContent = isCapturing ? 'Streaming Active' : 'Ready';
        
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

  toggleBtn.addEventListener('click', async () => {
    if (!isCapturing) {
      // Get current active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab) return;

      const wsUrlVal = bridgeUrl.value || 'ws://127.0.0.1:8765';
      chrome.runtime.sendMessage({
        type: 'START_CAPTURE',
        tabId: tab.id,
        tabTitle: tab.title,
        wsUrl: wsUrlVal
      }, (resp) => {
        refreshStatus();
      });
    } else {
      chrome.runtime.sendMessage({ type: 'STOP_CAPTURE' }, () => {
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
