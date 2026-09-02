/**
 * wav-encoder.js - Minimal WAV file encoder for debugging captured audio.
 */

function encodeWav(samplesChunks, sampleRate, numChannels, bitsPerSample) {
  let totalLength = 0;
  for (let i = 0; i < samplesChunks.length; i++) {
    totalLength += samplesChunks[i].byteLength;
  }

  const byteRate = (sampleRate * numChannels * bitsPerSample) / 8;
  const blockAlign = (numChannels * bitsPerSample) / 8;
  const buffer = new ArrayBuffer(44 + totalLength);
  const view = new DataView(buffer);

  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + totalLength, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  writeString(view, 36, 'data');
  view.setUint32(40, totalLength, true);

  const uint8View = new Uint8Array(buffer, 44);
  let currentOffset = 0;
  for (let i = 0; i < samplesChunks.length; i++) {
    uint8View.set(new Uint8Array(samplesChunks[i]), currentOffset);
    currentOffset += samplesChunks[i].byteLength;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}
