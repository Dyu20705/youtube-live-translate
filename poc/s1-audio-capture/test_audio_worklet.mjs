/**
 * test_audio_worklet.mjs - Independent verification of AudioWorklet Downsampler logic
 */

import { readFileSync } from 'fs';

// Mock AudioWorklet environment
class MockAudioWorkletProcessor {
  constructor() {
    this.port = {
      messages: [],
      postMessage(msg, transfer) {
        this.messages.push(msg);
      }
    };
  }
}

globalThis.AudioWorkletProcessor = MockAudioWorkletProcessor;
globalThis.currentTime = 0;
globalThis.sampleRate = 48000;

let registeredProcessor = null;
globalThis.registerProcessor = (name, procClass) => {
  registeredProcessor = procClass;
};

// Evaluate audio-processor.js
const processorCode = readFileSync('./poc/s1-audio-capture/audio-processor.js', 'utf8');
eval(processorCode);

if (!registeredProcessor) {
  console.error('FAIL: Processor was not registered.');
  process.exit(1);
}

console.log('Testing DownsamplerWorkletProcessor...');

const processor = new registeredProcessor({
  processorOptions: {
    targetSampleRate: 16000,
    bufferSize: 2048
  }
});

// 1. Test Sine Wave Resampling (48kHz -> 16kHz)
const freq = 440; // 440 Hz
const nativeRate = 48000;
const durationSec = 1.0;
const totalNativeSamples = nativeRate * durationSec;
const frameSize = 128; // Web Audio API standard frame size

let capturedPcmBuffers = [];
processor.port.postMessage = (msg) => {
  capturedPcmBuffers.push(new Int16Array(msg.pcm16));
};

let phase = 0;
const phaseInc = (2 * Math.PI * freq) / nativeRate;

for (let i = 0; i < totalNativeSamples; i += frameSize) {
  const ch0 = new Float32Array(frameSize);
  const ch1 = new Float32Array(frameSize);
  for (let j = 0; j < frameSize; j++) {
    const s = Math.sin(phase);
    ch0[j] = s * 0.8;
    ch1[j] = s * 0.8;
    phase += phaseInc;
  }
  globalThis.currentTime += frameSize / nativeRate;
  processor.process([[ch0, ch1]]);
}

console.log(`Dispatched ${totalNativeSamples} samples in ${totalNativeSamples / frameSize} frames.`);
console.log(`Captured ${capturedPcmBuffers.length} PCM buffer chunks.`);

// Validate captured samples
let totalCapturedSamples = 0;
let hasNaN = false;
let maxVal = -32768;
let minVal = 32767;

for (const buf of capturedPcmBuffers) {
  totalCapturedSamples += buf.length;
  for (let i = 0; i < buf.length; i++) {
    const val = buf[i];
    if (isNaN(val)) hasNaN = true;
    if (val > maxVal) maxVal = val;
    if (val < minVal) minVal = val;
  }
}

console.log(`Total 16kHz samples captured: ${totalCapturedSamples} (expected ~${16000 * durationSec})`);
console.log(`Min sample: ${minVal}, Max sample: ${maxVal}`);

if (hasNaN) {
  console.error('FAIL: Output contains NaN values!');
  process.exit(1);
}

if (Math.abs(totalCapturedSamples - 16000) > 2048) {
  console.error(`FAIL: Sample count divergence is too large: ${totalCapturedSamples}`);
  process.exit(1);
}

// 2. Test Allocation Profile in Hot Path
const perfCh0 = new Float32Array(frameSize);
const perfCh1 = new Float32Array(frameSize);
const inputs = [[perfCh0, perfCh1]];

const iterCount = 10000;
const t0 = performance.now();
for (let k = 0; k < iterCount; k++) {
  processor.process(inputs);
}
const elapsedMs = performance.now() - t0;
const timePerCallUs = (elapsedMs * 1000) / iterCount;

console.log(`Performance test: ${iterCount} process() invocations completed in ${elapsedMs.toFixed(2)}ms`);
console.log(`Average time per 128-sample process() call: ${timePerCallUs.toFixed(3)} μs (Microseconds)`);

if (timePerCallUs > 50) {
  console.warn(`WARNING: High process() overhead: ${timePerCallUs} μs`);
} else {
  console.log(`PASS: Ultra-low worklet overhead (${timePerCallUs.toFixed(3)} μs / call).`);
}

console.log('Worklet Verification: PASS');
