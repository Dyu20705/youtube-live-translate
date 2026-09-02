const OFFSCREEN_DOCUMENT_PATH = 'offscreen.html';

let captureState = {
  isCapturing: false,
  tabId: null,
  tabTitle: '',
  startTime: null,
  metrics: {
    durationMs: 0,
    samplesRecorded: 0,
    bytesRecorded: 0,
    rmsLevel: 0,
    underrunCount: 0,
    wsConnected: false
  }
};

async function hasOffscreenDocument() {
  if ('getContexts' in chrome.runtime) {
    const contexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT'],
      documentUrls: [chrome.runtime.getURL(OFFSCREEN_DOCUMENT_PATH)]
    });
    return contexts.length > 0;
  }
  const matchedClients = await clients.matchAll();
  return matchedClients.some(client => client.url.includes(OFFSCREEN_DOCUMENT_PATH));
}

async function ensureOffscreenDocument() {
  if (await hasOffscreenDocument()) {
    return;
  }

  await chrome.offscreen.createDocument({
    url: OFFSCREEN_DOCUMENT_PATH,
    reasons: [chrome.offscreen.Reason.USER_MEDIA || 'USER_MEDIA'],
    justification: 'Capturing live YouTube tab audio for local 16kHz PCM speech recognition processing.'
  });
}

async function closeOffscreenDocument() {
  if (await hasOffscreenDocument()) {
    await chrome.offscreen.closeDocument();
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const handleAsync = async () => {
    switch (message.type) {
      case 'START_CAPTURE': {
        try {
          const tabId = message.tabId;
          const tabTitle = message.tabTitle || 'YouTube Tab';
          const enableWs = message.enableWs || false;
          const wsUrl = message.wsUrl || 'ws://localhost:8765';

          const streamId = await chrome.tabCapture.getMediaStreamId({
            targetTabId: tabId
          });

          await ensureOffscreenDocument();

          chrome.runtime.sendMessage({
            type: 'OFFSCREEN_START_CAPTURE',
            streamId: streamId,
            tabId: tabId,
            enableWs: enableWs,
            wsUrl: wsUrl
          });

          captureState.isCapturing = true;
          captureState.tabId = tabId;
          captureState.tabTitle = tabTitle;
          captureState.startTime = Date.now();

          return { success: true };
        } catch (error) {
          captureState.isCapturing = false;
          return { success: false, error: error.message };
        }
      }

      case 'STOP_CAPTURE': {
        try {
          if (await hasOffscreenDocument()) {
            chrome.runtime.sendMessage({ type: 'OFFSCREEN_STOP_CAPTURE' });
          }
          captureState.isCapturing = false;
          return { success: true };
        } catch (error) {
          return { success: false, error: error.message };
        }
      }

      case 'GET_STATUS': {
        return {
          success: true,
          state: captureState
        };
      }

      case 'TELEMETRY_UPDATE': {
        if (captureState.isCapturing) {
          captureState.metrics = {
            ...captureState.metrics,
            ...message.metrics,
            durationMs: captureState.startTime ? (Date.now() - captureState.startTime) : 0
          };
        }
        return { success: true };
      }

      case 'CAPTURE_STOPPED': {
        captureState.isCapturing = false;
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
  if (captureState.isCapturing && captureState.tabId === tabId) {
    captureState.isCapturing = false;
    chrome.runtime.sendMessage({ type: 'OFFSCREEN_STOP_CAPTURE' }).catch(() => {});
  }
});
