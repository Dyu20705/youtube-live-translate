class DownsamplerWorkletProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetSampleRate = (options && options.processorOptions && options.processorOptions.targetSampleRate) || 16000;
    this.bufferSize = (options && options.processorOptions && options.processorOptions.bufferSize) || 2048;
    this.outputBuffer = new Float32Array(this.bufferSize);
    this.outputIndex = 0;
    this.sourcePhase = 0.0;
    this.lastSample = 0.0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0 || !input[0] || input[0].length === 0) {
      return true;
    }

    const channel0 = input[0];
    const channel1 = input[1];
    const isStereo = channel1 && channel1.length > 0;
    const inputLength = channel0.length;

    const inputSampleRate = globalThis.sampleRate || 48000;
    const ratio = inputSampleRate / this.targetSampleRate;

    let sourceIndex = this.sourcePhase;

    while (sourceIndex < inputLength) {
      const idxFloor = Math.floor(sourceIndex);
      const frac = sourceIndex - idxFloor;

      let sPrev;
      if (idxFloor === 0 && this.sourcePhase < 0) {
        sPrev = this.lastSample;
      } else {
        sPrev = isStereo
          ? (channel0[idxFloor] + channel1[idxFloor]) * 0.5
          : channel0[idxFloor];
      }

      const nextIdx = Math.min(idxFloor + 1, inputLength - 1);
      const sNext = isStereo
        ? (channel0[nextIdx] + channel1[nextIdx]) * 0.5
        : channel0[nextIdx];

      const sample = sPrev * (1.0 - frac) + sNext * frac;
      this.outputBuffer[this.outputIndex++] = Math.max(-1.0, Math.min(1.0, sample));

      if (this.outputIndex >= this.bufferSize) {
        let sumSquares = 0;
        const pcm16 = new Int16Array(this.bufferSize);
        for (let i = 0; i < this.bufferSize; i++) {
          const s = this.outputBuffer[i];
          sumSquares += s * s;
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }

        const rms = Math.sqrt(sumSquares / this.bufferSize);
        const dbfs = rms > 0 ? 20 * Math.log10(rms) : -100;

        this.port.postMessage({
          type: 'PCM_CHUNK',
          pcm16: pcm16.buffer,
          samplesCount: this.bufferSize,
          rms: rms,
          dbfs: dbfs,
          timestamp: currentTime
        }, [pcm16.buffer]);

        this.outputIndex = 0;
      }

      sourceIndex += ratio;
    }

    this.sourcePhase = sourceIndex - inputLength;
    const lastIdx = inputLength - 1;
    this.lastSample = isStereo
      ? (channel0[lastIdx] + channel1[lastIdx]) * 0.5
      : channel0[lastIdx];

    return true;
  }
}

registerProcessor('downsampler-processor', DownsamplerWorkletProcessor);
