let mediaStream = null;
let audioContext = null;
let workletNode = null;
let recordedChunks = [];
let totalBytesCaptured = 0;
let totalSamplesCaptured = 0;
let lastTelemetrySend = 0;
let wsClient = null;
let isRecording = false;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'OFFSCREEN_START_CAPTURE') {
    startTabAudioCapture(message.streamId, message.enableWs, message.wsUrl);
  } else if (message.type === 'OFFSCREEN_STOP_CAPTURE') {
    stopTabAudioCapture();
  } else if (message.type === 'DOWNLOAD_RECORDING') {
    exportRecording(message.format || 'wav');
  }
});

async function startTabAudioCapture(streamId, enableWs, wsUrl) {
  try {
    recordedChunks = [];
    totalBytesCaptured = 0;
    totalSamplesCaptured = 0;
    isRecording = true;

    if (enableWs && wsUrl) {
      initWebSocket(wsUrl);
    }

    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      },
      video: false
    });

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === 'suspended') {
      await audioContext.resume();
    }

    const source = audioContext.createMediaStreamSource(mediaStream);

    // Audio passthrough: retain audible output for the user while capturing
    source.connect(audioContext.destination);

    try {
      await audioContext.audioWorklet.addModule('audio-processor.js');
      workletNode = new AudioWorkletNode(audioContext, 'downsampler-processor', {
        processorOptions: {
          targetSampleRate: 16000,
          bufferSize: 2048
        }
      });

      workletNode.port.onmessage = (event) => {
        if (!isRecording) return;
        const data = event.data;
        if (data.type === 'PCM_CHUNK') {
          handlePcmChunk(data);
        }
      };

      source.connect(workletNode);
    } catch (workletError) {
      setupScriptProcessorFallback(source);
    }

  } catch (error) {
    chrome.runtime.sendMessage({
      type: 'CAPTURE_ERROR',
      error: error.message
    }).catch(() => {});
  }
}

function handlePcmChunk(data) {
  const chunkBuffer = data.pcm16;
  recordedChunks.push(chunkBuffer);
  totalBytesCaptured += chunkBuffer.byteLength;
  totalSamplesCaptured += data.samplesCount;

  if (wsClient && wsClient.readyState === WebSocket.OPEN) {
    wsClient.send(chunkBuffer);
  }

  const now = Date.now();
  if (now - lastTelemetrySend > 100) {
    lastTelemetrySend = now;
    chrome.runtime.sendMessage({
      type: 'TELEMETRY_UPDATE',
      metrics: {
        samplesRecorded: totalSamplesCaptured,
        bytesRecorded: totalBytesCaptured,
        rmsLevel: data.rms,
        dbfs: data.dbfs,
        nativeSampleRate: audioContext ? audioContext.sampleRate : 0,
        wsConnected: wsClient ? (wsClient.readyState === WebSocket.OPEN) : false
      }
    }).catch(() => {});
  }
}

function setupScriptProcessorFallback(source) {
  const bufferSize = 4096;
  const scriptNode = audioContext.createScriptProcessor(bufferSize, 2, 1);
  const ratio = audioContext.sampleRate / 16000;

  scriptNode.onaudioprocess = (audioProcessingEvent) => {
    if (!isRecording) return;
    const inputBuffer = audioProcessingEvent.inputBuffer;
    const ch0 = inputBuffer.getChannelData(0);
    const ch1 = inputBuffer.numberOfChannels > 1 ? inputBuffer.getChannelData(1) : null;
    const inputLen = ch0.length;

    const outputLen = Math.floor(inputLen / ratio);
    const pcm16 = new Int16Array(outputLen);
    let sumSquares = 0;

    for (let i = 0; i < outputLen; i++) {
      const srcIdx = Math.min(Math.floor(i * ratio), inputLen - 1);
      let s = ch1 ? (ch0[srcIdx] + ch1[srcIdx]) * 0.5 : ch0[srcIdx];
      s = Math.max(-1.0, Math.min(1.0, s));
      sumSquares += s * s;
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }

    const rms = Math.sqrt(sumSquares / outputLen);
    handlePcmChunk({
      pcm16: pcm16.buffer,
      samplesCount: outputLen,
      rms: rms,
      dbfs: rms > 0 ? 20 * Math.log10(rms) : -100
    });
  };

  source.connect(scriptNode);
  scriptNode.connect(audioContext.destination);
}

function initWebSocket(wsUrl) {
  try {
    wsClient = new WebSocket(wsUrl);
    wsClient.binaryType = 'arraybuffer';
  } catch (e) {
    wsClient = null;
  }
}

function stopTabAudioCapture() {
  isRecording = false;

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  if (workletNode) {
    workletNode.disconnect();
    workletNode = null;
  }

  if (audioContext && audioContext.state !== 'closed') {
    audioContext.close();
    audioContext = null;
  }

  if (wsClient) {
    wsClient.close();
    wsClient = null;
  }

  chrome.runtime.sendMessage({
    type: 'CAPTURE_STOPPED',
    totalBytes: totalBytesCaptured,
    totalSamples: totalSamplesCaptured
  }).catch(() => {});
}

function exportRecording(format) {
  if (recordedChunks.length === 0) {
    return;
  }

  let blob;
  let filename;
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

  if (format === 'wav') {
    blob = encodeWav(recordedChunks, 16000, 1, 16);
    filename = `youtube_captured_16k_${timestamp}.wav`;
  } else {
    blob = new Blob(recordedChunks, { type: 'application/octet-stream' });
    filename = `youtube_captured_16k_mono_${timestamp}.pcm`;
  }

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
