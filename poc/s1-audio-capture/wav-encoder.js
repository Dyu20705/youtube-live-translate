/**
 * wav-encoder.js - Helper to create standard RIFF WAV files from 16kHz 16-bit Mono PCM chunks.
 */

function encodeWav(pcmChunks, sampleRate = 16000, numChannels = 1, bitDepth = 16) {
  // Calculate total byte size of PCM chunks
  let totalBytes = 0;
  for (const chunk of pcmChunks) {
    totalBytes += chunk.byteLength;
  }

  const bytesPerSample = bitDepth / 8;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = totalBytes;
  const headerSize = 44;
  const totalFileSize = headerSize + dataSize;

  const buffer = new ArrayBuffer(totalFileSize);
  const view = new DataView(buffer);

  function writeString(offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  // RIFF Header
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + dataSize, true); // ChunkSize
  writeString(8, 'WAVE');

  // fmt Subchunk
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true);  // AudioFormat (1 = PCM)
  view.setUint16(22, numChannels, true); // NumChannels (1 = Mono)
  view.setUint32(24, sampleRate, true);  // SampleRate (16000)
  view.setUint32(28, byteRate, true);    // ByteRate
  view.setUint16(32, blockAlign, true);  // BlockAlign
  view.setUint16(34, bitDepth, true);    // BitsPerSample (16)

  // data Subchunk
  writeString(36, 'data');
  view.setUint32(40, dataSize, true);

  // Copy PCM data
  let offset = 44;
  const uint8View = new Uint8Array(buffer);
  for (const chunk of pcmChunks) {
    uint8View.set(new Uint8Array(chunk), offset);
    offset += chunk.byteLength;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { encodeWav };
}
