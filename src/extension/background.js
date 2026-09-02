/**
 * background.js - Production Service Worker for YouTube Live Translate.
 * Manages tab audio capture, Native Messaging / WebSocket transport, and subtitle event routing.
 */

const OFFSCREEN_DOCUMENT_PATH = 'offscreen.html';
const NATIVE_HOST_NAME = 'com.duy.youtube_live_translate';

let runtimeState = {
  isCapturing: false,
  isStarting: false,
  tabId: null,
  tabTitle: '',
  startTime: null,
  transportType: 'native', // Canonical default is 'native'
  wsUrl: 'ws://127.0.0.1:8765',
  status: 'READY', // 'NOT_INSTALLED' | 'READY' | 'STARTING' | 'RUNNING' | 'DEGRADED' | 'RECOVERING' | 'STOPPED' | 'ERROR'
  errorMessage: '',
  metrics: {
    durationMs: 0,
    samplesRecorded: 0,
    bytesRecorded: 0,
    rmsLevel: 0,
    wsConnected: false,
    subtitlesReceived: 0
  }
};

let wsSocket = null;
let nativePort = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 3;

async function hasOffscreenDocument() {
  if ('getContexts' in chrome.runtime) {
    const contexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT'],
      documentUrls: [chrome.runtime.getURL(OFFSCREEN_DOCUMENT_PATH)]
    });
    return contexts.length > 0;
  }
  return false;
}

async function ensureOffscreenDocument() {
  if (await hasOffscreenDocument()) return;
  await chrome.offscreen.createDocument({
    url: OFFSCREEN_DOCUMENT_PATH,
    reasons: [chrome.offscreen.Reason.USER_MEDIA || 'USER_MEDIA'],
    justification: 'Capturing live YouTube tab audio for local 16kHz PCM speech translation.'
  });
}

function initBridgeConnection() {
  if (runtimeState.transportType === 'websocket') {
    try {
      wsSocket = new WebSocket(runtimeState.wsUrl);
      wsSocket.binaryType = 'arraybuffer';

      wsSocket.onopen = () => {
        runtimeState.metrics.wsConnected = true;
        runtimeState.status = 'RUNNING';
        runtimeState.errorMessage = '';
        reconnectAttempts = 0;
        broadcastStatusToContentScript('RUNNING');
      };

      wsSocket.onmessage = (event) => {
        if (typeof event.data === 'string') {
          handleIncomingSubtitleMessage(event.data);
        }
      };

      wsSocket.onclose = () => {
        runtimeState.metrics.wsConnected = false;
        if (runtimeState.isCapturing) {
          handleBridgeDisconnection('WebSocket connection closed');
        } else {
          runtimeState.status = 'STOPPED';
          broadcastStatusToContentScript('STOPPED');
        }
      };

      wsSocket.onerror = (err) => {
        runtimeState.metrics.wsConnected = false;
        runtimeState.status = 'ERROR';
        runtimeState.errorMessage = 'WebSocket bridge unreachable';
        broadcastStatusToContentScript('ERROR', runtimeState.errorMessage);
      };
    } catch (e) {
      runtimeState.status = 'ERROR';
      runtimeState.errorMessage = e.message;
    }
  } else {
    // Canonical default: Chrome Native Messaging
    try {
      nativePort = chrome.runtime.connectNative(NATIVE_HOST_NAME);

      nativePort.onMessage.addListener((msg) => {
        if (msg.type === 'error') {
          handleIncomingErrorMessage(msg);
        } else {
          handleIncomingSubtitleMessage(msg);
        }
      });

      nativePort.onDisconnect.addListener(() => {
        const lastError = chrome.runtime.lastError;
        const errDetail = lastError ? lastError.message : 'Native host disconnected';
        console.warn('[NativeHost Disconnected]', errDetail);

        if (errDetail.includes('not found') || errDetail.includes('specified native messaging host not found')) {
          runtimeState.status = 'NOT_INSTALLED';
          runtimeState.errorMessage = 'Local runtime is not installed. Please run install.sh.';
          broadcastStatusToContentScript('ERROR', runtimeState.errorMessage);
        } else if (runtimeState.isCapturing) {
          handleBridgeDisconnection(errDetail);
        } else {
          runtimeState.status = 'STOPPED';
        }
        nativePort = null;
      });

      runtimeState.status = 'RUNNING';
      runtimeState.errorMessage = '';
      reconnectAttempts = 0;
    } catch (e) {
      runtimeState.status = 'NOT_INSTALLED';
      runtimeState.errorMessage = 'Failed to connect to local native host';
    }
  }
}

function handleBridgeDisconnection(reason) {
  if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
    reconnectAttempts++;
    runtimeState.status = 'RECOVERING';
    broadcastStatusToContentScript('DEGRADED', `Reconnecting to runtime (Attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);

    setTimeout(() => {
      if (runtimeState.isCapturing) {
        initBridgeConnection();
      }
    }, reconnectAttempts * 1500);
  } else {
    runtimeState.status = 'DEGRADED';
    runtimeState.errorMessage = `Runtime disconnected: ${reason}`;
    broadcastStatusToContentScript('DEGRADED', runtimeState.errorMessage);
  }
}

function handleIncomingErrorMessage(errMsg) {
  const code = errMsg.error_code || 'GENERIC_ERROR';
  let userMsg = errMsg.message || 'Translation runtime error';

  if (code === 'MODEL_MISSING') {
    userMsg = 'Translation model is missing or corrupt. Run model manager to download.';
    runtimeState.status = 'ERROR';
  } else if (code === 'INIT_FAILED') {
    userMsg = 'Engine initialization failed on local machine.';
    runtimeState.status = 'ERROR';
  }

  runtimeState.errorMessage = userMsg;
  broadcastStatusToContentScript('ERROR', userMsg);
}

function handleIncomingSubtitleMessage(rawMsg) {
  runtimeState.metrics.subtitlesReceived += 1;

  // Broadcast to content script in the active capturing tab
  if (runtimeState.tabId) {
    chrome.tabs.sendMessage(runtimeState.tabId, {
      type: 'SUBTITLE_EVENT',
      payload: rawMsg
    }).catch(() => {});
  }
}

function broadcastStatusToContentScript(state, message = '') {
  if (runtimeState.tabId) {
    chrome.tabs.sendMessage(runtimeState.tabId, {
      type: 'SUBTITLE_EVENT',
      payload: {
        version: '1.0',
        type: 'status',
        state: state,
        message: message,
        timestamp_ms: Date.now()
      }
    }).catch(() => {});
  }
}

function cleanupSession() {
  if (wsSocket) {
    try { wsSocket.close(); } catch (e) {}
    wsSocket = null;
  }
  if (nativePort) {
    try {
      nativePort.postMessage({ type: 'control.stop' });
      nativePort.disconnect();
    } catch (e) {}
    nativePort = null;
  }
  reconnectAttempts = 0;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const handleAsync = async () => {
    switch (message.type) {
      case 'START_CAPTURE': {
        if (runtimeState.isStarting || runtimeState.isCapturing) {
          return { success: false, error: 'Capture already active or starting' };
        }

        try {
          runtimeState.isStarting = true;
          const tabId = message.tabId;
          const tabTitle = message.tabTitle || 'YouTube Tab';
          runtimeState.transportType = message.transportType || 'native';
          runtimeState.wsUrl = message.wsUrl || 'ws://127.0.0.1:8765';

          const streamId = await chrome.tabCapture.getMediaStreamId({
            targetTabId: tabId
          });

          await ensureOffscreenDocument();
          initBridgeConnection();

          chrome.runtime.sendMessage({
            type: 'OFFSCREEN_START_CAPTURE',
            streamId: streamId,
            tabId: tabId
          });

          runtimeState.isCapturing = true;
          runtimeState.isStarting = false;
          runtimeState.tabId = tabId;
          runtimeState.tabTitle = tabTitle;
          runtimeState.startTime = Date.now();

          return { success: true };
        } catch (error) {
          runtimeState.isStarting = false;
          runtimeState.isCapturing = false;
          runtimeState.status = 'ERROR';
          runtimeState.errorMessage = error.message;
          cleanupSession();
          return { success: false, error: error.message };
        }
      }

      case 'STOP_CAPTURE': {
        try {
          if (await hasOffscreenDocument()) {
            chrome.runtime.sendMessage({ type: 'OFFSCREEN_STOP_CAPTURE' });
          }
          cleanupSession();
          runtimeState.isCapturing = false;
          runtimeState.isStarting = false;
          runtimeState.status = 'STOPPED';

          if (runtimeState.tabId) {
            chrome.tabs.sendMessage(runtimeState.tabId, { type: 'CLEAR_SUBTITLES' }).catch(() => {});
          }

          return { success: true };
        } catch (error) {
          return { success: false, error: error.message };
        }
      }

      case 'GET_STATUS': {
        return {
          success: true,
          state: runtimeState
        };
      }

      case 'TELEMETRY_UPDATE': {
        if (runtimeState.isCapturing) {
          runtimeState.metrics = {
            ...runtimeState.metrics,
            ...message.metrics,
            durationMs: runtimeState.startTime ? (Date.now() - runtimeState.startTime) : 0
          };
        }
        return { success: true };
      }

      case 'AUDIO_PCM_CHUNK': {
        // Forward chunk to active bridge
        if (wsSocket && wsSocket.readyState === WebSocket.OPEN) {
          wsSocket.send(message.pcmBuffer);
        } else if (nativePort) {
          // Native messaging expects JSON payload with base64 / hex audio data
          nativePort.postMessage({
            type: 'audio_chunk',
            data: message.pcmBase64 || message.pcmHex || ''
          });
        }
        return { success: true };
      }

      case 'CAPTURE_STOPPED': {
        runtimeState.isCapturing = false;
        runtimeState.status = 'STOPPED';
        return { success: true };
      }

      default:
        return { success: false, error: 'Unknown message type' };
    }
  };

  handleAsync().then(sendResponse);
  return true;
});

chrome.tabs.onRemoved.addListener((tabId) => {
  if (runtimeState.isCapturing && runtimeState.tabId === tabId) {
    runtimeState.isCapturing = false;
    cleanupSession();
    chrome.runtime.sendMessage({ type: 'OFFSCREEN_STOP_CAPTURE' }).catch(() => {});
  }
});
