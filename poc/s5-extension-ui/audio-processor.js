/**
 * audio-processor.js - AudioWorklet processor for downsampling 48kHz -> 16kHz mono 16-bit PCM.
 */

class DownsamplerProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetSampleRate = (options && options.processorOptions && options.processorOptions.targetSampleRate) || 16000;
    this.bufferSize = (options && options.processorOptions && options.processorOptions.bufferSize) || 2048;
    this.outputBuffer = new Int16Array(this.bufferSize);
    this.outputIndex = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const channel0 = input[0];
    const channel1 = input.length > 1 ? input[1] : null;
    const inputLength = channel0.length;
    if (inputLength === 0) return true;

    const sourceSampleRate = sampleRate;
    const ratio = sourceSampleRate / this.targetSampleRate;

    for (let i = 0; i < inputLength; i += ratio) {
      const srcIndex = Math.floor(i);
      if (srcIndex >= inputLength) break;

      let sample = channel0[srcIndex];
      if (channel1) {
        sample = (sample + channel1[srcIndex]) * 0.5;
      }

      sample = Math.max(-1.0, Math.min(1.0, sample));
      const pcm16 = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;

      this.outputBuffer[this.outputIndex++] = pcm16;

      if (this.outputIndex >= this.bufferSize) {
        this.flush();
      }
    }

    return true;
  }

  flush() {
    if (this.outputIndex === 0) return;

    const chunk = new Int16Array(this.outputIndex);
    chunk.set(this.outputBuffer.subarray(0, this.outputIndex));

    let sumSquares = 0;
    for (let i = 0; i < chunk.length; i++) {
      const norm = chunk[i] / 32768.0;
      sumSquares += norm * norm;
    }
    const rms = Math.sqrt(sumSquares / chunk.length);
    const dbfs = rms > 0 ? 20 * Math.log10(rms) : -100;

    this.port.postMessage({
      type: 'PCM_CHUNK',
      pcm16: chunk.buffer,
      samplesCount: chunk.length,
      rms: rms,
      dbfs: dbfs
    }, [chunk.buffer]);

    this.outputBuffer = new Int16Array(this.bufferSize);
    this.outputIndex = 0;
  }
}

registerProcessor('downsampler-processor', DownsamplerProcessor);
