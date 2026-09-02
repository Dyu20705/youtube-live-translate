document.addEventListener('DOMContentLoaded', async () => {
  const statusBadge = document.getElementById('statusBadge');
  const statusText = document.getElementById('statusText');
  const tabTitle = document.getElementById('tabTitle');
  const tabWarning = document.getElementById('tabWarning');
  const meterBar = document.getElementById('meterBar');
  const dbfsValue = document.getElementById('dbfsValue');
  const durationVal = document.getElementById('durationVal');
  const sizeVal = document.getElementById('sizeVal');
  const samplesVal = document.getElementById('samplesVal');
  const btnStart = document.getElementById('btnStart');
  const btnStop = document.getElementById('btnStop');
  const btnDownloadWav = document.getElementById('btnDownloadWav');
  const btnDownloadPcm = document.getElementById('btnDownloadPcm');
  const chkWsStream = document.getElementById('chkWsStream');
  const txtWsUrl = document.getElementById('txtWsUrl');

  let activeTab = null;
  let pollInterval = null;

  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs.length > 0) {
      activeTab = tabs[0];
      tabTitle.textContent = activeTab.title || 'Untitled Tab';

      const isYouTube = activeTab.url && (activeTab.url.includes('youtube.com') || activeTab.url.includes('youtu.be'));
      if (!isYouTube) {
        tabWarning.classList.remove('hidden');
        tabWarning.textContent = 'Not a YouTube tab. Capture works on active YouTube streams.';
      } else {
        tabWarning.classList.add('hidden');
      }
    }
  } catch (e) {
    tabTitle.textContent = 'Could not inspect tab';
  }

  async function refreshStatus() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });
      if (response && response.success && response.state) {
        updateUI(response.state);
      }
    } catch (e) {}
  }

  function updateUI(state) {
    if (state.isCapturing) {
      statusBadge.className = 'status-indicator capturing';
      statusText.textContent = 'CAPTURING';
      btnStart.classList.add('hidden');
      btnStop.classList.remove('hidden');
      btnDownloadWav.disabled = true;
      btnDownloadPcm.disabled = true;

      const metrics = state.metrics || {};
      const durationSec = Math.floor((metrics.durationMs || 0) / 1000);
      const hrs = String(Math.floor(durationSec / 3600)).padStart(2, '0');
      const mins = String(Math.floor((durationSec % 3600) / 60)).padStart(2, '0');
      const secs = String(durationSec % 60).padStart(2, '0');
      durationVal.textContent = `${hrs}:${mins}:${secs}`;

      const bytes = metrics.bytesRecorded || 0;
      sizeVal.textContent = bytes > 1048576 
        ? `${(bytes / 1048576).toFixed(2)} MB` 
        : `${(bytes / 1024).toFixed(1)} KB`;

      samplesVal.textContent = (metrics.samplesRecorded || 0).toLocaleString();

      const dbfs = metrics.dbfs != null ? metrics.dbfs : -100;
      if (dbfs <= -90) {
        meterBar.style.width = '0%';
        dbfsValue.textContent = '-∞ dBFS';
      } else {
        const pct = Math.max(0, Math.min(100, ((dbfs + 60) / 60) * 100));
        meterBar.style.width = `${pct.toFixed(1)}%`;
        dbfsValue.textContent = `${dbfs.toFixed(1)} dBFS`;
      }
    } else {
      statusBadge.className = 'status-indicator idle';
      statusText.textContent = 'IDLE';
      btnStart.classList.remove('hidden');
      btnStop.classList.add('hidden');

      const bytes = (state.metrics && state.metrics.bytesRecorded) || 0;
      if (bytes > 0) {
        btnDownloadWav.disabled = false;
        btnDownloadPcm.disabled = false;
      }

      meterBar.style.width = '0%';
      dbfsValue.textContent = 'IDLE';
    }
  }

  btnStart.addEventListener('click', async () => {
    if (!activeTab) return;
    btnStart.disabled = true;

    const enableWs = chkWsStream.checked;
    const wsUrl = txtWsUrl.value.trim();

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'START_CAPTURE',
        tabId: activeTab.id,
        tabTitle: activeTab.title,
        enableWs: enableWs,
        wsUrl: wsUrl
      });

      if (!response.success) {
        alert('Failed to start capture: ' + (response.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Error communicating with extension background: ' + err.message);
    } finally {
      btnStart.disabled = false;
      refreshStatus();
    }
  });

  btnStop.addEventListener('click', async () => {
    btnStop.disabled = true;
    try {
      await chrome.runtime.sendMessage({ type: 'STOP_CAPTURE' });
    } catch (err) {
    } finally {
      btnStop.disabled = false;
      refreshStatus();
    }
  });

  btnDownloadWav.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'DOWNLOAD_RECORDING', format: 'wav' });
  });

  btnDownloadPcm.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'DOWNLOAD_RECORDING', format: 'pcm' });
  });

  refreshStatus();
  pollInterval = setInterval(refreshStatus, 150);

  window.addEventListener('unload', () => {
    if (pollInterval) clearInterval(pollInterval);
  });
});
