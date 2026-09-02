/**
 * offscreen.js - Offscreen document capturing audio and streaming PCM to background.
 */

let mediaStream = null;
let audioContext = null;
let workletNode = null;
let recordedChunks = [];
let totalBytesCaptured = 0;
let totalSamplesCaptured = 0;
let lastTelemetrySend = 0;
let isRecording = false;

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'OFFSCREEN_START_CAPTURE') {
    startTabAudioCapture(message.streamId);
  } else if (message.type === 'OFFSCREEN_STOP_CAPTURE') {
    stopTabAudioCapture();
  }
});

async function startTabAudioCapture(streamId) {
  try {
    recordedChunks = [];
    totalBytesCaptured = 0;
    totalSamplesCaptured = 0;
    isRecording = true;

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
    source.connect(audioContext.destination); // Keep audible to user

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

  // Send PCM chunk to background service worker
  chrome.runtime.sendMessage({
    type: 'AUDIO_PCM_CHUNK',
    pcmBuffer: chunkBuffer,
    samplesCount: data.samplesCount,
    rms: data.rms
  }).catch(() => {});

  const now = Date.now();
  if (now - lastTelemetrySend > 150) {
    lastTelemetrySend = now;
    chrome.runtime.sendMessage({
      type: 'TELEMETRY_UPDATE',
      metrics: {
        samplesRecorded: totalSamplesCaptured,
        bytesRecorded: totalBytesCaptured,
        rmsLevel: data.rms,
        dbfs: data.dbfs
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
  chrome.runtime.sendMessage({
    type: 'CAPTURE_STOPPED',
    totalBytes: totalBytesCaptured
  }).catch(() => {});
}
