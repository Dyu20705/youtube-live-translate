/**
 * background.js - Stage S5 Service Worker.
 * Coordinates audio capture, bridge transport, and subtitle event routing.
 */

const OFFSCREEN_DOCUMENT_PATH = 'offscreen.html';

let runtimeState = {
  isCapturing: false,
  tabId: null,
  tabTitle: '',
  startTime: null,
  transportType: 'websocket', // 'websocket' or 'native'
  wsUrl: 'ws://127.0.0.1:8765',
  nativeHostName: 'com.duy.youtube_live_translate',
  status: 'READY',
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
        broadcastStatusToContentScript('RUNNING');
      };

      wsSocket.onmessage = (event) => {
        if (typeof event.data === 'string') {
          handleIncomingSubtitleMessage(event.data);
        }
      };

      wsSocket.onclose = () => {
        runtimeState.metrics.wsConnected = false;
        runtimeState.status = runtimeState.isCapturing ? 'DEGRADED' : 'STOPPED';
        broadcastStatusToContentScript(runtimeState.status);
      };

      wsSocket.onerror = (err) => {
        runtimeState.metrics.wsConnected = false;
        runtimeState.status = 'ERROR';
        broadcastStatusToContentScript('ERROR', 'WebSocket bridge unreachable');
      };
    } catch (e) {
      runtimeState.status = 'ERROR';
    }
  } else if (runtimeState.transportType === 'native') {
    try {
      nativePort = chrome.runtime.connectNative(runtimeState.nativeHostName);
      nativePort.onMessage.addListener((msg) => {
        handleIncomingSubtitleMessage(msg);
      });
      nativePort.onDisconnect.addListener(() => {
        runtimeState.status = 'DEGRADED';
        broadcastStatusToContentScript('DEGRADED', 'Native host disconnected');
      });
      runtimeState.status = 'RUNNING';
    } catch (e) {
      runtimeState.status = 'ERROR';
    }
  }
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

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const handleAsync = async () => {
    switch (message.type) {
      case 'START_CAPTURE': {
        try {
          const tabId = message.tabId;
          const tabTitle = message.tabTitle || 'YouTube Tab';
          runtimeState.transportType = message.transportType || 'websocket';
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
          runtimeState.tabId = tabId;
          runtimeState.tabTitle = tabTitle;
          runtimeState.startTime = Date.now();

          return { success: true };
        } catch (error) {
          runtimeState.isCapturing = false;
          runtimeState.status = 'ERROR';
          return { success: false, error: error.message };
        }
      }

      case 'STOP_CAPTURE': {
        try {
          if (await hasOffscreenDocument()) {
            chrome.runtime.sendMessage({ type: 'OFFSCREEN_STOP_CAPTURE' });
          }
          if (wsSocket) {
            wsSocket.close();
            wsSocket = null;
          }
          if (nativePort) {
            nativePort.disconnect();
            nativePort = null;
          }
          runtimeState.isCapturing = false;
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
        // Forward chunk to bridge
        if (wsSocket && wsSocket.readyState === WebSocket.OPEN) {
          wsSocket.send(message.pcmBuffer);
        } else if (nativePort) {
          // Send base64 or array
          nativePort.postMessage({
            type: 'audio_chunk',
            data: message.pcmHex
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
    chrome.runtime.sendMessage({ type: 'OFFSCREEN_STOP_CAPTURE' }).catch(() => {});
  }
});
